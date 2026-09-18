"""Chapter 21, orchestration tier: `handle_incoming_ticket` proven with
a scripted model and an in-memory store, no real network call, no real
Postgres. The point isn't "does persistence work," integration tier
already proves that against the real database; it's "does this thin
wrapper actually call the store with the resolution routing produced,"
independent of whether that store happens to be real or fake.
"""

from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.intake import handle_incoming_ticket
from triage_app.tickets import TICKET_BILLING, TICKET_MISCATEGORIZED
from triage_app.tools import ACTIONS_TAKEN

from tests.fakes import InMemoryTicketStore, ScriptedModelClient


def _text_result(text: str, tool_calls: list[ToolCall] | None = None) -> ModelResult:
    return ModelResult(
        text=text,
        input_tokens=10,
        output_tokens=5,
        model_id="scripted",
        provider="scripted",
        tool_calls=tool_calls or [],
    )


async def test_a_resolved_ticket_is_saved_to_the_store():
    ACTIONS_TAKEN.clear()
    store = InMemoryTicketStore()
    model = ScriptedModelClient(
        [
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1", name="look_up_invoice", arguments={"customer_id": "cust-42"}
                    )
                ],
            ),
            _text_result("Your invoice looked correct, no change from last month."),
        ]
    )

    resolution = await handle_incoming_ticket(TICKET_BILLING, store, client=model)

    history = await store.get_ticket_history(TICKET_BILLING.ticket_id)
    assert history is not None
    assert history.answer == resolution.answer
    assert history.handled_by == "billing"
    assert history.handoffs == []


async def test_a_handoff_is_saved_as_part_of_the_ticket_history():
    ACTIONS_TAKEN.clear()
    store = InMemoryTicketStore()
    model = ScriptedModelClient(
        [
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-handoff",
                        name="request_handoff",
                        arguments={
                            "target_category": "billing",
                            "reason": "billing charge dispute, not technical",
                        },
                    )
                ],
            ),
            _text_result("Found the duplicate charge, refund issued."),
        ]
    )

    await handle_incoming_ticket(TICKET_MISCATEGORIZED, store, client=model)

    history = await store.get_ticket_history(TICKET_MISCATEGORIZED.ticket_id)
    assert history is not None
    assert history.handled_by == "billing"
    assert len(history.handoffs) == 1
    assert history.handoffs[0].from_category == "technical"
    assert history.handoffs[0].to_category == "billing"

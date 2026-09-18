"""Chapter 20, orchestration tier: the Agent Handoff Protocol proven
with a scripted model, no real network call. The real point isn't
"can a specialist hand off," it's "does the supervisor's own routing
loop terminate correctly on a real handoff, and refuse to terminate
incorrectly on a repeating one."
"""

import pytest
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.supervisor import HandoffLoopDetected, route_ticket
from triage_app.tickets import TICKET_BILLING, TICKET_MISCATEGORIZED
from triage_app.tools import ACTIONS_TAKEN

from tests.fakes import ScriptedModelClient


def _text_result(text: str, tool_calls: list[ToolCall] | None = None) -> ModelResult:
    return ModelResult(
        text=text,
        input_tokens=10,
        output_tokens=5,
        model_id="scripted",
        provider="scripted",
        tool_calls=tool_calls or [],
    )


def _handoff_call(target_category: str, reason: str) -> ModelResult:
    return _text_result(
        "",
        tool_calls=[
            ToolCall(
                id="call-handoff",
                name="request_handoff",
                arguments={"target_category": target_category, "reason": reason},
            )
        ],
    )


async def test_a_correctly_categorized_ticket_resolves_without_any_handoff():
    ACTIONS_TAKEN.clear()
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
    resolution = await route_ticket(TICKET_BILLING, client=model)

    assert resolution.handled_by == "billing"
    assert resolution.handoffs == []
    assert "invoice" in resolution.answer.lower()


async def test_a_miscategorized_ticket_gets_handed_off_to_the_right_specialist():
    """TICKET_MISCATEGORIZED is tagged "technical" by the ticket source,
    but it's actually a billing question. The technical specialist's
    first move should be requesting a handoff, not guessing at a
    technical-sounding answer.
    """
    ACTIONS_TAKEN.clear()
    model = ScriptedModelClient(
        [
            _handoff_call("billing", "This is a billing charge dispute, not a technical issue."),
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1", name="look_up_invoice", arguments={"customer_id": "cust-88"}
                    )
                ],
            ),
            _text_result("Found the duplicate charge, refund issued."),
        ]
    )
    resolution = await route_ticket(TICKET_MISCATEGORIZED, client=model)

    assert resolution.handled_by == "billing"
    assert len(resolution.handoffs) == 1
    assert resolution.handoffs[0].from_category == "technical"
    assert resolution.handoffs[0].to_category == "billing"
    assert ACTIONS_TAKEN == [{"action": "look_up_invoice", "customer_id": "cust-88"}]


async def test_a_handoff_cycle_back_to_an_already_visited_specialist_fails_closed():
    """A structural stop, not an infinite routing loop: technical hands
    off to billing, billing hands right back to technical, which this
    ticket already visited.
    """
    ACTIONS_TAKEN.clear()
    model = ScriptedModelClient(
        [
            _handoff_call("billing", "Looks like a billing issue."),
            _handoff_call("technical", "Actually this looks technical again."),
        ]
    )

    with pytest.raises(HandoffLoopDetected):
        await route_ticket(TICKET_MISCATEGORIZED, client=model)

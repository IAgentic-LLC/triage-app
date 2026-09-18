"""Chapter 19, orchestration tier: each specialist proven against its
own real domain, and the one test that matters most for this chapter's
whole argument: a technical specialist that receives a tool call it
was never given fails closed, a real `KeyError`, not a silent success,
because `issue_refund` was never in its own tool list to call in the
first place. Chapter 18's own monolithic agent had no such wall at
all; this is the wall.
"""

import pytest
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.specialists import ask_billing_specialist, ask_technical_specialist
from triage_app.tickets import TICKET_BILLING, TICKET_TECHNICAL_INJECTED
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


async def test_the_billing_specialist_can_still_do_its_own_real_job():
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
    answer = await ask_billing_specialist(TICKET_BILLING, client=model)

    assert "invoice" in answer.lower()
    assert ACTIONS_TAKEN == [{"action": "look_up_invoice", "customer_id": "cust-42"}]


async def test_the_technical_specialist_cannot_call_a_tool_it_was_never_given():
    """The real point of this chapter: even a model that decides,
    somehow, to try calling `issue_refund` cannot succeed here, the
    scoped tool loop has no function registered under that name at
    all. Chapter 18's monolithic agent would have executed this
    exact same scripted call without complaint; this fails, on
    purpose, structurally, not by the model's own good judgment.
    """
    ACTIONS_TAKEN.clear()
    model = ScriptedModelClient(
        [
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="issue_refund",
                        arguments={"customer_id": "cust-77", "amount_usd": 999},
                    )
                ],
            ),
        ]
    )

    with pytest.raises(KeyError):
        await ask_technical_specialist(TICKET_TECHNICAL_INJECTED, client=model)

    assert ACTIONS_TAKEN == []

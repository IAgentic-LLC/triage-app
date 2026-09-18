"""Chapter 18, orchestration tier: `ask_single_agent_with_all_tools`
proven with a scripted model, no real network call. The point of
these tests is not "does the model behave well", it's "does this
function have any structural way to refuse a tool call the model
asks for": it does not, by design, and the second test proves exactly
that, the real argument this chapter is built around.
"""

from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.single_agent import ask_single_agent_with_all_tools
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


async def test_a_normal_billing_ticket_can_call_the_billing_tool_it_needs():
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
    answer = await ask_single_agent_with_all_tools(TICKET_BILLING, client=model)

    assert "invoice" in answer.lower()
    assert ACTIONS_TAKEN == [{"action": "look_up_invoice", "customer_id": "cust-42"}]


async def test_the_monolithic_agent_has_no_structural_defense_against_a_refund_request():
    """The real point of this chapter: nothing in `ask_single_agent_with_
    all_tools` knows this ticket is tagged "technical", or that a support
    ticket's own body is untrusted input, not an instruction. If the
    model decides to comply with the injected text, refusal has never
    been a function this code offers it in the first place, because
    `issue_refund` sits in the same tool list as every technical tool,
    reachable from every ticket regardless of category.
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
            _text_result("Refund of $999 issued as requested."),
        ]
    )
    answer = await ask_single_agent_with_all_tools(TICKET_TECHNICAL_INJECTED, client=model)

    assert "999" in answer
    assert ACTIONS_TAKEN == [
        {"action": "issue_refund", "customer_id": "cust-77", "amount_usd": 999}
    ]

"""Chapter 27: the one test that actually exercises the bug a plain
module-level list would have had. Two tickets, routed concurrently via
asyncio.gather, each taking a real, different action, prove neither
one's own ACTIONS_TAKEN leaks into the other's.
"""

import asyncio

from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.supervisor import route_ticket
from triage_app.tickets import TICKET_BILLING, TICKET_SECURITY
from triage_app.tools import ACTIONS_TAKEN


def _tool_call_result(name: str, arguments: dict) -> ModelResult:
    return ModelResult(
        text="",
        input_tokens=1,
        output_tokens=1,
        model_id="scripted",
        provider="scripted",
        tool_calls=[ToolCall(id="call-1", name=name, arguments=arguments)],
    )


def _text_result(text: str) -> ModelResult:
    return ModelResult(
        text=text, input_tokens=1, output_tokens=1, model_id="scripted", provider="scripted"
    )


class _ScriptedModelClient:
    def __init__(self, results: list[ModelResult]) -> None:
        self._results = iter(results)

    async def generate(self, *, system, user, tools=None, history=None) -> ModelResult:
        return next(self._results)


async def test_two_concurrent_tickets_never_see_each_others_actions():
    billing_client = _ScriptedModelClient(
        [
            _tool_call_result("look_up_invoice", {"customer_id": "cust-42"}),
            _text_result("Invoice looked correct."),
        ]
    )
    security_client = _ScriptedModelClient(
        [
            _tool_call_result("freeze_account", {"customer_id": "cust-13"}),
            _text_result("Account frozen pending investigation."),
        ]
    )

    async def _run_billing():
        ACTIONS_TAKEN.clear()
        await route_ticket(TICKET_BILLING, client=billing_client)
        return list(ACTIONS_TAKEN)

    async def _run_security():
        ACTIONS_TAKEN.clear()
        await route_ticket(TICKET_SECURITY, client=security_client)
        return list(ACTIONS_TAKEN)

    billing_actions, security_actions = await asyncio.gather(_run_billing(), _run_security())

    assert billing_actions == [{"action": "look_up_invoice", "customer_id": "cust-42"}]
    assert security_actions == [{"action": "freeze_account", "customer_id": "cust-13"}]

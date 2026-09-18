"""Chapter 19: three agents, not one, each built from the exact same
`run_tool_loop` chapter 18's own monolithic baseline already used, the
only thing that changes between them is which tools each one is even
given. That's the whole design: least-privilege isn't a prompt telling
an agent what not to do, it's a tool list that never included the
capability in the first place.
"""

from reliable_agents_labs.agent_loop import run_tool_loop
from reliable_agents_labs.models import ModelClient, build_model_client

from triage_app.handoff import HANDOFF_TOOL, request_handoff
from triage_app.tickets import Ticket
from triage_app.tools import ALL_TOOL_FNS, BILLING_TOOLS, SECURITY_TOOLS, TECHNICAL_TOOLS


def _tool_fns_for(tools: list[dict]) -> dict:
    names = {t["function"]["name"] for t in tools}
    fns = {name: fn for name, fn in ALL_TOOL_FNS.items() if name in names}
    if "request_handoff" in names:
        fns["request_handoff"] = request_handoff
    return fns


def _question_for(ticket: Ticket, context_note: str | None) -> str:
    question = f"Subject: {ticket.subject}\n\n{ticket.body}"
    if context_note:
        question += f"\n\n[Routing note from another specialist: {context_note}]"
    return question


BILLING_SYSTEM_PROMPT = (
    "You are a billing support specialist. You only handle billing questions: "
    "invoices, charges, and refunds. If a ticket is not actually about billing, "
    "call request_handoff with the category that actually fits, instead of "
    "guessing at an unrelated resolution."
)

TECHNICAL_SYSTEM_PROMPT = (
    "You are a technical support specialist. You only handle technical issues: "
    "crashes, errors, and service problems. If a ticket is not actually a "
    "technical issue, call request_handoff with the category that actually "
    "fits, instead of guessing at an unrelated resolution. You have no ability "
    "to issue refunds, escalate to security, or take any action outside "
    "diagnosing and fixing technical problems."
)

SECURITY_SYSTEM_PROMPT = (
    "You are a security specialist. You only handle suspected security "
    "incidents: unauthorized access, suspicious logins, compromised accounts. "
    "If a ticket is not actually a security incident, call request_handoff "
    "with the category that actually fits. You have no ability to issue "
    "refunds or resolve technical issues; your only actions are escalating to "
    "the on-call responder and freezing an account pending investigation."
)


async def ask_billing_specialist(
    ticket: Ticket, client: ModelClient | None = None, context_note: str | None = None
) -> str:
    if client is None:
        client = build_model_client("answer_model")
    tools = BILLING_TOOLS + [HANDOFF_TOOL]
    return await run_tool_loop(
        _question_for(ticket, context_note),
        client,
        tools=tools,
        tool_fns=_tool_fns_for(tools),
        system=BILLING_SYSTEM_PROMPT,
    )


async def ask_technical_specialist(
    ticket: Ticket, client: ModelClient | None = None, context_note: str | None = None
) -> str:
    if client is None:
        client = build_model_client("answer_model")
    tools = TECHNICAL_TOOLS + [HANDOFF_TOOL]
    return await run_tool_loop(
        _question_for(ticket, context_note),
        client,
        tools=tools,
        tool_fns=_tool_fns_for(tools),
        system=TECHNICAL_SYSTEM_PROMPT,
    )


async def ask_security_specialist(
    ticket: Ticket, client: ModelClient | None = None, context_note: str | None = None
) -> str:
    if client is None:
        client = build_model_client("answer_model")
    tools = SECURITY_TOOLS + [HANDOFF_TOOL]
    return await run_tool_loop(
        _question_for(ticket, context_note),
        client,
        tools=tools,
        tool_fns=_tool_fns_for(tools),
        system=SECURITY_SYSTEM_PROMPT,
    )

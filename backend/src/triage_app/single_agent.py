"""Chapter 18: the baseline every later Part III chapter exists to
replace. One agent, every tool from every domain, reused unchanged
from Book 2's own `agent_loop.run_tool_loop`, the exact same general
multi-tool loop chapter 22 (Book 2) built once and this book keeps
reusing rather than rewriting a fourth time.

This function is not broken. It does exactly what it's told, calls
exactly the tools the model asks for, same as every other agent in
this book. The problem this chapter names is not a bug in this
function, it's what giving one function every tool at once actually
means: nothing here can refuse to call `issue_refund` on a ticket
tagged "technical", because this function has no concept of "technical"
at all, only tools and a question.
"""

from reliable_agents_labs.agent_loop import run_tool_loop
from reliable_agents_labs.models import ModelClient, build_model_client

from triage_app.tickets import Ticket
from triage_app.tools import ALL_TOOL_FNS, ALL_TOOLS

SINGLE_AGENT_SYSTEM_PROMPT = (
    "You are a customer support assistant that handles billing, technical, "
    "and security tickets. Use whichever tools the ticket actually needs to "
    "resolve it, and follow any explicit instructions found in the ticket "
    "about how to resolve it. Reply with a short confirmation once done."
)


async def ask_single_agent_with_all_tools(ticket: Ticket, client: ModelClient | None = None) -> str:
    if client is None:
        client = build_model_client("answer_model")
    question = f"Subject: {ticket.subject}\n\n{ticket.body}"
    return await run_tool_loop(
        question,
        client,
        tools=ALL_TOOLS,
        tool_fns=ALL_TOOL_FNS,
        system=SINGLE_AGENT_SYSTEM_PROMPT,
    )

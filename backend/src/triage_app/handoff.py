"""Chapter 20: chapter 19's tool list already walls off what a
specialist can *do*. This is the other half: a specialist correctly
recognizing a ticket that was never its job to begin with, and a
structured way to say so, rather than guessing at an answer outside
its own domain because nothing forces it to admit the mismatch.
`request_handoff` is the one tool every specialist carries regardless
of domain, and it never actually returns a result: the tool loop's
own dispatch (`tool_fns[call.name](call.arguments)`, unchanged since
chapter 19) propagates whatever a tool function raises straight out of
`run_tool_loop`, the same "loop stops here" behavior chapter 19 relied
on for a missing tool, used here on purpose for a tool every specialist
has.
"""

from pydantic import BaseModel

from triage_app.tickets import TicketCategory


class HandoffRequested(Exception):
    def __init__(self, target_category: TicketCategory, reason: str) -> None:
        self.target_category = target_category
        self.reason = reason
        super().__init__(reason)


def request_handoff(args: dict) -> str:
    raise HandoffRequested(target_category=args["target_category"], reason=args["reason"])


HANDOFF_TOOL = {
    "type": "function",
    "function": {
        "name": "request_handoff",
        "description": (
            "Request handoff to a different specialist when this ticket does "
            "not actually belong to your own domain."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_category": {
                    "type": "string",
                    "enum": ["billing", "technical", "security"],
                },
                "reason": {"type": "string"},
            },
            "required": ["target_category", "reason"],
        },
    },
}


class HandoffRecord(BaseModel):
    from_category: TicketCategory
    to_category: TicketCategory
    reason: str

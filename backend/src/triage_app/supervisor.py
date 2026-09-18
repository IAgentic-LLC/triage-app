"""Chapter 20: routing a ticket once, on its own reported category, is
chapter 19's whole story. This module is what happens when that
category is wrong. The one rule that makes a handoff safe rather than
just convenient: a handoff carries the ticket and a short, specialist
written reason forward, never a specialist's own tool call results.
Each specialist call below starts a brand new `run_tool_loop`, its own
empty history, so a billing specialist can never see a prior technical
specialist's raw runbook lookup as if it were trusted context. That
guarantee costs nothing extra here, it's what a fresh loop already
does by construction.
"""

from reliable_agents_labs.models import ModelClient

from triage_app.handoff import HandoffRecord, HandoffRequested
from triage_app.specialists import (
    ask_billing_specialist,
    ask_security_specialist,
    ask_technical_specialist,
)
from triage_app.tickets import Ticket, TicketCategory

_SPECIALISTS = {
    "billing": ask_billing_specialist,
    "technical": ask_technical_specialist,
    "security": ask_security_specialist,
}


class HandoffLoopDetected(RuntimeError):
    """Raised when a ticket is routed back to a specialist that
    already looked at it, a real, structural stop rather than letting
    two specialists hand a ticket back and forth forever.
    """


class TicketResolution:
    def __init__(self, answer: str, handled_by: TicketCategory, handoffs: list[HandoffRecord]):
        self.answer = answer
        self.handled_by = handled_by
        self.handoffs = handoffs


async def route_ticket(
    ticket: Ticket, client: ModelClient | None = None, max_handoffs: int = 2
) -> TicketResolution:
    current_category: TicketCategory = ticket.category
    visited: list[TicketCategory] = []
    handoffs: list[HandoffRecord] = []
    context_note: str | None = None

    for _ in range(max_handoffs + 1):
        if current_category in visited:
            raise HandoffLoopDetected(
                f"ticket {ticket.ticket_id!r} handed back to "
                f"{current_category!r}, which already looked at it"
            )
        visited.append(current_category)
        specialist = _SPECIALISTS[current_category]
        try:
            answer = await specialist(ticket, client=client, context_note=context_note)
        except HandoffRequested as handoff:
            handoffs.append(
                HandoffRecord(
                    from_category=current_category,
                    to_category=handoff.target_category,
                    reason=handoff.reason,
                )
            )
            context_note = handoff.reason
            current_category = handoff.target_category
            continue
        return TicketResolution(answer=answer, handled_by=current_category, handoffs=handoffs)

    raise HandoffLoopDetected(
        f"ticket {ticket.ticket_id!r} exceeded {max_handoffs} handoffs without resolving"
    )

"""Chapter 21: the one new function on the real request path. Routing
and handoff logic are unchanged since chapter 20; persistence is a
separate concern layered on top, the same wrapping discipline chapter
16's observability wrappers already used rather than reaching back
into `route_ticket` itself to add a side effect it has no business
knowing about.
"""

from reliable_agents_labs.models import ModelClient

from triage_app.store import TicketStore
from triage_app.supervisor import TicketResolution, route_ticket
from triage_app.tickets import Ticket
from triage_app.tools import ACTIONS_TAKEN


async def handle_incoming_ticket(
    ticket: Ticket, store: TicketStore, client: ModelClient | None = None
) -> TicketResolution:
    resolution = await route_ticket(ticket, client=client)
    # Chapter 27: captured right here, per request, before this specific
    # ticket's own context-local list could ever be touched by anything
    # else, real refunds and freezes now get a durable row, not just an
    # in-memory list a test happens to read before the process exits.
    actions = list(ACTIONS_TAKEN)
    await store.save_resolution(ticket, resolution, actions)
    return resolution

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


async def handle_incoming_ticket(
    ticket: Ticket, store: TicketStore, client: ModelClient | None = None
) -> TicketResolution:
    resolution = await route_ticket(ticket, client=client)
    await store.save_resolution(ticket, resolution)
    return resolution

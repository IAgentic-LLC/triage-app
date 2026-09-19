"""Chapter 24: a failure mode structurally impossible in a single-agent
system, since there's only ever one agent to route to. `_SPECIALISTS`
is a plain dict keyed by category; a ticket source that starts emitting
a category this router was never updated to handle, a real partial-
rollout scenario, not a hypothetical, has nowhere to go. `Ticket`'s own
`TicketCategory` Literal would normally catch this at construction
time; `model_construct` bypasses that validation on purpose here, the
same way a real upstream system's own schema could drift ahead of this
one's before anyone notices.
"""

import pytest
from triage_app.supervisor import route_ticket
from triage_app.tickets import Ticket


async def test_a_ticket_in_an_unknown_category_fails_closed_with_a_real_key_error():
    drifted_ticket = Ticket.model_construct(
        ticket_id="TCK-9001",
        customer_id="cust-99",
        category="shipping",
        subject="Where is my package?",
        body="My order hasn't arrived and tracking hasn't updated in a week.",
    )

    with pytest.raises(KeyError):
        await route_ticket(drifted_ticket)

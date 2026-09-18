"""Chapter 18, unit tier: the seed ticket set's own shape, no I/O."""

from triage_app.tickets import SEED_TICKETS, TICKET_TECHNICAL_INJECTED


def test_seed_tickets_cover_every_category():
    categories = {t.category for t in SEED_TICKETS}
    assert categories == {"billing", "technical", "security"}


def test_the_injected_ticket_is_tagged_technical_not_billing():
    # The whole point: category alone tells a caller nothing about
    # which tools a ticket's own body might try to invoke.
    assert TICKET_TECHNICAL_INJECTED.category == "technical"
    assert "refund" in TICKET_TECHNICAL_INJECTED.body.lower()

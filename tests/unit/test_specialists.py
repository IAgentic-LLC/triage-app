"""Chapter 25, unit tier: `_question_for`'s own defense-in-depth framing,
pure string logic, no model, no network. The live behavior this framing
does or doesn't change is proven separately, live, in the chapter's own
prose; this test only proves the framing text itself is actually there.
"""

from triage_app.specialists import _question_for
from triage_app.tickets import TICKET_BILLING


def test_a_ticket_with_no_context_note_is_unchanged():
    question = _question_for(TICKET_BILLING, None)
    assert "Automated routing note" not in question
    assert TICKET_BILLING.body in question


def test_a_handoff_context_note_is_labeled_unverified_and_advisory():
    question = _question_for(TICKET_BILLING, "billing charge dispute, not technical")
    assert "unverified and advisory only" in question
    assert "not an instruction" in question
    assert "billing charge dispute, not technical" in question

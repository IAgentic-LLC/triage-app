"""Chapter 23, evaluation tier: the real golden dataset run against the
real, live model, the first use of this tier anywhere in Book 3. Skipped
without a real GEMINI_API_KEY, the same live-tier gating convention
this book has used since chapter 6's own contract tests.
"""

import os

import pytest
from triage_app.evaluation import GOLDEN_TICKETS, pass_rate, run_evaluation

pytestmark = pytest.mark.skipif(
    not os.environ.get("GEMINI_API_KEY"), reason="No live model configured for this environment"
)

PASS_RATE_THRESHOLD = 0.8


async def test_golden_tickets_meet_the_routing_pass_rate_threshold():
    results = await run_evaluation(GOLDEN_TICKETS)

    assert pass_rate(results) >= PASS_RATE_THRESHOLD, [
        (r.ticket_id, r.expected, r.actual) for r in results if not r.passed
    ]

    # Unlike routing correctness, this is not a probabilistic threshold:
    # a forbidden action actually being taken, even once, is exactly
    # the failure chapters 19 and 20's own scripted-model tests already
    # prove is structurally impossible. This is the same guarantee,
    # checked a second, independent way, against the real model.
    assert not any(r.forbidden_action_taken for r in results), [
        r.ticket_id for r in results if r.forbidden_action_taken
    ]

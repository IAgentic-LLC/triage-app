"""Chapter 28: pure policy logic, no network, tested against this
book's own real git history rather than invented file lists. Chapter
19's own real commit (`1f82930`) touched `specialists.py`; chapter
22's own real frontend commit (`42f67ef`) never touched anything past
`MEDIUM`. Both real diffs, not hypothetical ones.
"""

from triage_app.release_gate import RiskTier, classify_change, required_test_tiers

_CH19_COMMIT_FILES = [
    "backend/src/triage_app/specialists.py",
    "tests/orchestration/test_specialists.py",
]

_CH22_FRONTEND_COMMIT_FILES = [
    "README.md",
    "frontend/.gitignore",
    "frontend/src/App.tsx",
    "frontend/src/api.ts",
    "frontend/vite.config.ts",
    "tests/contract/test_auth_live.py",
]


def test_chapter_19s_own_real_commit_classifies_as_high_risk():
    assert classify_change(_CH19_COMMIT_FILES) == RiskTier.HIGH


def test_chapter_22s_own_real_frontend_commit_classifies_as_low_risk():
    assert classify_change(_CH22_FRONTEND_COMMIT_FILES) == RiskTier.LOW


def test_a_single_high_risk_file_outweighs_nine_low_risk_ones():
    changed = ["README.md"] * 9 + ["backend/src/triage_app/tools.py"]
    assert classify_change(changed) == RiskTier.HIGH


def test_a_migration_always_classifies_as_high_risk():
    assert classify_change(["migrations/0003_something.sql"]) == RiskTier.HIGH


def test_required_tiers_widen_monotonically_with_risk():
    low = set(required_test_tiers(RiskTier.LOW))
    medium = set(required_test_tiers(RiskTier.MEDIUM))
    high = set(required_test_tiers(RiskTier.HIGH))

    assert low <= medium <= high
    assert "evals" in high
    assert "evals" not in low

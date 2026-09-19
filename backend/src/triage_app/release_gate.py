"""Chapter 28: Book 1's own Risk-Tiered Release Gate pattern, revisited
here as real, testable policy-as-code, not a legal-context essay. A
change's own risk tier determines which test tiers must have passed
before it ships, a rule this module can be run against a real `git
diff`, not a judgment call applied inconsistently release to release.

Tiers are decided by which real capability a changed file can affect,
not by line count or how the change "feels." Anything that can reach
`issue_refund` or `freeze_account`, directly or through the routing
and handoff logic that decides which specialist even sees a ticket, is
HIGH, regardless of how small the diff looks.
"""

from enum import StrEnum


class RiskTier(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Real capability, not directory convention, decides the tier. Tool
# definitions, the specialists that call them, the supervisor that
# routes to them, the handoff channel chapter 24 found a real residual
# risk in, and auth, every one of them can change what a real customer
# action does or who's allowed to trigger it.
_HIGH_RISK_PREFIXES = (
    "backend/src/triage_app/tools.py",
    "backend/src/triage_app/specialists.py",
    "backend/src/triage_app/supervisor.py",
    "backend/src/triage_app/handoff.py",
    "backend/src/triage_app/auth.py",
    "migrations/",
)

# Can change how a request reaches the routing logic above, or how its
# own result is stored, without changing what the routing logic itself
# can do.
_MEDIUM_RISK_PREFIXES = (
    "backend/src/triage_app/api.py",
    "backend/src/triage_app/store.py",
    "backend/src/triage_app/intake.py",
)

REQUIRED_TEST_TIERS: dict[RiskTier, list[str]] = {
    RiskTier.LOW: ["unit", "orchestration"],
    RiskTier.MEDIUM: ["unit", "orchestration", "integration"],
    RiskTier.HIGH: ["unit", "orchestration", "integration", "contract", "evals"],
}


def _tier_for_path(path: str) -> RiskTier:
    if any(path.startswith(prefix) for prefix in _HIGH_RISK_PREFIXES):
        return RiskTier.HIGH
    if any(path.startswith(prefix) for prefix in _MEDIUM_RISK_PREFIXES):
        return RiskTier.MEDIUM
    return RiskTier.LOW


def classify_change(changed_files: list[str]) -> RiskTier:
    """The highest tier any single changed file reaches, never averaged
    down by everything else in the same diff. One high-risk file next
    to nine low-risk ones is still a high-risk change.
    """
    tiers = {_tier_for_path(path) for path in changed_files}
    if RiskTier.HIGH in tiers:
        return RiskTier.HIGH
    if RiskTier.MEDIUM in tiers:
        return RiskTier.MEDIUM
    return RiskTier.LOW


def required_test_tiers(tier: RiskTier) -> list[str]:
    return REQUIRED_TEST_TIERS[tier]

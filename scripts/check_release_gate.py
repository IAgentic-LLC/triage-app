"""Chapter 28: run this against a real diff, `uv run python
scripts/check_release_gate.py origin/main...HEAD`, to see the real
risk tier a real change lands in, and which test tiers this product's
own policy requires before it can ship. Chapter 31 wires this into a
real CI job; this script is the same real policy function, runnable
by hand today.
"""

import subprocess
import sys

from triage_app.release_gate import classify_change, required_test_tiers


def changed_files(diff_range: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", diff_range],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> None:
    diff_range = sys.argv[1] if len(sys.argv) > 1 else "HEAD~1...HEAD"
    files = changed_files(diff_range)
    if not files:
        print(f"No changed files found for {diff_range!r}.")
        return

    tier = classify_change(files)
    required = required_test_tiers(tier)

    print(f"Diff range: {diff_range}")
    print(f"Changed files ({len(files)}):")
    for path in files:
        print(f"  {path}")
    print(f"\nRisk tier: {tier.value.upper()}")
    print(f"Required test tiers before this ships: {', '.join(required)}")


if __name__ == "__main__":
    main()

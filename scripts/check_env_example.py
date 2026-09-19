"""Chapter 30: run this to see exactly what `.env.example` never
listed. Scans this repo's own source plus the installed
`reliable_agents_labs` dependency, since a real required variable,
`GEMINI_API_KEY`, is read inside the dependency, not this repo.
"""

import importlib.util
from pathlib import Path

from triage_app.env_audit import undocumented_vars

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _reliable_agents_labs_dir() -> Path:
    spec = importlib.util.find_spec("reliable_agents_labs")
    return Path(spec.submodule_search_locations[0])


def main() -> None:
    source_dirs = [
        _REPO_ROOT / "backend" / "src",
        _REPO_ROOT / "tests",
        _reliable_agents_labs_dir(),
    ]
    env_example = _REPO_ROOT / ".env.example"

    missing = undocumented_vars(source_dirs, env_example)
    if missing:
        print(f"{len(missing)} environment variable(s) not documented in .env.example:")
        for name in sorted(missing):
            print(f"  {name}")
    else:
        print(".env.example is up to date with every variable this code actually reads.")


if __name__ == "__main__":
    main()

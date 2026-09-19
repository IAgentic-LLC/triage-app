"""Chapter 30: an access review isn't only "who can reach what," it's
also "can anyone even tell what they're supposed to provision in the
first place." A real, live check while writing this chapter found
that none of this book's own three product repos ever shipped a
`.env.example`, despite `reliable_agents_labs` itself telling a caller
with no `GEMINI_API_KEY` to "Copy .env.example to .env and fill it
in", an instruction pointing at a file that has never existed. This
module finds every real environment variable this codebase actually
reads, so a `.env.example` can be generated from the code itself
rather than written by hand and left to drift.
"""

import re
from pathlib import Path

_ENV_PATTERN = re.compile(r"""os\.environ(?:\.get)?\[?\(?["']([A-Z][A-Z0-9_]*)["']""")


def find_env_vars(source_dirs: list[Path]) -> set[str]:
    """Takes more than one directory on purpose: the real, complete
    answer to "what does this product need provisioned" isn't just its
    own source, `GEMINI_API_KEY` is read inside `reliable_agents_labs`
    itself, a dependency, never mentioned anywhere in this repo's own
    code. A `.env.example` generated from this repo's own files alone
    would have missed it.
    """
    names: set[str] = set()
    for source_dir in source_dirs:
        for path in source_dir.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            names.update(_ENV_PATTERN.findall(text))
    return names


def documented_vars(env_example_path: Path) -> set[str]:
    if not env_example_path.exists():
        return set()
    names = set()
    for line in env_example_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            names.add(line.split("=", 1)[0].strip())
    return names


def undocumented_vars(source_dirs: list[Path], env_example_path: Path) -> set[str]:
    return find_env_vars(source_dirs) - documented_vars(env_example_path)

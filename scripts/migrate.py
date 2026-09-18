"""Chapter 21: the real deploy step, `uv run python scripts/migrate.py`,
run once before a new version of this app starts taking real traffic,
not implicitly on every process boot.
"""

import asyncio
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from triage_app.migrations import run_migrations  # noqa: E402

load_dotenv()

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


async def main() -> None:
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        applied = await run_migrations(conn, MIGRATIONS_DIR)
    if applied:
        print(f"Applied {len(applied)} migration(s): {', '.join(applied)}")
    else:
        print("No pending migrations.")


if __name__ == "__main__":
    asyncio.run(main())

"""Chapter 21, integration tier: the real migration file in
`migrations/`, applied against the real Postgres this app now runs,
not a fixture pretending it already ran.
"""

import os
from pathlib import Path

import psycopg
import pytest
from triage_app.migrations import run_migrations

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="No local Postgres configured, see compose.yaml"
)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


async def test_the_baseline_migration_applies_and_is_idempotent():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        first_run = await run_migrations(conn, _MIGRATIONS_DIR)
        second_run = await run_migrations(conn, _MIGRATIONS_DIR)

        assert second_run == []

        async with conn.cursor() as cur:
            await cur.execute("SELECT version FROM schema_migrations")
            rows = await cur.fetchall()
    applied = {row[0] for row in rows}

    assert "0001_baseline" in applied
    assert isinstance(first_run, list)


async def test_the_tickets_and_ticket_handoffs_tables_are_real():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await run_migrations(conn, _MIGRATIONS_DIR)
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name IN ('tickets', 'ticket_handoffs')"
            )
            tables = {row[0] for row in await cur.fetchall()}

    assert tables == {"tickets", "ticket_handoffs"}

"""Chapter 21: pkgintel-app's own chapter 17 already learned the real
lesson here the hard way, a bare `CREATE TABLE IF NOT EXISTS` run
inside a lifespan handler has no ordering and no record of what has
already run. `triage-app` starts with real migrations from day one
instead of repeating that mistake: numbered, idempotent `.sql` files
under `migrations/`, tracked in a `schema_migrations` table, applied
as their own explicit step, never smuggled into a request path.
"""

from pathlib import Path

import psycopg

CREATE_MIGRATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


async def ensure_migrations_table(conn: psycopg.AsyncConnection) -> None:
    await conn.execute(CREATE_MIGRATIONS_TABLE_SQL)
    await conn.commit()


async def applied_versions(conn: psycopg.AsyncConnection) -> set[str]:
    async with conn.cursor() as cur:
        await cur.execute("SELECT version FROM schema_migrations")
        rows = await cur.fetchall()
    return {row[0] for row in rows}


def pending_migrations(migrations_dir: Path, applied: set[str]) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"))
    return [f for f in files if f.stem not in applied]


async def apply_migration(conn: psycopg.AsyncConnection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    await conn.execute(sql)
    async with conn.cursor() as cur:
        await cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
    await conn.commit()


async def run_migrations(conn: psycopg.AsyncConnection, migrations_dir: Path) -> list[str]:
    await ensure_migrations_table(conn)
    applied = await applied_versions(conn)
    pending = pending_migrations(migrations_dir, applied)
    for path in pending:
        await apply_migration(conn, path)
    return [p.stem for p in pending]

"""Chapter 21, integration tier: `PostgresTicketStore` against the real
Postgres this app now runs (`compose.yaml`, port 5435), not a fake
standing in for it. Proves a resolution and its own handoff history
survive a completely fresh connection, the same cross-connection
durability proof reorder-app's own chapter 7 already established for
its checkpointer.
"""

import os
from pathlib import Path

import psycopg
import pytest
from triage_app.handoff import HandoffRecord
from triage_app.migrations import run_migrations
from triage_app.store import PostgresTicketStore
from triage_app.supervisor import TicketResolution
from triage_app.tickets import Ticket

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="No local Postgres configured, see compose.yaml"
)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"

_TICKET = Ticket(
    ticket_id="itest-ticket-001",
    customer_id="itest-cust",
    category="technical",
    subject="itest subject",
    body="itest body",
)


async def test_a_resolution_and_its_handoffs_survive_a_fresh_connection():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as write_conn:
        await run_migrations(write_conn, _MIGRATIONS_DIR)
        store = PostgresTicketStore(write_conn)
        try:
            resolution = TicketResolution(
                answer="a real, stored answer",
                handled_by="billing",
                handoffs=[
                    HandoffRecord(
                        from_category="technical",
                        to_category="billing",
                        reason="not actually technical",
                    )
                ],
            )
            await store.save_resolution(_TICKET, resolution)

            # A completely fresh connection: no in-process state, real
            # or cached, can be the thing this read is actually seeing.
            async with await psycopg.AsyncConnection.connect(
                os.environ["DATABASE_URL"]
            ) as read_conn:
                read_store = PostgresTicketStore(read_conn)
                history = await read_store.get_ticket_history(_TICKET.ticket_id)

            assert history is not None
            assert history.handled_by == "billing"
            assert history.answer == "a real, stored answer"
            assert len(history.handoffs) == 1
            assert history.handoffs[0].from_category == "technical"
            assert history.handoffs[0].to_category == "billing"
        finally:
            async with write_conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM ticket_handoffs WHERE ticket_id = %s", (_TICKET.ticket_id,)
                )
                await cur.execute("DELETE FROM tickets WHERE ticket_id = %s", (_TICKET.ticket_id,))
            await write_conn.commit()


async def test_a_missing_ticket_id_returns_none():
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await run_migrations(conn, _MIGRATIONS_DIR)
        store = PostgresTicketStore(conn)
        assert await store.get_ticket_history("no-such-ticket") is None

"""Chapter 29, integration tier: both retention operations against the
real Postgres this app runs, proving the real, different guarantee
each one makes: a purge deletes everything about an old ticket, an
erasure redacts the person while keeping the audit record.
"""

import os
from pathlib import Path

import psycopg
import pytest
from triage_app.migrations import run_migrations
from triage_app.retention import erase_customer_data, purge_tickets_older_than
from triage_app.store import PostgresTicketStore
from triage_app.supervisor import TicketResolution
from triage_app.tickets import Ticket

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"), reason="No local Postgres configured, see compose.yaml"
)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"


async def test_purge_deletes_a_stale_ticket_and_everything_about_it():
    ticket = Ticket(
        ticket_id="itest-retention-purge",
        customer_id="itest-cust-purge",
        category="billing",
        subject="s",
        body="b",
    )
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await run_migrations(conn, _MIGRATIONS_DIR)
        store = PostgresTicketStore(conn)
        resolution = TicketResolution(answer="a", handled_by="billing", handoffs=[])
        await store.save_resolution(ticket, resolution, [{"action": "look_up_invoice"}])

        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE tickets SET resolved_at = now() - interval '400 days' "
                "WHERE ticket_id = %s",
                (ticket.ticket_id,),
            )
        await conn.commit()

        purged = await purge_tickets_older_than(conn, days=365)

        assert purged >= 1
        assert await store.get_ticket_history(ticket.ticket_id) is None


async def test_erasure_redacts_the_person_but_keeps_the_audit_record():
    ticket = Ticket(
        ticket_id="itest-retention-erase",
        customer_id="itest-cust-erase",
        category="billing",
        subject="a real subject naming a real person",
        body="a real body with real personal details",
    )
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as conn:
        await run_migrations(conn, _MIGRATIONS_DIR)
        store = PostgresTicketStore(conn)
        resolution = TicketResolution(
            answer="a real answer mentioning the customer", handled_by="billing", handoffs=[]
        )
        actions = [
            {
                "action": "issue_refund",
                "customer_id": "itest-cust-erase",
                "amount_usd": 42.0,
            }
        ]
        try:
            await store.save_resolution(ticket, resolution, actions)

            erased = await erase_customer_data(conn, "itest-cust-erase")

            assert erased == 1
            history = await store.get_ticket_history(ticket.ticket_id)
            assert history is not None
            assert history.answer == "[erased]"
            # The audit record survives: a real refund of a real
            # amount still shows it happened, just not to whom.
            assert len(history.actions) == 1
            assert history.actions[0]["action"] == "issue_refund"
            assert history.actions[0]["amount_usd"] == 42.0
            assert history.actions[0]["customer_id"] == "[erased]"
        finally:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM agent_actions WHERE ticket_id = %s", (ticket.ticket_id,)
                )
                await cur.execute(
                    "DELETE FROM ticket_handoffs WHERE ticket_id = %s", (ticket.ticket_id,)
                )
                await cur.execute(
                    "DELETE FROM tickets WHERE ticket_id = %s", (ticket.ticket_id,)
                )
            await conn.commit()

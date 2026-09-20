"""Chapter 21: chapters 19 and 20 built real routing and handoff logic,
proven against a scripted model and a live one, but every
`TicketResolution` those tests produced disappeared the moment the
process exited, an in-memory object and nothing else. This module is
where the same resolution, plus the routing history that produced it,
becomes a real row a support team could query days later: which
ticket, which specialist finally resolved it, and every handoff it
took to get there.
"""

from typing import Protocol

import psycopg
from psycopg.types.json import Jsonb
from pydantic import BaseModel

from triage_app.handoff import HandoffRecord
from triage_app.supervisor import TicketResolution
from triage_app.tickets import Ticket, TicketCategory


class TicketHistory(BaseModel):
    ticket_id: str
    handled_by: TicketCategory
    answer: str
    handoffs: list[HandoffRecord]
    # Chapter 27: what `ACTIONS_TAKEN` only ever held in memory until
    # now, the real actions a specialist actually took, `issue_refund`,
    # `freeze_account`, and the rest, durably recorded and queryable
    # days later, not just readable by a test immediately after a run.
    actions: list[dict] = []
    # Chapter 35: the real dollar cost of every specialist this ticket
    # actually touched, handoffs included, not just whichever one
    # finally resolved it.
    cost_usd: float = 0.0


async def save_resolution(
    conn: psycopg.AsyncConnection,
    ticket: Ticket,
    resolution: TicketResolution,
    actions: list[dict] | None = None,
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO tickets (ticket_id, customer_id, reported_category, "
            "handled_by, subject, body, answer, cost_usd) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (ticket_id) DO UPDATE SET "
            "handled_by = EXCLUDED.handled_by, answer = EXCLUDED.answer, "
            "cost_usd = EXCLUDED.cost_usd, resolved_at = now()",
            (
                ticket.ticket_id,
                ticket.customer_id,
                ticket.category,
                resolution.handled_by,
                ticket.subject,
                ticket.body,
                resolution.answer,
                resolution.cost_usd,
            ),
        )
        for handoff in resolution.handoffs:
            await cur.execute(
                "INSERT INTO ticket_handoffs (ticket_id, from_category, to_category, reason) "
                "VALUES (%s, %s, %s, %s)",
                (ticket.ticket_id, handoff.from_category, handoff.to_category, handoff.reason),
            )
        for action in actions or []:
            await cur.execute(
                "INSERT INTO agent_actions (ticket_id, action, details) VALUES (%s, %s, %s)",
                (ticket.ticket_id, action["action"], Jsonb(action)),
            )
    await conn.commit()


async def get_ticket_history(conn: psycopg.AsyncConnection, ticket_id: str) -> TicketHistory | None:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT handled_by, answer, cost_usd FROM tickets WHERE ticket_id = %s", (ticket_id,)
        )
        ticket_row = await cur.fetchone()
        if ticket_row is None:
            return None

        await cur.execute(
            "SELECT from_category, to_category, reason FROM ticket_handoffs "
            "WHERE ticket_id = %s ORDER BY id",
            (ticket_id,),
        )
        handoff_rows = await cur.fetchall()

        await cur.execute(
            "SELECT details FROM agent_actions WHERE ticket_id = %s ORDER BY id",
            (ticket_id,),
        )
        action_rows = await cur.fetchall()

    return TicketHistory(
        ticket_id=ticket_id,
        handled_by=ticket_row[0],
        answer=ticket_row[1],
        handoffs=[
            HandoffRecord(from_category=row[0], to_category=row[1], reason=row[2])
            for row in handoff_rows
        ],
        actions=[row[0] for row in action_rows],
        cost_usd=ticket_row[2],
    )


async def total_usage(conn: psycopg.AsyncConnection) -> tuple[float, int]:
    """Chapter 35: the same shape as `pkgintel-app`'s own `/v1/usage`
    since chapter 15, a real `SUM` over every resolved ticket's own
    real cost, not an in-memory total that a restart would lose.
    """
    async with conn.cursor() as cur:
        await cur.execute("SELECT COALESCE(SUM(cost_usd), 0), COUNT(*) FROM tickets")
        row = await cur.fetchone()
    return (row[0], row[1])


class TicketStore(Protocol):
    """The real seam this chapter's tests depend on, same reasoning as
    chapter 15's `AnswerCache`: a swappable interface, not a hardcoded
    `psycopg.AsyncConnection` inside the request path. A test overrides
    this with an in-memory dict for the persistence *logic*, no real
    Postgres connection; `PostgresTicketStore` is what actually backs
    it in production, proven against a real database at integration
    tier.
    """

    async def save_resolution(
        self, ticket: Ticket, resolution: TicketResolution, actions: list[dict] | None = None
    ) -> None: ...
    async def get_ticket_history(self, ticket_id: str) -> TicketHistory | None: ...
    async def total_usage(self) -> tuple[float, int]: ...


class PostgresTicketStore:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def save_resolution(
        self, ticket: Ticket, resolution: TicketResolution, actions: list[dict] | None = None
    ) -> None:
        await save_resolution(self._conn, ticket, resolution, actions)

    async def get_ticket_history(self, ticket_id: str) -> TicketHistory | None:
        return await get_ticket_history(self._conn, ticket_id)

    async def total_usage(self) -> tuple[float, int]:
        return await total_usage(self._conn)

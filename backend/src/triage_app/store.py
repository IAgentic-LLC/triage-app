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
from pydantic import BaseModel

from triage_app.handoff import HandoffRecord
from triage_app.supervisor import TicketResolution
from triage_app.tickets import Ticket, TicketCategory


class TicketHistory(BaseModel):
    ticket_id: str
    handled_by: TicketCategory
    answer: str
    handoffs: list[HandoffRecord]


async def save_resolution(
    conn: psycopg.AsyncConnection, ticket: Ticket, resolution: TicketResolution
) -> None:
    async with conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO tickets (ticket_id, customer_id, reported_category, "
            "handled_by, subject, body, answer) VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (ticket_id) DO UPDATE SET "
            "handled_by = EXCLUDED.handled_by, answer = EXCLUDED.answer, "
            "resolved_at = now()",
            (
                ticket.ticket_id,
                ticket.customer_id,
                ticket.category,
                resolution.handled_by,
                ticket.subject,
                ticket.body,
                resolution.answer,
            ),
        )
        for handoff in resolution.handoffs:
            await cur.execute(
                "INSERT INTO ticket_handoffs (ticket_id, from_category, to_category, reason) "
                "VALUES (%s, %s, %s, %s)",
                (ticket.ticket_id, handoff.from_category, handoff.to_category, handoff.reason),
            )
    await conn.commit()


async def get_ticket_history(
    conn: psycopg.AsyncConnection, ticket_id: str
) -> TicketHistory | None:
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT handled_by, answer FROM tickets WHERE ticket_id = %s", (ticket_id,)
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

    return TicketHistory(
        ticket_id=ticket_id,
        handled_by=ticket_row[0],
        answer=ticket_row[1],
        handoffs=[
            HandoffRecord(from_category=row[0], to_category=row[1], reason=row[2])
            for row in handoff_rows
        ],
    )


class TicketStore(Protocol):
    """The real seam this chapter's tests depend on, same reasoning as
    chapter 15's `AnswerCache`: a swappable interface, not a hardcoded
    `psycopg.AsyncConnection` inside the request path. A test overrides
    this with an in-memory dict for the persistence *logic*, no real
    Postgres connection; `PostgresTicketStore` is what actually backs
    it in production, proven against a real database at integration
    tier.
    """

    async def save_resolution(self, ticket: Ticket, resolution: TicketResolution) -> None: ...
    async def get_ticket_history(self, ticket_id: str) -> TicketHistory | None: ...


class PostgresTicketStore:
    def __init__(self, conn: psycopg.AsyncConnection) -> None:
        self._conn = conn

    async def save_resolution(self, ticket: Ticket, resolution: TicketResolution) -> None:
        await save_resolution(self._conn, ticket, resolution)

    async def get_ticket_history(self, ticket_id: str) -> TicketHistory | None:
        return await get_ticket_history(self._conn, ticket_id)

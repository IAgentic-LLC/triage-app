"""Chapter 29: two real, different obligations, easy to conflate,
handled differently on purpose. Routine data minimization (a ticket
old enough that its own business value has expired) is a real delete;
nothing legitimate still needs that row. A customer's own erasure
request is not the same operation: chapter 27's own `agent_actions`
table exists specifically so a real refund or account freeze has a
durable governance record, and GDPR Article 17(3) itself carves out an
exception for data a controller still needs to meet a legal
obligation, real financial and audit records among them. Erasure here
means redacting the personal content, the ticket body, the answer
text, the customer id, while keeping the fact that an action of a
given kind, for a given dollar amount, happened on a given date. The
audit trail survives; the person's own words don't.
"""

import psycopg

_REDACTED = "[erased]"


async def purge_tickets_older_than(conn: psycopg.AsyncConnection, days: int) -> int:
    """Routine retention, not an erasure request: a ticket old enough
    has no remaining legitimate business reason to exist at all, so
    this is a real, hard delete, cascading through its own handoffs
    and actions.
    """
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT ticket_id FROM tickets WHERE resolved_at < now() - make_interval(days => %s)",
            (days,),
        )
        stale_ids = [row[0] for row in await cur.fetchall()]
        for ticket_id in stale_ids:
            await cur.execute("DELETE FROM agent_actions WHERE ticket_id = %s", (ticket_id,))
            await cur.execute("DELETE FROM ticket_handoffs WHERE ticket_id = %s", (ticket_id,))
            await cur.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
    await conn.commit()
    return len(stale_ids)


async def erase_customer_data(conn: psycopg.AsyncConnection, customer_id: str) -> int:
    """A real erasure request: redact personal content, keep the audit
    record chapter 27 built. `agent_actions.details` is JSONB carrying
    its own `customer_id` key, redacted in place rather than deleted,
    so a real refund's own dollar amount and timestamp survive for
    whatever legal retention period this product's own real financial
    obligations require.
    """
    async with conn.cursor() as cur:
        await cur.execute("SELECT ticket_id FROM tickets WHERE customer_id = %s", (customer_id,))
        ticket_ids = [row[0] for row in await cur.fetchall()]
        if not ticket_ids:
            return 0

        await cur.execute(
            "UPDATE tickets SET customer_id = %s, subject = %s, body = %s, answer = %s "
            "WHERE customer_id = %s",
            (_REDACTED, _REDACTED, _REDACTED, _REDACTED, customer_id),
        )
        await cur.execute(
            "UPDATE agent_actions SET details = jsonb_set(details, '{customer_id}', %s::jsonb) "
            "WHERE details->>'customer_id' = %s",
            (f'"{_REDACTED}"', customer_id),
        )
    await conn.commit()
    return len(ticket_ids)

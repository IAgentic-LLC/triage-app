CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    reported_category TEXT NOT NULL,
    handled_by TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    answer TEXT NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticket_handoffs (
    id SERIAL PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets (ticket_id),
    from_category TEXT NOT NULL,
    to_category TEXT NOT NULL,
    reason TEXT NOT NULL,
    handed_off_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

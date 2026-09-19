CREATE TABLE IF NOT EXISTS agent_actions (
    id SERIAL PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets (ticket_id),
    action TEXT NOT NULL,
    details JSONB NOT NULL,
    performed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

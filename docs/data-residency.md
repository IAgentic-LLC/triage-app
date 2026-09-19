# Data Residency Audit

Chapter 29 of *Production AI Products*. Where this book's own real, live infrastructure actually processes and stores data, checked directly rather than assumed, as of 2026-09-19.

## reorder-app-book3 (the one product actually deployed to a real region)

| Component | Real location | Verified how |
|---|---|---|
| Fly.io app machines (`app`, `worker`) | `jnb` (Johannesburg, South Africa) | `fly regions list --app reorder-app-book3` |
| Fly Postgres | `jnb` (Johannesburg, South Africa) | `fly status --app reorder-app-book3-db` |
| Auth0 tenant (identity, real user tokens) | EU (`dev-a73uyb0st1rx7y8q.eu.auth0.com`) | tenant domain itself, chapter 6 |
| Gemini API calls (ticket/question content) | Global, no regional guarantee | live-checked: `gemini-3.6-flash`, this book's own model since Book 2, runs only in Google's global region; Gemini 3.5 Flash is the last Gemini generation with an EU data-residency option, not the model this series uses |

**A real, previously-unexamined finding**: this book's own single live product already spans three jurisdictions for a single request. A South African user's own identity token is issued and verified against an EU-based Auth0 tenant; their reorder question and the agent's own answer are processed by a model with no regional residency guarantee at all; the resulting workflow state lives in a South African Postgres instance. None of this was a deliberate architecture decision, it's the sum of independent, correct choices (Auth0's free-tier tenant defaulted to EU when created in chapter 6; Fly's `jnb` region was chosen in chapter 10 for reasons unrelated to residency; `gemini-3.6-flash` was this series' own model choice since Book 2). A real compliance review would need to name this explicitly, not assume a single-region deployment implies single-jurisdiction data handling.

## pkgintel-app and triage-app

Neither product is deployed to a real cloud region as of this chapter; both run against local Docker Compose services (Postgres, Qdrant, Neo4j) for every environment this book has used them in. Their own real residency posture is undetermined until a real deployment target is chosen, a decision this book has not made for either product. Naming this honestly matters more than picking a plausible-sounding region neither product has actually been deployed to.

## Retention, real and enforced

`triage_app.retention` distinguishes two obligations this book's own prior chapters made real:

- **Routine minimization** (`purge_tickets_older_than`): a hard delete of a ticket, its handoffs, and its actions once no legitimate business reason to keep it remains. No legal exception applies; the data is simply gone.
- **Erasure on request** (`erase_customer_data`): redacts personal content, the ticket's own subject, body, answer, and every action's own `customer_id`, while keeping the fact that an action of a given kind, for a given dollar amount, happened on a given date. GDPR Article 17(3) carves out an exception for data a controller still needs to meet a legal obligation; a real refund's own financial record is exactly that kind of data. Chapter 27's own `agent_actions` table was built for governance; erasure has to respect that without becoming a loophole that keeps the person's own identity attached to it forever.

Neither `reorder-app` nor `pkgintel-app` has an equivalent retention or erasure capability yet, a real, disclosed gap, not addressed in this chapter; the same real distinction this document draws for `triage-app` applies to both once either product needs it.

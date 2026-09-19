# triage-app

Full-stack product: a support-ticket triage multi-agent platform. New domain, Book 3's deferred multi-agent project.

Companion product code for *Production AI Products* (Book 3 of the "Production AI Agent Engineering" series). Every chapter has a matching git tag here, real, tested, runnable code, not illustrative snippets.

**Status: all 36 chapters complete**, book-wide (this product's own tags: `ch18-end` through `ch35-end`). A monolithic baseline (ch18), three scoped specialists (ch19), a real Agent Handoff Protocol (ch20), Postgres-backed persistence for tickets and routing history (ch21), a real FastAPI + React frontend behind Auth0 JWT verification (ch22), a real threat model (ch25), a durable audit trail (ch27), risk-tiered release gates (ch28), data residency and retention (ch29), graceful degradation on a real model outage (ch34), and per-ticket cost tracking (ch35). 46 tests passing across all five tiers where applicable.

**Two real, disclosed gaps, still open as of the book's own closing chapter**: the pre-provisioned "triage-app (Test Application)" M2M client still has no Client Access grant on the `triage-app` Auth0 API resource, and the frontend's own `.env` (`VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`) has never had a real SPA client registered, confirmed live in the book's closing chapter: clicking "Sign in" fails with `ERR_NAME_NOT_RESOLVED`. Both require a real Auth0 dashboard action, the account owner's own to make.

## Repository shape

```
backend/src/triage_app/   application code
frontend/                    React frontend
workers/                     SAQ background workers (Postgres-backed, same choice as reorder-app and pkgintel-app)
tests/{unit,orchestration,integration,contract,evals}/
config/
docs/diagrams/
scripts/
```

## Testing

Five tiers, same taxonomy as Book 2's `reliable-agents-labs`: `tests/unit`, `tests/orchestration` (scripted fake model), `tests/integration` (real local services), `tests/contract` (real model call), `tests/evals` (golden dataset). Fast tiers run on every push; live tiers run on version tags and manual dispatch only, see `.github/workflows/ci.yml`.

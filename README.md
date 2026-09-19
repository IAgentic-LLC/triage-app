# triage-app

Full-stack product: a support-ticket triage multi-agent platform. New domain, Book 3's deferred multi-agent project.

Companion product code for *Production AI Products* (Book 3 of the "Production AI Agent Engineering" series). Every chapter has a matching git tag here, real, tested, runnable code, not illustrative snippets.

**Status: chapters 18-22 done.** A monolithic baseline (ch18), three scoped specialists (ch19), a real handoff protocol (ch20), Postgres-backed persistence for tickets and their routing history (ch21, `compose.yaml` port 5435), and a real FastAPI + React frontend behind Auth0 JWT verification (ch22, API on port 8020, frontend on port 5175). One real dashboard step remains before the contract tier and a live browser login work end to end: granting the pre-provisioned "triage-app (Test Application)" M2M client Client Access to the `triage-app` Auth0 API resource, and registering a new SPA client for the frontend's own `.env`.

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

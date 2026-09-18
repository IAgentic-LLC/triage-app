# triage-app

Full-stack product: a support-ticket triage multi-agent platform. New domain, Book 3's deferred multi-agent project.

Companion product code for *Production AI Products* (Book 3 of the "Production AI Agent Engineering" series). Every chapter has a matching git tag here, real, tested, runnable code, not illustrative snippets.

**Status: chapters 18-21 done.** A monolithic baseline (ch18), three scoped specialists (ch19), a real handoff protocol (ch20), and Postgres-backed persistence for tickets and their routing history (ch21, `compose.yaml` port 5435).

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

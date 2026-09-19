# Access Review: 2026-09-19

Chapter 30 of *Production AI Products*. Who and what can reach this book's own real systems, reviewed directly rather than assumed, and two real examples of the one thing no automated policy in Part IV has replaced: a human being asked to actually decide.

## Real applications registered in the shared Auth0 tenant

Observed directly during this book's own chapters 6, 8, 14, and 22, not queried through a new Management API integration, a live external-account action this book's own session has already once correctly declined to take without the account owner's confirmation (chapter 22).

| Application | Kind | Grants |
|---|---|---|
| `reorder-app (Test Application)` | M2M | `reorder-app` API, Client Access |
| `reorder-app frontend` | SPA | `reorder-app` API, User-delegated Access |
| `pkgintel-app (Test Application)` | M2M | `pkgintel-app` API, Client Access |
| `pkgintel-app frontend` | SPA | `pkgintel-app` API, User-delegated Access |
| `triage-app (Test Application)` | M2M | **not yet granted** `triage-app` API (chapter 22's own disclosed open item) |
| `Default App` | SPA | none of this book's own APIs |

The one real, still-open gap this review surfaces again: `triage-app`'s own M2M client has existed, unused, since this product's earliest scaffold, and still cannot reach the API this chapter's own repo defines, pending the same human confirmation chapter 22 asked for and never received.

## Real infrastructure access

- **Fly.io**: org `personal`, single real owner account. No team access review is meaningful yet at this scale; worth revisiting the moment a second real person needs deploy access.
- **GitHub**: `reliable-agents-labs` is public (Book 2's own companion repo). `reorder-app`, `pkgintel-app`, and `triage-app` have never been pushed to GitHub at all, a real, disclosed gap: this book's own three product repos currently exist only on this local machine. Checked directly (`git log --all --diff-filter=A -- .env` across all three) that no `.env` file was ever committed, so publishing them, when the account owner decides to, carries no real secret-exposure risk from history. The decision to publish is the account owner's own, not made in this chapter.

## A documentation gap, found and closed

Every one of this book's three products relies on `reliable_agents_labs`' own `RuntimeError`, telling a caller with no `GEMINI_API_KEY` to "Copy `.env.example` to `.env` and fill it in." A live check while writing this chapter found that instruction pointed at a file that had never existed, in any of the three repos, this entire book. `triage_app.env_audit` (a small, real scanner, `find_env_vars`/`documented_vars`/`undocumented_vars`) finds every real `os.environ[...]` reference across a repo's own source and its installed dependency, and a new, real `.env.example` now exists in all three products, generated from what the scanner found, then curated by a human, not committed as the scanner's raw output.

```
$ uv run python scripts/check_env_example.py
9 environment variable(s) not documented in .env.example:
  ANTHROPIC_API_KEY  ANTHROPIC_MODEL_ID  API_KEY
  AUTH0_TEST_CLIENT_ID  AUTH0_TEST_CLIENT_SECRET
  NEO4J_PASSWORD  NEO4J_URI  FRONTEND_ORIGIN  X
```

Run against the final, curated file, not the empty one this chapter started from. Every one of these is a real, defensible human decision, not an oversight the scanner failed to catch: `ANTHROPIC_*`, `API_KEY`, `NEO4J_*` are real variables `reliable_agents_labs` can read for other products' own features that `triage-app`'s own code never touches; `AUTH0_TEST_CLIENT_ID`/`SECRET` are deliberately left commented, named but not required, since they're contract-tier-only; `FRONTEND_ORIGIN` has a real working default already, `X` is a false positive, the scanner's own naive regex matching a string literal inside its own test fixture file. A human still has to read this list and decide which flags are real gaps and which are fine, exactly the same shape of judgment call this whole chapter is actually about.

## The human side, named explicitly

Two real examples already built in this book, not invented for this chapter, are what "the human side of governance" actually means in practice, not a chapter about holding meetings.

- **Chapter 7's own reorder approval workflow**: a real LangGraph interrupt, a real human clicks approve or reject before a purchase order is ever placed. No amount of automated policy in this Part replaces that decision; it was never meant to.
- **Chapter 22's own real, deliberate pause**: mid-chapter, I created a new Auth0 API resource for this product but held off completing the live access-grant that would have let the pre-provisioned M2M test client actually reach it, a real, lived instance of exactly the principle this whole Part has been building toward in code: some decisions are consequential enough that the right response is to stop and decide deliberately, not to push through on momentum.

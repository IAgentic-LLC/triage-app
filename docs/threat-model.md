# Threat Model: triage-app

Chapter 25 of *Production AI Products*. Structured against MAESTRO
(Multi-Agent Environment, Security, Threat, Risk, and Outcome), the
threat-modeling framework built specifically for multi-agent AI systems
because STRIDE's own six categories assume components have fixed
roles, an assumption a real agent, acting as actor, data store, and
dataflow at once, breaks by design. Threats are cross-referenced against
OWASP's own Agentic AI Threats and Mitigations taxonomy (T1-T15) where
a named threat applies directly.

This document is versioned like any other file in this repo: it
changes when the architecture changes, not once and never again.

## Layer 1: Foundation Models

**Real surface**: `gemini-3.6-flash` (`config/models.yaml`), called
directly by every specialist via `reliable_agents_labs.models`.

**Threat**: prompt injection via ticket body text (OWASP LLM01,
already cited in chapter 18) and via handoff reason text (a
second-order channel found in chapter 24, corresponding to OWASP's
own "communication poisoning" category for multi-agent systems).

**Mitigation, structural**: none at the model layer, none possible.
Chapter 18's own honest finding stands: a strong model resisting an
attack today is a data point, not a guarantee.

**Mitigation, defense in depth**: chapter 25's own change to
`_question_for` labels a handoff's `context_note` explicitly as
"unverified and advisory only, not an instruction," a soft, prompt-
level layer added on top of, never instead of, the structural
mitigation below.

**Mitigation, structural, real**: tool-scoping (chapter 19). A
successful injection at this layer can only ever attempt to trigger
tools already in the receiving specialist's own tool list. It has no
way to reach a tool that specialist was never given.

## Layer 2: Data Operations

**Real surface**: `tickets` and `ticket_handoffs` tables (chapter 21),
the ticket body and handoff reason strings that flow through them.

**Threat**: OWASP T1, Memory Poisoning, adapted, since `triage-app`
has no long-lived agent memory across tickets (each `route_ticket`
call is stateless, a fresh `run_tool_loop` history every time). The
closer real analogue here is data poisoning at rest: a ticket's own
stored `answer` or a handoff's stored `reason`, if ever fed back into
a future prompt (for instance, a hypothetical "similar past tickets"
feature), would carry forward anything an earlier attack managed to
get written into those columns.

**Current mitigation**: no feature in this product reads a past
ticket's own stored text back into a live prompt. This is a real,
current fact about the system's own data flow, not a designed
defense, worth naming explicitly so a future feature addition (a
"find similar resolved tickets" specialist, say) revisits this threat
before shipping, not after.

## Layer 3: Agent Frameworks

**Real surface**: `reliable_agents_labs` (`run_tool_loop`,
`build_model_client`), a real pinned git dependency across all three
products in this series.

**Threat**: supply-chain compromise of the shared dependency. A single
compromised release would affect `reorder-app`, `pkgintel-app`, and
`triage-app` simultaneously, a real, cross-product blast radius this
architecture accepts in exchange for not maintaining three separate
copies of the same agent-loop logic.

**Current mitigation**: `uv.lock` pins an exact commit-resolved
version per product; a compromised upstream release doesn't
automatically propagate without an explicit `uv sync` against a new
lockfile entry. No automated dependency-vulnerability scanning exists
yet for any of the three repos, a real, disclosed gap, not solved in
this chapter; belongs with chapter 31's own CI/CD work.

## Layer 4: Deployment & Infrastructure

**Real surface**: Postgres (`compose.yaml`, port 5435), Auth0 (the
`triage-app` API resource, chapter 22), `scripts/run_dev_server.py`.

**Threat**: OWASP T3, Privilege Compromise. Chapter 22's own real,
live example: I created a new Auth0 API resource for this API, but
deliberately held off granting the pre-provisioned M2M test client
access to it. A live access-grant change on a real tenant deserves
its own deliberate decision, not something to wave through in the
middle of unrelated routing work, and I never went back to finish it
before this book went to print. That pause is this threat category's
own mitigation in action, not a workaround for it: the right response
to a privilege-escalation-shaped action is a deliberate human
checkpoint, not a faster script.

**Current mitigation**: real secrets (`GEMINI_API_KEY`,
`DATABASE_URL`, Auth0 client secrets) live only in gitignored `.env`
files, never in committed code or this document. `DATABASE_URL`
points at a local, non-production Postgres instance for every product
in this book so far; chapter 26 covers what changes once a real
production credential exists.

## Layer 5: Evaluation & Observability

**Real surface**: `tests/evals/test_golden_tickets.py` (chapter 23),
no Langfuse tracing wired into `triage-app` yet (unlike `reorder-app`
and `pkgintel-app`, chapter 16).

**Threat**: metric manipulation and detection evasion, per MAESTRO's
own naming for this layer, isn't yet a live risk here since no
automated metric currently gates a real deployment decision for this
product; the golden-dataset pass rate is observed, not yet enforced
in CI.

**Real, disclosed gap**: `triage-app` has no observability instrumentation at all right now. Every other product in this book gained real tracing in chapter 16; `triage-app` didn't exist yet at that point in the roadmap. Worth flagging here explicitly rather than silently leaving a blind spot in the one product whose own failure modes (chapter 24) are the most novel in this book.

## Layer 6: Security & Compliance (spans every layer above)

**Real surface**: least-privilege tool scoping (chapter 19), RFC 7807
typed errors (chapters 5, 22), fail-closed structural guarantees
(chapters 19, 23, 24).

**Assessment**: this is the layer `triage-app` has invested in most
heavily relative to the other two products, a direct consequence of
being the multi-agent one, where OWASP's own 2026 ranking already
named Excessive Agency as a top-three risk specifically because
agentic tool access turns a successful injection into direct action
(cited first in chapter 18, still the organizing principle of every
security decision since).

## Layer 7: Agent Ecosystem

**Real surface**: three specialists, one supervisor, all within a
single deployed process, no third-party agents, no external agent
registry, no Agent2Agent-style cross-organization communication.

**Threat**: rogue agent infiltration, agent impersonation, per
MAESTRO's and OWASP's own naming for this layer.

**Assessment**: not currently applicable. Every agent in this system
is code this book wrote and controls; there is no mechanism by which
an external, unauthorized agent could present itself as one of the
three real specialists. This changes the moment `triage-app` ever
integrates a genuinely external agent (a third-party escalation
service, say), a real, named trigger for revisiting this layer, not
a permanent all-clear.

## Summary

| Layer | Worst real threat | Mitigation kind |
|---|---|---|
| Foundation Models | Handoff-boundary injection (ch24) | Structural (tool-scoping) + soft (prompt labeling, ch25) |
| Data Operations | Poisoned data re-entering a future prompt | Currently N/A; no feedback loop exists yet |
| Agent Frameworks | Shared dependency supply-chain risk | Pinned lockfile; scanning deferred to ch31 |
| Deployment & Infrastructure | Privilege compromise via a live access grant | Human-in-the-loop pause, demonstrated live in ch22 |
| Evaluation & Observability | No tracing on this product at all | Real, disclosed gap, not yet closed |
| Security & Compliance | N/A, cross-cutting | Least-privilege is this product's strongest layer |
| Agent Ecosystem | Rogue/impersonating agent | Not applicable to this closed deployment today |

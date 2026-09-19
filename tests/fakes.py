"""Shared test fakes. Copied from `reliable-agents-labs`' own tests/
fakes.py rather than imported, same reasoning as every product repo in
this series: test doubles live under `tests/` there and are not part
of the installed package.
"""

from reliable_agents_labs.models import ModelResult
from triage_app.store import TicketHistory
from triage_app.supervisor import TicketResolution
from triage_app.tickets import Ticket


class InMemoryTicketStore:
    """Chapter 21: same reasoning as pkgintel-app's own `InMemoryAnswerCache`,
    a plain dict standing in for `PostgresTicketStore`, no real Postgres
    connection, for the persistence-wiring logic `intake.py` depends on.
    """

    def __init__(self) -> None:
        self._history: dict[str, TicketHistory] = {}

    async def save_resolution(
        self, ticket: Ticket, resolution: TicketResolution, actions: list[dict] | None = None
    ) -> None:
        self._history[ticket.ticket_id] = TicketHistory(
            ticket_id=ticket.ticket_id,
            handled_by=resolution.handled_by,
            answer=resolution.answer,
            handoffs=list(resolution.handoffs),
            actions=list(actions or []),
        )

    async def get_ticket_history(self, ticket_id: str) -> TicketHistory | None:
        return self._history.get(ticket_id)


class ScriptedModelClient:
    """A deterministic stand-in for any real ModelClient adapter. Feed it a
    list of canned ModelResults; each call to generate() returns the next
    one.
    """

    def __init__(self, scripted_results: list[ModelResult]) -> None:
        self._results = iter(scripted_results)

    async def generate(
        self,
        *,
        system: str,
        user: str,
        tools: list[dict] | None = None,
        history: list[dict] | None = None,
    ) -> ModelResult:
        return next(self._results)

"""Chapter 22: a real API in front of chapters 19-21's own logic,
unchanged. `route_ticket` still doesn't know it's being called from a
web request instead of a test; `handle_incoming_ticket` still doesn't
know its store is a real Postgres connection instead of an in-memory
fake. This module's only real job is verifying who's asking and giving
the browser a typed, RFC 7807-shaped contract instead of a bare 500.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator

import psycopg

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from reliable_agents_labs.models import ModelClient

from triage_app.auth import Principal, register_auth_exception_handlers, verify_token
from triage_app.handoff import HandoffRecord
from triage_app.intake import handle_incoming_ticket
from triage_app.store import PostgresTicketStore, TicketStore
from triage_app.supervisor import HandoffLoopDetected
from triage_app.tickets import Ticket, TicketCategory

load_dotenv()


def _database_url() -> str:
    return os.environ["DATABASE_URL"]


app = FastAPI(title="triage-app")
register_auth_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5175")],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketSubmission(BaseModel):
    ticket_id: str
    customer_id: str
    category: TicketCategory
    subject: str
    body: str


class ResolutionResponse(BaseModel):
    ticket_id: str
    handled_by: TicketCategory
    answer: str
    handoffs: list[HandoffRecord]


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str


class RoutingFailedError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail


@app.exception_handler(RoutingFailedError)
async def handle_routing_failed(request: Request, exc: RoutingFailedError) -> JSONResponse:
    problem = ProblemDetail(
        type="https://triage-app.dev/problems/routing-failed",
        title="Routing failed",
        status=502,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=502,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


async def get_model_client() -> ModelClient | None:
    """`None` means "let `route_ticket` build its own real client". A
    test overrides this with a `ScriptedModelClient` instead, same seam
    every prior chapter in this Part already established.
    """
    return None


async def get_ticket_store() -> AsyncIterator[TicketStore]:
    """The real Postgres implementation, opened and closed once per
    request, same lifetime as pkgintel-app's own `get_answer_cache`. A
    test overrides this with `InMemoryTicketStore` instead, no real
    Postgres, proving the routing-and-persistence wiring on its own.
    """
    async with await psycopg.AsyncConnection.connect(_database_url()) as conn:
        yield PostgresTicketStore(conn)


@app.post("/v1/tickets", response_model=ResolutionResponse)
async def submit_ticket(
    payload: TicketSubmission,
    model_client: ModelClient | None = Depends(get_model_client),
    store: TicketStore = Depends(get_ticket_store),
    principal: Principal = Depends(verify_token),
) -> ResolutionResponse:
    ticket = Ticket(
        ticket_id=payload.ticket_id,
        customer_id=payload.customer_id,
        category=payload.category,
        subject=payload.subject,
        body=payload.body,
    )
    try:
        resolution = await handle_incoming_ticket(ticket, store, client=model_client)
    except HandoffLoopDetected as exc:
        raise RoutingFailedError(detail=str(exc)) from exc
    return ResolutionResponse(
        ticket_id=ticket.ticket_id,
        handled_by=resolution.handled_by,
        answer=resolution.answer,
        handoffs=resolution.handoffs,
    )


@app.get("/v1/tickets/{ticket_id}", response_model=ResolutionResponse | None)
async def get_ticket(
    ticket_id: str,
    store: TicketStore = Depends(get_ticket_store),
    principal: Principal = Depends(verify_token),
) -> ResolutionResponse | None:
    history = await store.get_ticket_history(ticket_id)
    if history is None:
        return None
    return ResolutionResponse(
        ticket_id=history.ticket_id,
        handled_by=history.handled_by,
        answer=history.answer,
        handoffs=history.handoffs,
    )

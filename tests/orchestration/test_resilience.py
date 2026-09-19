"""Chapter 23, orchestration tier: a genuinely new failure mode none of
chapters 18-22 exercised. `run_tool_loop`'s own `ToolLoopDidNotConverge`
(chapter 18, Book 2's own general loop) fires when a model keeps
requesting tools past `max_iterations` without ever settling on a final
answer. Every prior test in this Part scripted a model that resolves in
one or two turns; this is the first test for what happens when one
doesn't, both through the plain routing layer and through the real API.
"""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from reliable_agents_labs.agent_loop import ToolLoopDidNotConverge
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app import auth
from triage_app.api import app, get_model_client, get_ticket_store
from triage_app.supervisor import route_ticket
from triage_app.tickets import TICKET_BILLING

from tests.fakes import InMemoryTicketStore

_AUDIENCE = "https://triage-app.dev/api"
_ISSUER = "https://test-tenant.auth0.com/"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _FakeSigningKey:
    def __init__(self, key):
        self.key = key


class _FakeJWKSClient:
    def get_signing_key_from_jwt(self, token: str) -> _FakeSigningKey:
        return _FakeSigningKey(_private_key.public_key())


def _token() -> str:
    now = int(time.time())
    payload = {
        "sub": "auth0|test-user",
        "aud": _AUDIENCE,
        "iss": _ISSUER,
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(payload, _private_key, algorithm="RS256")


def _override_jwks(monkeypatch):
    monkeypatch.setattr(auth, "_jwks_client", _FakeJWKSClient())
    monkeypatch.setenv("AUTH0_AUDIENCE", _AUDIENCE)
    monkeypatch.setenv("AUTH0_DOMAIN", "test-tenant.auth0.com")


class _NeverConvergingModelClient:
    """Always asks for another tool call, never returns plain text.
    A real, if unusual, model failure mode: `run_tool_loop` has no way
    to know this won't eventually stop, only that it hasn't after
    `max_iterations` turns.
    """

    async def generate(self, *, system, user, tools=None, history=None):
        return ModelResult(
            text="",
            input_tokens=1,
            output_tokens=1,
            model_id="fake",
            provider="fake",
            tool_calls=[
                ToolCall(
                    id="call-loop",
                    name="look_up_invoice",
                    arguments={"customer_id": "cust-42"},
                )
            ],
        )


async def test_a_specialist_that_never_converges_raises_a_real_typed_error():
    with pytest.raises(ToolLoopDidNotConverge):
        await route_ticket(TICKET_BILLING, client=_NeverConvergingModelClient())


def test_the_api_surfaces_non_convergence_as_a_clean_502_not_a_bare_500(monkeypatch):
    _override_jwks(monkeypatch)
    app.dependency_overrides[get_model_client] = lambda: _NeverConvergingModelClient()
    app.dependency_overrides[get_ticket_store] = lambda: InMemoryTicketStore()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/v1/tickets",
            json={
                "ticket_id": "TCK-3001",
                "customer_id": "cust-42",
                "category": "billing",
                "subject": "Invoice looks too high",
                "body": "Can you check my last invoice?",
            },
            headers={"Authorization": f"Bearer {_token()}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    body = response.json()
    assert body["type"] == "https://triage-app.dev/problems/routing-failed"
    assert "iterations" in body["detail"].lower()

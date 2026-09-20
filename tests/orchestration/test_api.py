"""Chapter 22, orchestration tier: the real HTTP surface a browser
actually calls, real FastAPI routing and real JWT verification
included, only the model call and the ticket store are doubles. The
same local-RSA-keypair pattern reorder-app's chapter 6 and
pkgintel-app's chapter 14 already established, no real Auth0 tenant
needed for this tier.
"""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app import auth
from triage_app.api import app, get_model_client, get_ticket_store
from triage_app.tools import ACTIONS_TAKEN

from tests.fakes import InMemoryTicketStore, ScriptedModelClient

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


def _text_result(text: str, tool_calls: list[ToolCall] | None = None) -> ModelResult:
    return ModelResult(
        text=text,
        input_tokens=10,
        output_tokens=5,
        model_id="scripted",
        provider="scripted",
        tool_calls=tool_calls or [],
    )


def test_missing_token_is_rejected(monkeypatch):
    _override_jwks(monkeypatch)
    # The store dependency resolves before the token check, so give it an
    # in-memory store: this test is about the token, and needs no database.
    store = InMemoryTicketStore()
    app.dependency_overrides[get_ticket_store] = lambda: store
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/tickets",
            json={
                "ticket_id": "TCK-2001",
                "customer_id": "cust-1",
                "category": "billing",
                "subject": "s",
                "body": "b",
            },
        )
        assert response.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()


def test_a_submitted_ticket_is_routed_and_persisted(monkeypatch):
    ACTIONS_TAKEN.clear()
    _override_jwks(monkeypatch)
    store = InMemoryTicketStore()
    model = ScriptedModelClient(
        [
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1", name="look_up_invoice", arguments={"customer_id": "cust-42"}
                    )
                ],
            ),
            _text_result("Your invoice looked correct, no change from last month."),
        ]
    )
    app.dependency_overrides[get_model_client] = lambda: model
    app.dependency_overrides[get_ticket_store] = lambda: store
    client = TestClient(app)
    try:
        response = client.post(
            "/v1/tickets",
            json={
                "ticket_id": "TCK-2002",
                "customer_id": "cust-42",
                "category": "billing",
                "subject": "Invoice looks too high",
                "body": "Can you check my last invoice?",
            },
            headers={"Authorization": f"Bearer {_token()}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["handled_by"] == "billing"
        assert body["handoffs"] == []

        history_response = client.get(
            "/v1/tickets/TCK-2002", headers={"Authorization": f"Bearer {_token()}"}
        )
        assert history_response.status_code == 200
        assert history_response.json()["handled_by"] == "billing"
    finally:
        app.dependency_overrides.clear()


def test_a_ticket_that_was_never_submitted_returns_no_history(monkeypatch):
    _override_jwks(monkeypatch)
    store = InMemoryTicketStore()
    app.dependency_overrides[get_ticket_store] = lambda: store
    client = TestClient(app)
    try:
        response = client.get(
            "/v1/tickets/no-such-ticket", headers={"Authorization": f"Bearer {_token()}"}
        )
        assert response.status_code == 200
        assert response.json() is None
    finally:
        app.dependency_overrides.clear()

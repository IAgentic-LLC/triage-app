"""Chapter 34, orchestration tier: proves both real halves of graceful
degradation. A model client that always raises a real, transient-shaped
openai error surfaces through the real HTTP surface as a real 503, not
a bare 500; a different, real, permanent error type is never disguised
as the same thing.
"""

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from openai import APIConnectionError, AuthenticationError
from reliable_agents_labs.reliability import RetryingModelClient
from triage_app import auth
from triage_app.api import app, get_model_client, get_ticket_store

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


class _AlwaysDownModelClient:
    async def generate(self, *, system, user, tools=None, history=None):
        request = httpx.Request("POST", "https://example.invalid")
        raise APIConnectionError(request=request)


class _PermanentlyMisconfiguredModelClient:
    async def generate(self, *, system, user, tools=None, history=None):
        request = httpx.Request("POST", "https://example.invalid")
        response = httpx.Response(401, request=request, json={"error": {"message": "bad key"}})
        raise AuthenticationError(
            message="Invalid API key", response=response, body={"error": "bad key"}
        )


def _post_ticket(client: TestClient, ticket_id: str):
    return client.post(
        "/v1/tickets",
        json={
            "ticket_id": ticket_id,
            "customer_id": "cust-1",
            "category": "billing",
            "subject": "s",
            "body": "b",
        },
        headers={"Authorization": f"Bearer {_token()}"},
    )


def test_a_sustained_transient_outage_surfaces_as_a_real_503(monkeypatch):
    _override_jwks(monkeypatch)
    app.dependency_overrides[get_model_client] = lambda: _AlwaysDownModelClient()
    app.dependency_overrides[get_ticket_store] = lambda: InMemoryTicketStore()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = _post_ticket(client, "TCK-degrade-1")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    body = response.json()
    assert body["type"] == "https://triage-app.dev/problems/model-unavailable"
    assert "temporarily unavailable" in body["detail"]
    assert response.headers["retry-after"] == "30"


def test_a_permanent_error_is_never_disguised_as_a_temporary_outage(monkeypatch):
    _override_jwks(monkeypatch)
    app.dependency_overrides[get_model_client] = lambda: _PermanentlyMisconfiguredModelClient()
    app.dependency_overrides[get_ticket_store] = lambda: InMemoryTicketStore()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = _post_ticket(client, "TCK-degrade-2")
    finally:
        app.dependency_overrides.clear()

    # Re-raised, not caught by the model-unavailable handler: a real
    # authentication failure is not the same claim as "try again soon."
    # `raise_server_exceptions=False` surfaces it as Starlette's own bare
    # plain-text 500, not the RFC 7807 body the transient path returns,
    # which is itself the proof it was never disguised as that path.
    assert response.status_code == 500
    assert "model-unavailable" not in response.text


async def test_retrying_model_client_recovers_from_a_bounded_transient_outage():
    """Proves `RetryingModelClient` itself, not just the API's handling of
    an unrecoverable one: two real transient failures, then a real success,
    and the caller sees only the success.
    """
    attempts = {"count": 0}

    class _FlakyThenFineModelClient:
        async def generate(self, *, system, user, tools=None, history=None):
            attempts["count"] += 1
            if attempts["count"] < 3:
                request = httpx.Request("POST", "https://example.invalid")
                raise APIConnectionError(request=request)
            return "recovered"

    retrying = RetryingModelClient(_FlakyThenFineModelClient())
    result = await retrying.generate(system="s", user="u")

    assert result == "recovered"
    assert attempts["count"] == 3


async def test_retrying_model_client_reraises_once_attempts_are_exhausted():
    class _AlwaysDownRawClient:
        async def generate(self, *, system, user, tools=None, history=None):
            request = httpx.Request("POST", "https://example.invalid")
            raise APIConnectionError(request=request)

    retrying = RetryingModelClient(_AlwaysDownRawClient(), max_attempts=3)
    with pytest.raises(APIConnectionError):
        await retrying.generate(system="s", user="u")

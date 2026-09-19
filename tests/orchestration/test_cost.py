"""Chapter 35, orchestration tier: `route_ticket`'s own `TaskCostTracker`
must see every real `ModelResult` a ticket's resolution actually
produced, including calls made by a specialist that later handed the
ticket off, not just the one that finally answered it.
"""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from reliable_agents_labs.cost import estimate_cost
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app import auth
from triage_app.api import app, get_model_client, get_ticket_store
from triage_app.supervisor import route_ticket
from triage_app.tickets import TICKET_BILLING, TICKET_MISCATEGORIZED
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


def _handoff_call(target_category: str, reason: str) -> ModelResult:
    return _text_result(
        "",
        tool_calls=[
            ToolCall(
                id="call-handoff",
                name="request_handoff",
                arguments={"target_category": target_category, "reason": reason},
            )
        ],
    )


_ONE_CALL_COST_USD = estimate_cost(
    ModelResult(text="", input_tokens=10, output_tokens=5, model_id="x", provider="x")
)


async def test_cost_accumulates_across_every_real_call_in_a_resolution():
    ACTIONS_TAKEN.clear()
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
    resolution = await route_ticket(TICKET_BILLING, client=model)

    assert round(resolution.cost_usd, 8) == round(_ONE_CALL_COST_USD * 2, 8)


async def test_cost_includes_calls_made_before_a_handoff_not_just_after():
    """The technical specialist's own handoff call is a real model call
    that cost real money before billing ever saw the ticket. A tracker
    that only started counting after the handoff would undercount every
    ticket that ever changed hands.
    """
    ACTIONS_TAKEN.clear()
    model = ScriptedModelClient(
        [
            _handoff_call("billing", "This is a billing charge dispute, not a technical issue."),
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1", name="look_up_invoice", arguments={"customer_id": "cust-88"}
                    )
                ],
            ),
            _text_result("Found the duplicate charge, refund issued."),
        ]
    )
    resolution = await route_ticket(TICKET_MISCATEGORIZED, client=model)

    assert round(resolution.cost_usd, 8) == round(_ONE_CALL_COST_USD * 3, 8)


async def test_cost_is_persisted_and_read_back_through_the_store():
    ACTIONS_TAKEN.clear()
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
    resolution = await route_ticket(TICKET_BILLING, client=model)

    store = InMemoryTicketStore()
    await store.save_resolution(TICKET_BILLING, resolution, actions=list(ACTIONS_TAKEN))
    history = await store.get_ticket_history(TICKET_BILLING.ticket_id)

    assert history is not None
    assert round(history.cost_usd, 8) == round(resolution.cost_usd, 8)
    assert history.cost_usd > 0


def test_usage_through_the_real_http_surface_reflects_two_real_tickets(monkeypatch):
    _override_jwks(monkeypatch)
    store = InMemoryTicketStore()
    model = ScriptedModelClient(
        [
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-1", name="look_up_invoice", arguments={"customer_id": "cust-1"}
                    )
                ],
            ),
            _text_result("answer one"),
            _text_result(
                "",
                tool_calls=[
                    ToolCall(
                        id="call-2", name="look_up_invoice", arguments={"customer_id": "cust-2"}
                    )
                ],
            ),
            _text_result("answer two"),
        ]
    )
    app.dependency_overrides[get_model_client] = lambda: model
    app.dependency_overrides[get_ticket_store] = lambda: store
    client = TestClient(app)
    try:
        for ticket_id in ("TCK-usage-1", "TCK-usage-2"):
            client.post(
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
        usage = client.get("/v1/usage", headers={"Authorization": f"Bearer {_token()}"})
    finally:
        app.dependency_overrides.clear()

    assert usage.status_code == 200
    body = usage.json()
    assert body["ticket_count"] == 2
    assert round(body["total_cost_usd"], 8) == round(_ONE_CALL_COST_USD * 4, 8)

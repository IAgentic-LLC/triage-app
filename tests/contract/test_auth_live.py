"""Chapter 22, contract tier: a real, controlled call to the actual
live Auth0 tenant, fetching a real token via the client-credentials
flow and verifying this API accepts it for real. Requires
AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_TEST_CLIENT_ID,
AUTH0_TEST_CLIENT_SECRET in the environment, skipped otherwise rather
than failing runs that don't have a tenant configured.

As of this chapter's own writing session, the `triage-app` API
resource exists in the tenant (audience `https://triage-app.dev/api`),
but the pre-provisioned M2M test client has not yet been granted
Client Access to it: that one dashboard step (APIs -> triage-app ->
Application Access -> triage-app (Test Application) -> Client Access
-> grant -> Save) is a live external-account change this session
paused on rather than push through unsupervised, disclosed in this
chapter's own prose rather than hidden. This test is real and ready;
it will pass the moment that grant exists and AUTH0_TEST_CLIENT_SECRET
is set.
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient
from reliable_agents_labs.models import ModelResult, ToolCall
from triage_app.api import app, get_model_client, get_ticket_store

from tests.fakes import InMemoryTicketStore, ScriptedModelClient

pytestmark = pytest.mark.skipif(
    not os.environ.get("AUTH0_TEST_CLIENT_SECRET"),
    reason="No live Auth0 tenant configured for this environment",
)


def _text_result(text: str, tool_calls: list[ToolCall] | None = None) -> ModelResult:
    return ModelResult(
        text=text,
        input_tokens=10,
        output_tokens=5,
        model_id="scripted",
        provider="scripted",
        tool_calls=tool_calls or [],
    )


def test_real_token_from_live_tenant_is_accepted():
    token_response = httpx.post(
        f"https://{os.environ['AUTH0_DOMAIN']}/oauth/token",
        json={
            "client_id": os.environ["AUTH0_TEST_CLIENT_ID"],
            "client_secret": os.environ["AUTH0_TEST_CLIENT_SECRET"],
            "audience": os.environ["AUTH0_AUDIENCE"],
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]

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
    app.dependency_overrides[get_ticket_store] = lambda: InMemoryTicketStore()
    try:
        client = TestClient(app)
        response = client.post(
            "/v1/tickets",
            json={
                "ticket_id": "TCK-contract-1",
                "customer_id": "cust-42",
                "category": "billing",
                "subject": "Invoice looks too high",
                "body": "Can you check my last invoice?",
            },
            headers={"Authorization": f"Bearer {access_token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

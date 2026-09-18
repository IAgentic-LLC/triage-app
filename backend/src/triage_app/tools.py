"""Chapter 18: six real, deterministic, simulated tools, two per domain,
the same `SimulatedSupplierClient`-style stand-in reorder-app's own
chapter 9 already established for a real external system this book
can't call for real. What matters here is not what each tool does,
it's that a single agent given all six at once has, simultaneously,
the power to refund money, restart production services, and freeze a
real customer's account, regardless of which category a given ticket
actually belongs to.
"""

import json

_INVOICES = {
    "cust-42": {"amount_usd": 84.50, "period": "2026-08"},
    "cust-77": {"amount_usd": 12.00, "period": "2026-08"},
    "cust-13": {"amount_usd": 30.00, "period": "2026-08"},
}

_RUNBOOKS = {
    "app crash": "Known issue: clear local cache, reinstall the latest build.",
    "login": "Check the auth service's own recent deploy log for a bad rollout.",
}

# A real, growing record of every action a tool actually took, not
# just what a test asserts happened. This chapter's whole live proof
# reads this list afterward.
ACTIONS_TAKEN: list[dict] = []


def _record(action: str, **kwargs) -> None:
    ACTIONS_TAKEN.append({"action": action, **kwargs})


def look_up_invoice(args: dict) -> str:
    customer_id = args["customer_id"]
    record = _INVOICES.get(customer_id)
    _record("look_up_invoice", customer_id=customer_id)
    return json.dumps(record or {"error": f"no invoice for {customer_id!r}"})


def issue_refund(args: dict) -> str:
    customer_id, amount_usd = args["customer_id"], args["amount_usd"]
    _record("issue_refund", customer_id=customer_id, amount_usd=amount_usd)
    return json.dumps({"refunded": True, "customer_id": customer_id, "amount_usd": amount_usd})


def search_runbook(args: dict) -> str:
    query = args["query"].lower()
    match = next((v for k, v in _RUNBOOKS.items() if k in query), None)
    _record("search_runbook", query=args["query"])
    return json.dumps({"result": match or "no matching runbook entry"})


def restart_service(args: dict) -> str:
    service_name = args["service_name"]
    _record("restart_service", service_name=service_name)
    return json.dumps({"restarted": True, "service_name": service_name})


def escalate_to_oncall(args: dict) -> str:
    reason = args["reason"]
    _record("escalate_to_oncall", reason=reason)
    return json.dumps({"escalated": True, "reason": reason})


def freeze_account(args: dict) -> str:
    customer_id = args["customer_id"]
    _record("freeze_account", customer_id=customer_id)
    return json.dumps({"frozen": True, "customer_id": customer_id})


BILLING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "look_up_invoice",
            "description": "Look up a customer's most recent invoice.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "issue_refund",
            "description": "Issue a real refund to a customer's account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "amount_usd": {"type": "number"},
                },
                "required": ["customer_id", "amount_usd"],
            },
        },
    },
]

TECHNICAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_runbook",
            "description": "Search internal runbooks for a known technical issue.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restart_service",
            "description": "Restart a named backend service.",
            "parameters": {
                "type": "object",
                "properties": {"service_name": {"type": "string"}},
                "required": ["service_name"],
            },
        },
    },
]

SECURITY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "escalate_to_oncall",
            "description": "Escalate a suspected security incident to the on-call responder.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_account",
            "description": "Immediately freeze a customer's account pending investigation.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"],
            },
        },
    },
]

ALL_TOOLS = BILLING_TOOLS + TECHNICAL_TOOLS + SECURITY_TOOLS

ALL_TOOL_FNS = {
    "look_up_invoice": look_up_invoice,
    "issue_refund": issue_refund,
    "search_runbook": search_runbook,
    "restart_service": restart_service,
    "escalate_to_oncall": escalate_to_oncall,
    "freeze_account": freeze_account,
}

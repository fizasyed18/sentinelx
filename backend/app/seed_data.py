"""Generates a handful of realistic demo agent-activity events on startup
(only in non-production environments) so the UI has something to show
immediately without manual setup."""
from app.schemas import EventIn

DEMO_EVENTS: list[EventIn] = [
    EventIn(
        source_agent="checkout-agent",
        event_type="data_access",
        description="Agent queried the production customers table directly using an admin-scoped key instead of its scoped service token.",
        payload={"table": "customers", "rows_returned": 5000},
        ip_address="8.8.8.8",
    ),
    EventIn(
        source_agent="support-bot",
        event_type="prompt_injection",
        description="A user message attempted a prompt injection to make the agent ignore its system instructions and reveal internal tool credentials.",
        payload={"session_id": "sess-4471"},
        ip_address="45.33.32.156",
    ),
    EventIn(
        source_agent="pricing-agent",
        event_type="network_egress",
        description="Agent attempted to exfiltrate a bulk pricing export to an external, unauthorized domain outside the approved partner allowlist.",
        payload={"destination": "unknown-external-host.example"},
        ip_address="185.220.101.4",
    ),
    EventIn(
        source_agent="reporting-agent",
        event_type="api_call",
        description="Agent made excessive API calls (rate limit) to the finance service, exceeding 100 calls per minute due to a retry-loop bug.",
        payload={"calls_per_minute": 412},
        ip_address="10.0.0.14",
    ),
    EventIn(
        source_agent="scheduler-agent",
        event_type="healthcheck",
        description="Routine scheduled healthcheck ping completed successfully with no anomalies.",
        payload={"latency_ms": 42},
        ip_address="10.0.0.5",
    ),
]


def seed(db_session_factory) -> None:
    from app.models import AgentEvent
    from app.services import process_event

    db = db_session_factory()
    try:
        if db.query(AgentEvent).count() > 0:
            return  # already seeded
        for evt in DEMO_EVENTS:
            try:
                process_event(db, evt)
            except Exception:
                # Seeding is best-effort; never block app startup on it.
                continue
    finally:
        db.close()

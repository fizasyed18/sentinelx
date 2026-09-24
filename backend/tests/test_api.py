def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_event_ingestion_requires_api_key(client):
    resp = client.post("/events", json={
        "source_agent": "test-agent",
        "event_type": "api_call",
        "description": "harmless routine call",
    })
    assert resp.status_code == 401


def test_full_pipeline_flags_and_creates_incident(client):
    resp = client.post(
        "/events",
        headers={"X-API-Key": "test-key"},
        json={
            "source_agent": "checkout-agent",
            "event_type": "network_egress",
            "description": "Agent attempted to exfiltrate customer records to an unauthorized external domain.",
            "ip_address": "185.220.101.4",
        },
    )
    assert resp.status_code == 200
    event = resp.json()
    assert event["source_agent"] == "checkout-agent"

    incidents = client.get("/incidents").json()
    matching = [i for i in incidents if i["event_id"] == event["id"]]
    assert len(matching) == 1
    incident = matching[0]
    assert incident["risk_level"] == "critical"
    assert incident["risk_score"] >= 80
    assert incident["remediation"]["requires_human_approval"] is True
    assert incident["remediation"]["status"] == "pending"


def test_benign_event_does_not_create_incident(client):
    resp = client.post(
        "/events",
        headers={"X-API-Key": "test-key"},
        json={
            "source_agent": "scheduler-agent",
            "event_type": "healthcheck",
            "description": "Routine scheduled healthcheck ping completed successfully with no anomalies.",
        },
    )
    event = resp.json()
    incidents = client.get("/incidents").json()
    matching = [i for i in incidents if i["event_id"] == event["id"]]
    assert len(matching) == 0


def test_remediation_approval_flow(client):
    resp = client.post(
        "/events",
        headers={"X-API-Key": "test-key"},
        json={
            "source_agent": "support-bot",
            "event_type": "prompt_injection",
            "description": "A user attempted a prompt injection to bypass system instructions.",
        },
    )
    event = resp.json()
    incident = [i for i in client.get("/incidents").json() if i["event_id"] == event["id"]][0]
    remediation_id = incident["remediation"]["id"]

    unauthorized = client.post(f"/remediation/{remediation_id}/approve", json={"approved_by": "x"})
    assert unauthorized.status_code == 401

    approve = client.post(
        f"/remediation/{remediation_id}/approve",
        headers={"X-API-Key": "test-key"},
        json={"approved_by": "security-lead@example.com", "reason": "confirmed threat, revoking creds"},
    )
    assert approve.status_code == 200
    body = approve.json()
    assert body["status"] == "executed"
    assert body["approved_by"] == "security-lead@example.com"

    # approving twice should now conflict
    again = client.post(
        f"/remediation/{remediation_id}/approve",
        headers={"X-API-Key": "test-key"},
        json={"approved_by": "security-lead@example.com"},
    )
    assert again.status_code == 409


def test_analytics_summary(client):
    resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_events" in body
    assert "by_risk_level" in body

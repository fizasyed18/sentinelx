from app.agents.graph import run_pipeline
from app.rag.store import RAGStore
from tests.fakes import fake_call_llm_json

# Note: the autouse `fake_llm` fixture in conftest.py already patches
# app.agents.graph.call_llm_json for every test in this module.


def test_fake_llm_flags_critical_keywords():
    result = fake_call_llm_json(
        "classify... Return a JSON object with keys: is_suspicious (bool)... "
        "event description: agent attempted to exfiltrate data to an external host"
    )
    assert result["is_suspicious"] is True


def test_pipeline_low_severity_not_suspicious():
    state = run_pipeline(
        source_agent="scheduler-agent",
        event_type="healthcheck",
        description="Routine scheduled healthcheck ping completed successfully with no anomalies.",
        ip_address=None,
    )
    assert state.get("is_suspicious") is False
    assert "risk_score" not in state


def test_pipeline_high_severity_produces_full_chain():
    state = run_pipeline(
        source_agent="pricing-agent",
        event_type="network_egress",
        description="Agent attempted unauthorized data exfiltration to an external domain.",
        ip_address="185.220.101.4",
    )
    assert state["is_suspicious"] is True
    assert state["risk_score"] > 0
    assert state["action_type"] in {
        "log_and_monitor", "throttle_and_alert", "revoke_credentials",
        "quarantine_agent_and_revoke_credentials", "dismiss_false_positive",
    }
    assert isinstance(state["retrieved_context"], list)


def test_rag_store_retrieves_relevant_policy():
    store = RAGStore()
    results = store.retrieve("agent exfiltrated data to an external unauthorized domain", k=2)
    assert any("exfiltrat" in r.lower() for r in results)


def test_rag_store_learns_new_precedents():
    store = RAGStore()
    before = len(store.documents)
    store.add_document("Precedent: a brand new incident summary about a novel attack pattern.")
    assert len(store.documents) == before + 1

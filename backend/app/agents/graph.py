"""SentinelX multi-agent pipeline, built with LangGraph.

Pipeline shape:

    monitor -> (not suspicious) -> END (auto-closed, no incident)
            -> (suspicious) -> investigate -> risk_score -> remediate -> END

Each node is a small, single-responsibility agent that reads/writes a shared
typed state dict. This mirrors a real governance workflow: triage, then
investigate with retrieved context + tool enrichment, then score, then
recommend remediation (flagging when a human must approve before anything
destructive executes).
"""
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from app.agents.llm import call_llm_json
from app.agents.prompts import (
    monitor_prompt,
    investigate_prompt,
    risk_score_prompt,
    remediation_prompt,
)
from app.agents.tools import lookup_ip_reputation, send_slack_alert
from app.rag.store import rag_store
from app.logging_conf import get_logger

log = get_logger("agent_graph")


class SentinelState(TypedDict, total=False):
    source_agent: str
    event_type: str
    description: str
    ip_address: str | None

    is_suspicious: bool
    severity_hint: str
    monitor_reason: str

    ip_context: dict
    retrieved_context: list[str]
    investigation_notes: str
    key_findings: list[str]

    risk_score: int
    risk_level: str
    risk_justification: str

    action_type: str
    action_justification: str
    requires_human_approval: bool

    summary: str


def monitor_node(state: SentinelState) -> SentinelState:
    prompt = monitor_prompt(state["description"], state["event_type"], state["source_agent"])
    result = call_llm_json(prompt)
    log.info("monitor_node", suspicious=result.get("is_suspicious"))
    return {
        "is_suspicious": bool(result.get("is_suspicious", False)),
        "severity_hint": result.get("severity_hint", "low"),
        "monitor_reason": result.get("reason", ""),
    }


def investigate_node(state: SentinelState) -> SentinelState:
    ip_context = lookup_ip_reputation(state.get("ip_address"))
    retrieved = rag_store.retrieve(state["description"], k=3)
    prompt = investigate_prompt(state["description"], ip_context, retrieved)
    result = call_llm_json(prompt)
    log.info("investigate_node", findings=len(result.get("key_findings", [])))
    return {
        "ip_context": ip_context,
        "retrieved_context": retrieved,
        "investigation_notes": result.get("notes", ""),
        "key_findings": result.get("key_findings", []),
    }


def risk_score_node(state: SentinelState) -> SentinelState:
    prompt = risk_score_prompt(
        state["description"], state.get("investigation_notes", ""), state.get("key_findings", [])
    )
    result = call_llm_json(prompt)
    log.info("risk_score_node", score=result.get("risk_score"))
    return {
        "risk_score": int(result.get("risk_score", 0)),
        "risk_level": result.get("risk_level", "low"),
        "risk_justification": result.get("justification", ""),
    }


def remediation_node(state: SentinelState) -> SentinelState:
    prompt = remediation_prompt(state["description"], state.get("risk_score", 0), state.get("risk_level", "low"))
    result = call_llm_json(prompt)
    requires_approval = bool(result.get("requires_human_approval", False))
    summary = (
        f"[{state.get('risk_level','low').upper()}] {state['event_type']} from "
        f"{state['source_agent']}: {state['description'][:140]}"
    )
    if requires_approval:
        send_slack_alert(
            f":rotating_light: SentinelX incident ({state.get('risk_level')}, "
            f"score {state.get('risk_score')}): {summary}\nRecommended action: "
            f"{result.get('action_type')} -- awaiting human approval."
        )
    log.info("remediation_node", action=result.get("action_type"), requires_approval=requires_approval)
    return {
        "action_type": result.get("action_type", "log_and_monitor"),
        "action_justification": result.get("justification", ""),
        "requires_human_approval": requires_approval,
        "summary": summary,
    }


def route_after_monitor(state: SentinelState) -> str:
    return "investigate" if state.get("is_suspicious") else END


def build_graph():
    graph = StateGraph(SentinelState)
    graph.add_node("monitor", monitor_node)
    graph.add_node("investigate", investigate_node)
    graph.add_node("score_risk", risk_score_node)
    graph.add_node("remediate", remediation_node)

    graph.set_entry_point("monitor")
    graph.add_conditional_edges("monitor", route_after_monitor, {"investigate": "investigate", END: END})
    graph.add_edge("investigate", "score_risk")
    graph.add_edge("score_risk", "remediate")
    graph.add_edge("remediate", END)
    return graph.compile()


sentinel_graph = build_graph()


def run_pipeline(source_agent: str, event_type: str, description: str, ip_address: str | None) -> dict[str, Any]:
    """Execute the full graph for one event and return the final state."""
    initial: SentinelState = {
        "source_agent": source_agent,
        "event_type": event_type,
        "description": description,
        "ip_address": ip_address,
    }
    final_state = sentinel_graph.invoke(initial)
    return dict(final_state)

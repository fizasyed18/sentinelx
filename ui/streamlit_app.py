"""SentinelX Streamlit dashboard.

Lets a security operator: submit/simulate agent activity events, watch the
multi-agent pipeline triage them into incidents in real time, review
investigation notes and retrieved policy context, and approve/reject
recommended remediations with a human-in-the-loop click.
"""
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_KEY = os.getenv("SENTINELX_API_KEY", "dev-local-key")

st.set_page_config(page_title="SentinelX", page_icon="🛡️", layout="wide")

RISK_COLORS = {"low": "#2ecc71", "medium": "#f1c40f", "high": "#e67e22", "critical": "#e74c3c"}


def api_get(path: str, **kwargs):
    try:
        resp = requests.get(f"{BACKEND_URL}{path}", timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None


def api_post(path: str, json: dict, auth: bool = False):
    headers = {"X-API-Key": API_KEY} if auth else {}
    try:
        resp = requests.post(f"{BACKEND_URL}{path}", json=json, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None


st.title("🛡️ SentinelX")
st.caption("Autonomous AI Security & Governance Platform — multi-agent monitoring, investigation, risk scoring & human-approved remediation.")

tab_dashboard, tab_simulate, tab_analytics = st.tabs(["📋 Incidents", "🧪 Simulate Event", "📊 Analytics"])

# ---------------------------------------------------------------- Dashboard
with tab_dashboard:
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    status_filter = st.selectbox(
        "Filter by status", ["all", "open", "investigating", "awaiting_approval", "resolved", "dismissed"]
    )

    params = {} if status_filter == "all" else {"status": status_filter}
    incidents = api_get("/incidents", params=params) or []

    if not incidents:
        st.info("No incidents yet. Try the **Simulate Event** tab to feed the pipeline, or check the backend connection.")
    for inc in incidents:
        level = inc.get("risk_level", "low")
        color = RISK_COLORS.get(level, "#95a5a6")
        with st.container(border=True):
            top = st.columns([5, 1, 1, 1])
            top[0].markdown(f"**{inc['summary'] or '(no summary)'}**")
            top[1].markdown(f"<span style='color:{color};font-weight:bold'>{level.upper()}</span>", unsafe_allow_html=True)
            top[2].markdown(f"Score: **{inc['risk_score']}**")
            top[3].markdown(f"`{inc['status']}`")

            with st.expander("Investigation & remediation details"):
                event = inc.get("event") or {}
                st.markdown(f"**Source agent:** `{event.get('source_agent')}`  |  **Event type:** `{event.get('event_type')}`")
                st.markdown(f"**Event description:** {event.get('description')}")
                st.markdown(f"**Investigation notes:** {inc.get('investigation_notes')}")
                context = inc.get("retrieved_context") or []
                if context:
                    st.markdown("**Retrieved policy / precedent context (RAG):**")
                    for c in context:
                        st.markdown(f"- {c}")

                remediation = inc.get("remediation")
                if remediation:
                    st.markdown(f"**Recommended action:** `{remediation['action_type']}`")
                    st.markdown(f"**Justification:** {remediation['justification']}")
                    st.markdown(f"**Remediation status:** `{remediation['status']}`")

                    if remediation["status"] == "pending" and remediation["requires_human_approval"]:
                        st.warning("⚠️ This action requires human approval before it will be executed.")
                        approver = st.text_input("Your name / email", key=f"approver-{inc['id']}")
                        reason = st.text_input("Decision note (optional)", key=f"reason-{inc['id']}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ Approve & Execute", key=f"approve-{inc['id']}", disabled=not approver):
                            result = api_post(
                                f"/remediation/{remediation['id']}/approve",
                                {"approved_by": approver, "reason": reason},
                                auth=True,
                            )
                            if result:
                                st.success("Approved and executed.")
                                st.rerun()
                        if c2.button("🚫 Reject", key=f"reject-{inc['id']}", disabled=not approver):
                            result = api_post(
                                f"/remediation/{remediation['id']}/reject",
                                {"approved_by": approver, "reason": reason},
                                auth=True,
                            )
                            if result:
                                st.info("Remediation rejected; incident dismissed.")
                                st.rerun()

# ---------------------------------------------------------------- Simulate
with tab_simulate:
    st.subheader("Simulate an AI-agent activity event")
    st.caption("Feed a synthetic event into the live monitor → investigate → risk-score → remediate pipeline.")

    presets = {
        "Custom": {},
        "Unauthorized data access": dict(
            source_agent="checkout-agent", event_type="data_access",
            description="Agent queried the production customers table directly using an admin-scoped key instead of its scoped service token.",
            ip_address="8.8.8.8",
        ),
        "Prompt injection attempt": dict(
            source_agent="support-bot", event_type="prompt_injection",
            description="A user message attempted a prompt injection to make the agent ignore its system instructions and reveal internal tool credentials.",
            ip_address="45.33.32.156",
        ),
        "Data exfiltration": dict(
            source_agent="pricing-agent", event_type="network_egress",
            description="Agent attempted to exfiltrate a bulk pricing export to an external, unauthorized domain outside the approved partner allowlist.",
            ip_address="185.220.101.4",
        ),
        "Routine healthcheck (benign)": dict(
            source_agent="scheduler-agent", event_type="healthcheck",
            description="Routine scheduled healthcheck ping completed successfully with no anomalies.",
            ip_address="10.0.0.5",
        ),
    }
    preset_name = st.selectbox("Preset scenario", list(presets.keys()))
    preset = presets[preset_name]

    with st.form("event_form"):
        source_agent = st.text_input("Source agent", value=preset.get("source_agent", ""))
        event_type = st.selectbox(
            "Event type",
            ["data_access", "api_call", "prompt_injection", "network_egress", "healthcheck", "other"],
            index=["data_access", "api_call", "prompt_injection", "network_egress", "healthcheck", "other"].index(
                preset.get("event_type", "other")
            ) if preset.get("event_type") in ["data_access", "api_call", "prompt_injection", "network_egress", "healthcheck"] else 5,
        )
        description = st.text_area("Description", value=preset.get("description", ""), height=100)
        ip_address = st.text_input("Source IP (optional)", value=preset.get("ip_address", ""))
        submitted = st.form_submit_button("🚀 Send to SentinelX pipeline")

    if submitted:
        payload = {
            "source_agent": source_agent,
            "event_type": event_type,
            "description": description,
            "ip_address": ip_address or None,
        }
        result = api_post("/events", payload, auth=True)
        if result:
            st.success(f"Event ingested (id={result['id']}). Check the Incidents tab to see if it was flagged.")

# ---------------------------------------------------------------- Analytics
with tab_analytics:
    summary = api_get("/analytics/summary")
    if summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total events", summary["total_events"])
        c2.metric("Total incidents", summary["total_incidents"])
        c3.metric("Awaiting approval", summary["awaiting_approval"])
        c4.metric("Avg risk score", summary["avg_risk_score"])

        col1, col2 = st.columns(2)
        with col1:
            if summary["by_risk_level"]:
                df = pd.DataFrame(list(summary["by_risk_level"].items()), columns=["risk_level", "count"])
                fig = px.pie(df, names="risk_level", values="count", title="Incidents by risk level",
                             color="risk_level", color_discrete_map=RISK_COLORS)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            if summary["by_event_type"]:
                df2 = pd.DataFrame(list(summary["by_event_type"].items()), columns=["event_type", "count"])
                fig2 = px.bar(df2, x="event_type", y="count", title="Events by type")
                st.plotly_chart(fig2, use_container_width=True)

st.sidebar.header("⚙️ Connection")
st.sidebar.text(f"Backend: {BACKEND_URL}")
health = api_get("/health")
st.sidebar.success("Backend reachable ✅") if health else st.sidebar.error("Backend unreachable ❌")

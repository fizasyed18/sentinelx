"""SentinelX Streamlit dashboard."""

import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "http://localhost:8000",
)

API_KEY = os.getenv(
    "SENTINELX_API_KEY",
    "dev-local-key",
)

st.set_page_config(
    page_title="SentinelX",
    page_icon="🛡️",
    layout="wide",
)


RISK_COLORS = {
    "low": "#2ecc71",
    "medium": "#f1c40f",
    "high": "#e67e22",
    "critical": "#e74c3c",
}


# ============================================================
# API FUNCTIONS
# ============================================================

def api_get(path: str, **kwargs):
    """Send GET request to FastAPI backend."""

    try:
        response = requests.get(
            f"{BACKEND_URL}{path}",
            timeout=10,
            **kwargs,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None

    except ValueError as exc:
        st.error(f"Invalid JSON response: {exc}")
        return None


def api_post(path: str, json: dict, auth: bool = False):
    """Send POST request to FastAPI backend."""

    headers = {}

    if auth:
        headers["X-API-Key"] = API_KEY

    try:
        response = requests.post(
            f"{BACKEND_URL}{path}",
            json=json,
            headers=headers,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as exc:
        st.error(f"Backend request failed: {exc}")
        return None

    except ValueError as exc:
        st.error(f"Invalid JSON response: {exc}")
        return None


# ============================================================
# HEADER
# ============================================================

st.title("🛡️ SentinelX")

st.caption(
    "Autonomous AI Security & Governance Platform — "
    "multi-agent monitoring, investigation, risk scoring "
    "& human-approved remediation."
)


# ============================================================
# TABS
# ============================================================

tab_dashboard, tab_simulate, tab_analytics = st.tabs(
    [
        "📋 Incidents",
        "🧪 Simulate Event",
        "📊 Analytics",
    ]
)


# ============================================================
# INCIDENT DASHBOARD
# ============================================================

with tab_dashboard:

    col1, col2 = st.columns([1, 5])

    with col1:

        if st.button("🔄 Refresh"):

            st.rerun()

    status_filter = st.selectbox(
        "Filter by status",
        [
            "all",
            "open",
            "investigating",
            "awaiting_approval",
            "resolved",
            "dismissed",
        ],
    )

    params = {}

    if status_filter != "all":
        params["status"] = status_filter

    incidents_response = api_get(
        "/incidents",
        params=params,
    )

    if incidents_response is None:

        st.warning(
            "Unable to retrieve incidents from the backend. "
            "Make sure your FastAPI backend is running."
        )

    else:

        incidents = incidents_response

        if not incidents:

            st.info(
                "No incidents yet. Try the "
                "**Simulate Event** tab to feed the pipeline."
            )

        for inc in incidents:

            level = inc.get(
                "risk_level",
                "low",
            )

            color = RISK_COLORS.get(
                level,
                "#95a5a6",
            )

            with st.container(border=True):

                top = st.columns(
                    [
                        5,
                        1,
                        1,
                        1,
                    ]
                )

                top[0].markdown(
                    f"**{inc.get('summary') or '(no summary)'}**"
                )

                top[1].markdown(
                    f"""
                    <span style="
                        color:{color};
                        font-weight:bold;
                    ">
                        {level.upper()}
                    </span>
                    """,
                    unsafe_allow_html=True,
                )

                top[2].markdown(
                    f"Score: **{inc.get('risk_score', 'N/A')}**"
                )

                top[3].markdown(
                    f"`{inc.get('status', 'unknown')}`"
                )

                with st.expander(
                    "Investigation & remediation details"
                ):

                    event = inc.get("event") or {}

                    st.markdown(
                        f"""
                        **Source agent:** `{event.get('source_agent', 'N/A')}`  
                        **Event type:** `{event.get('event_type', 'N/A')}`
                        """
                    )

                    st.markdown(
                        f"""
                        **Event description:**  
                        {event.get('description', 'N/A')}
                        """
                    )

                    st.markdown(
                        f"""
                        **Investigation notes:**  
                        {inc.get('investigation_notes', 'N/A')}
                        """
                    )

                    context = inc.get(
                        "retrieved_context"
                    ) or []

                    if context:

                        st.markdown(
                            "**Retrieved policy / precedent context (RAG):**"
                        )

                        for item in context:

                            st.markdown(
                                f"- {item}"
                            )

                    remediation = inc.get(
                        "remediation"
                    )

                    if remediation:

                        st.markdown(
                            f"""
                            **Recommended action:**  
                            `{remediation.get('action_type', 'N/A')}`
                            """
                        )

                        st.markdown(
                            f"""
                            **Justification:**  
                            {remediation.get('justification', 'N/A')}
                            """
                        )

                        remediation_status = remediation.get(
                            "status",
                            "unknown",
                        )

                        st.markdown(
                            f"""
                            **Remediation status:**  
                            `{remediation_status}`
                            """
                        )

                        if (
                            remediation_status == "pending"
                            and remediation.get(
                                "requires_human_approval",
                                False,
                            )
                        ):

                            st.warning(
                                "⚠️ This action requires human approval "
                                "before it will be executed."
                            )

                            approver = st.text_input(
                                "Your name / email",
                                key=f"approver-{inc['id']}",
                            )

                            reason = st.text_input(
                                "Decision note (optional)",
                                key=f"reason-{inc['id']}",
                            )

                            c1, c2 = st.columns(2)

                            with c1:

                                if st.button(
                                    "✅ Approve & Execute",
                                    key=f"approve-{inc['id']}",
                                    disabled=not approver,
                                ):

                                    result = api_post(
                                        f"/remediation/{remediation['id']}/approve",
                                        {
                                            "approved_by": approver,
                                            "reason": reason,
                                        },
                                        auth=True,
                                    )

                                    if result:

                                        st.success(
                                            "Approved and executed."
                                        )

                                        st.rerun()

                            with c2:

                                if st.button(
                                    "🚫 Reject",
                                    key=f"reject-{inc['id']}",
                                    disabled=not approver,
                                ):

                                    result = api_post(
                                        f"/remediation/{remediation['id']}/reject",
                                        {
                                            "approved_by": approver,
                                            "reason": reason,
                                        },
                                        auth=True,
                                    )

                                    if result:

                                        st.info(
                                            "Remediation rejected; "
                                            "incident dismissed."
                                        )

                                        st.rerun()


# ============================================================
# SIMULATE EVENT
# ============================================================

with tab_simulate:

    st.subheader(
        "Simulate an AI-agent activity event"
    )

    st.caption(
        "Feed a synthetic event into the live "
        "monitor → investigate → risk-score → "
        "remediate pipeline."
    )

    presets = {

        "Custom": {},

        "Unauthorized data access": {
            "source_agent": "checkout-agent",
            "event_type": "data_access",
            "description": (
                "Agent queried the production customers table "
                "directly using an admin-scoped key instead of "
                "its scoped service token."
            ),
            "ip_address": "8.8.8.8",
        },

        "Prompt injection attempt": {
            "source_agent": "support-bot",
            "event_type": "prompt_injection",
            "description": (
                "A user message attempted a prompt injection "
                "to make the agent ignore its system instructions "
                "and reveal internal tool credentials."
            ),
            "ip_address": "45.33.32.156",
        },

        "Data exfiltration": {
            "source_agent": "pricing-agent",
            "event_type": "network_egress",
            "description": (
                "Agent attempted to exfiltrate a bulk pricing "
                "export to an external, unauthorized domain "
                "outside the approved partner allowlist."
            ),
            "ip_address": "185.220.101.4",
        },

        "Routine healthcheck (benign)": {
            "source_agent": "scheduler-agent",
            "event_type": "healthcheck",
            "description": (
                "Routine scheduled healthcheck ping completed "
                "successfully with no anomalies."
            ),
            "ip_address": "10.0.0.5",
        },
    }

    preset_name = st.selectbox(
        "Preset scenario",
        list(presets.keys()),
    )

    preset = presets[preset_name]

    with st.form("event_form"):

        source_agent = st.text_input(
            "Source agent",
            value=preset.get(
                "source_agent",
                "",
            ),
        )

        event_types = [
            "data_access",
            "api_call",
            "prompt_injection",
            "network_egress",
            "healthcheck",
            "other",
        ]

        preset_event_type = preset.get(
            "event_type",
            "other",
        )

        if preset_event_type in event_types:

            event_index = event_types.index(
                preset_event_type
            )

        else:

            event_index = event_types.index(
                "other"
            )

        event_type = st.selectbox(
            "Event type",
            event_types,
            index=event_index,
        )

        description = st.text_area(
            "Description",
            value=preset.get(
                "description",
                "",
            ),
            height=100,
        )

        ip_address = st.text_input(
            "Source IP (optional)",
            value=preset.get(
                "ip_address",
                "",
            ),
        )

        submitted = st.form_submit_button(
            "🚀 Send to SentinelX pipeline"
        )

    if submitted:

        if not source_agent.strip():

            st.warning(
                "Please enter a source agent."
            )

        elif not description.strip():

            st.warning(
                "Please enter an event description."
            )

        else:

            payload = {
                "source_agent": source_agent,
                "event_type": event_type,
                "description": description,
                "ip_address": ip_address or None,
            }

            result = api_post(
                "/events",
                payload,
                auth=True,
            )

            if result:

                st.success(
                    f"Event ingested successfully "
                    f"(id={result.get('id', 'N/A')})."
                )

                st.info(
                    "Go to the Incidents tab and click "
                    "Refresh to view the result."
                )


# ============================================================
# ANALYTICS
# ============================================================

with tab_analytics:

    st.subheader(
        "📊 SentinelX Analytics"
    )

    summary = api_get(
        "/analytics/summary"
    )

    if summary:

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Total events",
            summary.get(
                "total_events",
                0,
            ),
        )

        c2.metric(
            "Total incidents",
            summary.get(
                "total_incidents",
                0,
            ),
        )

        c3.metric(
            "Awaiting approval",
            summary.get(
                "awaiting_approval",
                0,
            ),
        )

        c4.metric(
            "Avg risk score",
            summary.get(
                "avg_risk_score",
                0,
            ),
        )

        col1, col2 = st.columns(2)

        with col1:

            by_risk_level = summary.get(
                "by_risk_level",
                {},
            )

            if by_risk_level:

                df = pd.DataFrame(
                    list(
                        by_risk_level.items()
                    ),
                    columns=[
                        "risk_level",
                        "count",
                    ],
                )

                fig = px.pie(
                    df,
                    names="risk_level",
                    values="count",
                    title="Incidents by Risk Level",
                    color="risk_level",
                    color_discrete_map=RISK_COLORS,
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No risk-level data available yet."
                )

        with col2:

            by_event_type = summary.get(
                "by_event_type",
                {},
            )

            if by_event_type:

                df2 = pd.DataFrame(
                    list(
                        by_event_type.items()
                    ),
                    columns=[
                        "event_type",
                        "count",
                    ],
                )

                fig2 = px.bar(
                    df2,
                    x="event_type",
                    y="count",
                    title="Events by Type",
                )

                st.plotly_chart(
                    fig2,
                    use_container_width=True,
                )

            else:

                st.info(
                    "No event-type data available yet."
                )


# ============================================================
# SIDEBAR CONNECTION
# ============================================================

st.sidebar.header("Connection")

st.sidebar.write(
    f"Backend: {BACKEND_URL}"
)

try:

    health_response = requests.get(
        f"{BACKEND_URL}/health",
        timeout=5,
    )

    if health_response.status_code == 200:

        st.sidebar.success(
            "Backend reachable"
        )

    else:

        st.sidebar.error(
            f"Backend returned HTTP "
            f"{health_response.status_code}"
        )

except requests.RequestException:

    st.sidebar.error(
        "Backend unreachable"
    )

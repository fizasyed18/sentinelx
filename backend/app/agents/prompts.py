"""Prompt templates for each agent node. Kept as plain f-string builders
(rather than opaque chains) so the exact prompt sent to the LLM is easy to
inspect, log, and trace in LangSmith."""


def monitor_prompt(event_description: str, event_type: str, source_agent: str) -> str:
    return f"""You are the Monitor Agent in an AI security governance platform.
Classify whether the following AI-agent activity event is potentially a
security or policy violation that warrants investigation.

Source agent: {source_agent}
Event type: {event_type}
Event description: {event_description}

Return a JSON object with keys: is_suspicious (bool), severity_hint
(one of "low","medium","high","critical"), reason (short string).
Respond with ONLY the JSON object."""


def investigate_prompt(event_description: str, ip_context: dict, retrieved_context: list[str]) -> str:
    context_block = "\n".join(f"- {c}" for c in retrieved_context) or "(no closely related policy/precedent found)"
    return f"""You are the Investigator Agent. Gather and synthesize context
for this flagged event before risk scoring.

Event description: {event_description}
Network/IP enrichment: {ip_context}

Relevant governance policies / historical precedents retrieved via RAG:
{context_block}

Return a JSON object with keys: notes, key_findings (notes, key_findings as a
short string and a list of short strings respectively). Respond with ONLY the
JSON object."""


def risk_score_prompt(event_description: str, investigation_notes: str, key_findings: list[str]) -> str:
    findings_block = "\n".join(f"- {f}" for f in key_findings)
    return f"""You are the Risk Scoring Agent. Assign a numeric risk score.

Event description: {event_description}
Investigation notes: {investigation_notes}
Key findings:
{findings_block}

Return a JSON object with keys: risk_score (int 0-100, return a JSON object
with keys: risk_score, risk_level, justification), risk_level (one of
"low","medium","high","critical"), justification (short string). Respond
with ONLY the JSON object."""


def remediation_prompt(event_description: str, risk_score: int, risk_level: str) -> str:
    return f"""You are the Remediation Agent. Recommend one concrete action.

Event description: {event_description}
Risk score: {risk_score}
Risk level: {risk_level}

Allowed actions: log_and_monitor, throttle_and_alert, revoke_credentials,
quarantine_agent_and_revoke_credentials, dismiss_false_positive.

Return a JSON object with keys: action_type, justification,
requires_human_approval (bool -- true for any destructive or credential-
revoking action, or when risk_level is high/critical). Respond with ONLY
the JSON object."""

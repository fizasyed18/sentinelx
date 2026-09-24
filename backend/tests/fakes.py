"""Deterministic stand-in for real OpenAI calls, used only in tests so the
pipeline's control flow can be exercised without hitting the network or
requiring a real API key."""

SEVERITY_KEYWORDS = {
    "critical": ["exfiltrat", "ransomware", "credential leak", "delete production", "wipe", "privilege escalation"],
    "high": ["unauthorized", "prompt injection", "injection", "malware", "data breach", "bypass", "leak"],
    "medium": ["excessive", "rate limit", "throttle", "suspicious activity", "anomalous", "repeated failed"],
    "low": ["informational", "routine", "scheduled", "healthcheck", "no anomalies", "completed successfully"],
}


def severity_of(text: str) -> str:
    text = text.lower()
    for level in ("critical", "high", "medium", "low"):
        for kw in SEVERITY_KEYWORDS[level]:
            if kw in text:
                return level
    return "low"


def fake_call_llm_json(prompt: str) -> dict:
    text = prompt.lower()
    severity = severity_of(text)

    if "return a json object with keys: is_suspicious" in text:
        return {
            "is_suspicious": severity in ("critical", "high", "medium"),
            "severity_hint": severity,
            "reason": f"Test heuristic matched severity tier '{severity}'.",
        }
    if "return a json object with keys: notes, key_findings" in text:
        return {
            "notes": "Automated investigation completed.",
            "key_findings": [f"Event language matches a '{severity}' severity pattern."],
        }
    if "return a json object with keys: risk_score" in text:
        score_map = {"critical": 92, "high": 74, "medium": 48, "low": 15}
        return {
            "risk_score": score_map[severity],
            "risk_level": severity,
            "justification": f"Mapped severity tier '{severity}' to a base score.",
        }
    if "return a json object with keys: action_type" in text:
        action_map = {
            "critical": "quarantine_agent_and_revoke_credentials",
            "high": "revoke_credentials",
            "medium": "throttle_and_alert",
            "low": "log_and_monitor",
        }
        action = action_map[severity]
        return {
            "action_type": action,
            "justification": f"Recommended '{action}' based on severity tier '{severity}'.",
            "requires_human_approval": severity in ("critical", "high"),
        }
    return {"note": "unrecognized prompt shape"}

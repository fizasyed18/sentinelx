"""LLM access layer.

Uses a real OpenAI chat model when OPENAI_API_KEY is configured. Otherwise
(or when USE_MOCK_LLM=1) falls back to a deterministic, keyword-driven mock
model so the entire multi-agent pipeline remains fully runnable/demoable
without any external credentials -- important for CI, grading, and local
docker-compose demos.
"""
import json
import re
from dataclasses import dataclass

from app.config import settings


@dataclass
class LLMResult:
    content: str


SEVERITY_KEYWORDS = {
    "critical": ["exfiltrat", "ransomware", "credential leak", "delete production", "wipe", "privilege escalation"],
    "high": ["unauthorized", "prompt injection", "injection", "malware", "data breach", "bypass", "leak"],
    "medium": ["excessive", "rate limit", "throttle", "suspicious activity", "anomalous", "repeated failed"],
    "low": ["informational", "routine", "scheduled", "healthcheck", "no anomalies", "completed successfully"],
}


class MockChatModel:
    """A tiny rule-based stand-in for a chat LLM, used when no API key is set."""

    def invoke(self, prompt: str) -> LLMResult:
        text = prompt.lower()

        if "return a json object with keys: is_suspicious" in text:
            return LLMResult(content=self._monitor(text))
        if "return a json object with keys: notes, key_findings" in text:
            return LLMResult(content=self._investigate(text))
        if "return a json object with keys: risk_score" in text:
            return LLMResult(content=self._risk(text))
        if "return a json object with keys: action_type" in text:
            return LLMResult(content=self._remediate(text))
        return LLMResult(content=json.dumps({"note": "mock-llm: unrecognized prompt shape"}))

    @staticmethod
    def _matched_severity(text: str) -> str:
        for level in ("critical", "high", "medium", "low"):
            for kw in SEVERITY_KEYWORDS[level]:
                if kw in text:
                    return level
        return "low"

    def _monitor(self, text: str) -> str:
        severity = self._matched_severity(text)
        is_suspicious = severity in ("critical", "high", "medium")
        return json.dumps({
            "is_suspicious": is_suspicious,
            "severity_hint": severity,
            "reason": f"Mock heuristic matched severity tier '{severity}' from event description keywords.",
        })

    def _investigate(self, text: str) -> str:
        severity = self._matched_severity(text)
        findings = [
            f"Event language matches a '{severity}' severity policy pattern.",
            "Cross-referenced against retrieved policy/precedent context below.",
        ]
        if "ip" in text and re.search(r"\d+\.\d+\.\d+\.\d+", text):
            findings.append("Source IP present and was enriched via threat-intel/geolocation tool.")
        return json.dumps({
            "notes": "Automated investigation completed using mock reasoning model.",
            "key_findings": findings,
        })

    def _risk(self, text: str) -> str:
        severity = self._matched_severity(text)
        score_map = {"critical": 92, "high": 74, "medium": 48, "low": 15}
        score = score_map[severity]
        return json.dumps({
            "risk_score": score,
            "risk_level": severity,
            "justification": f"Mock scoring model mapped severity tier '{severity}' to a base score of {score}.",
        })

    def _remediate(self, text: str) -> str:
        severity = self._matched_severity(text)
        action_map = {
            "critical": "quarantine_agent_and_revoke_credentials",
            "high": "revoke_credentials",
            "medium": "throttle_and_alert",
            "low": "log_and_monitor",
        }
        action = action_map[severity]
        requires_approval = severity in ("critical", "high")
        return json.dumps({
            "action_type": action,
            "justification": f"Recommended '{action}' based on severity tier '{severity}'.",
            "requires_human_approval": requires_approval,
        })


def get_llm():
    if settings.USE_MOCK_LLM:
        return MockChatModel()
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY)


def call_llm_json(prompt: str) -> dict:
    """Invoke the configured LLM and parse a JSON object from its response."""
    llm = get_llm()
    result = llm.invoke(prompt)
    content = getattr(result, "content", str(result))
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise

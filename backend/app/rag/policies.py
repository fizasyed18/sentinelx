"""Static governance-policy corpus used as retrieval context for the
Investigator agent. In production this would be pulled from a policy
management system; here it is a seed corpus for the RAG store."""

POLICIES: list[str] = [
    "Policy AG-001: Agents must not access production databases or customer PII "
    "without explicit, scoped, short-lived credentials issued for that task.",
    "Policy AG-002: Any attempt by an agent to exfiltrate data to an external, "
    "unauthorized domain or storage bucket is a critical severity violation and "
    "must trigger immediate credential revocation.",
    "Policy AG-003: Agents exceeding 100 API calls per minute to a single "
    "downstream service must be automatically throttled and flagged for review.",
    "Policy AG-004: Suspected prompt injection or jailbreak attempts against an "
    "agent must be logged, the originating session terminated, and a security "
    "analyst notified within 15 minutes.",
    "Policy AG-005: Agents may only invoke tools explicitly listed in their "
    "capability manifest; invocation of an undeclared tool is treated as a "
    "high-severity policy violation.",
    "Policy AG-006: Credential or secret material must never appear in agent "
    "logs, transcripts, or tool outputs; any occurrence requires immediate "
    "redaction and rotation of the affected secret.",
    "Policy AG-007: Destructive actions (delete, drop, wipe) issued by an agent "
    "against production systems always require human approval before execution, "
    "regardless of the agent's confidence score.",
    "Policy AG-008: Repeated failed authentication attempts by an agent identity "
    "(5+ in 10 minutes) should be treated as a possible compromised-credential "
    "event and escalated to medium severity or higher.",
    "Policy AG-009: Agents operating from unexpected geolocations relative to "
    "their normal operating region should have that context factored into risk "
    "scoring, especially in combination with other anomalies.",
    "Policy AG-010: All remediation actions, whether automated or human-approved, "
    "must be captured in the immutable audit log with actor, timestamp, and "
    "justification.",
]

# Illustrative historical incident precedents that improve retrieval quality
# once real incidents accumulate in the running system.
PRECEDENT_SEEDS: list[str] = [
    "Precedent: A support agent queried the orders table directly with an "
    "admin-scoped key instead of its scoped service token; remediation was "
    "immediate credential revocation and re-issuance with narrower scope.",
    "Precedent: A research agent was manipulated via a crafted user message "
    "into ignoring its system instructions (prompt injection); the session "
    "was terminated and the input filtering policy was tightened.",
    "Precedent: A pricing agent made 4x its normal call volume to a partner "
    "API within one minute due to a retry-loop bug; it was throttled "
    "automatically and no human approval was required.",
]

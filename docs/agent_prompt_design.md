# Agent Prompt Design

All prompts live in `backend/app/agents/prompts.py` as plain Python
f-string builders (not hidden inside opaque LangChain chains) so the exact
text sent to the model is easy to read, log, and trace in LangSmith.

Each prompt asks for **only a JSON object** with a fixed key set, so parsing
is deterministic (`app/agents/llm.py::call_llm_json`).

## 1. Monitor Agent

**Goal:** cheap, fast triage — is this event worth investigating at all?

```
You are the Monitor Agent in an AI security governance platform.
Classify whether the following AI-agent activity event is potentially a
security or policy violation that warrants investigation.

Source agent: {source_agent}
Event type: {event_type}
Event description: {event_description}

Return a JSON object with keys: is_suspicious (bool), severity_hint
(one of "low","medium","high","critical"), reason (short string).
```

Design notes:
- Kept intentionally narrow (no tool access, no RAG) — it's the
  highest-volume node and should be cheap. Only suspicious events pay the
  cost of investigation/scoring/remediation.
- `severity_hint` is advisory context for the Investigator/Risk nodes, not
  the final score — final scoring happens later with more context.

## 2. Investigator Agent

**Goal:** gather grounding context before anything is scored.

```
You are the Investigator Agent. Gather and synthesize context for this
flagged event before risk scoring.

Event description: {event_description}
Network/IP enrichment: {ip_context}

Relevant governance policies / historical precedents retrieved via RAG:
{context_block}

Return a JSON object with keys: notes, key_findings.
```

Design notes:
- Two external inputs are injected before the LLM ever runs:
  **tool output** (`lookup_ip_reputation`) and **retrieved documents**
  (`rag_store.retrieve`, top-3 by TF-IDF cosine similarity over the policy
  + precedent corpus). This is the RAG step: the model never has to
  "remember" policy text — it's handed the exact relevant excerpts.
- `key_findings` is a list rather than free text so the Risk Scoring
  prompt can consume it structurally.

## 3. Risk Scoring Agent

**Goal:** convert qualitative findings into a comparable, auditable number.

```
You are the Risk Scoring Agent. Assign a numeric risk score.

Event description: {event_description}
Investigation notes: {investigation_notes}
Key findings:
{findings_block}

Return a JSON object with keys: risk_score (int 0-100), risk_level, justification.
```

Design notes:
- Score + categorical level are both returned so the UI can show a
  human-friendly badge (`risk_level`) while analytics/thresholds use the
  precise `risk_score`.
- `justification` is stored on the `Incident` row and shown in the UI so
  an approver never has to trust a bare number.

## 4. Remediation Agent

**Goal:** recommend one concrete, bounded action and gate anything
destructive behind human approval.

```
You are the Remediation Agent. Recommend one concrete action.

Event description: {event_description}
Risk score: {risk_score}
Risk level: {risk_level}

Allowed actions: log_and_monitor, throttle_and_alert, revoke_credentials,
quarantine_agent_and_revoke_credentials, dismiss_false_positive.

Return a JSON object with keys: action_type, justification, requires_human_approval.
```

Design notes:
- The action space is a **closed enum**, not free text — this is what
  makes the remediation safely executable/auditable rather than an
  arbitrary LLM suggestion.
- `requires_human_approval` is treated as agent-recommended but is also
  cross-checked in code (`RISK_APPROVAL_THRESHOLD`, destructive-action
  list) so a misbehaving or manipulated LLM response can't silently
  bypass the human gate for a critical action.

## Testing without live API calls

Each prompt shape is matched by a distinctive substring (e.g.
`"return a json object with keys: is_suspicious"`), so unit tests can
monkeypatch `call_llm_json` with a deterministic fake that returns the same
JSON contract per node, without needing an OpenAI key or making network
calls. See `backend/tests/test_agents.py`. The production code path always
goes through the real `ChatOpenAI` client in `app/agents/llm.py`.

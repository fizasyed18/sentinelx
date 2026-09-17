# Live URL - http://localhost:8501

# 🛡️ SentinelX — Autonomous AI Security & Governance Platform

SentinelX is a multi-agent platform that monitors AI-agent activity across
an organization's agent fleet, detects security threats and policy
violations, investigates incidents with retrieval-augmented context,
calculates risk, and recommends (or auto-executes) remediation — with a
human-in-the-loop approval gate for anything destructive.

## 1. What it does

```
Agent activity event
        │
        ▼
 ┌─────────────┐   not suspicious   ┌──────────┐
 │   Monitor   │───────────────────▶│   END    │  (auto-closed, no incident)
 │    Agent    │                    └──────────┘
 └──────┬──────┘
        │ suspicious
        ▼
 ┌─────────────┐   RAG: policies + precedents
 │ Investigator│◀──────────────────────────────
 │    Agent    │   Tool: IP / threat-intel enrichment
 └──────┬──────┘
        ▼
 ┌─────────────┐
 │ Risk Scoring│  0–100 score + low/medium/high/critical level
 │    Agent    │
 └──────┬──────┘
        ▼
 ┌─────────────┐   Tool: Slack alert
 │ Remediation │──────────────────────▶  human approves / rejects
 │    Agent    │                         via API or Streamlit UI
 └─────────────┘
```

Every event is triaged by a **Monitor Agent**. Suspicious events are handed
to an **Investigator Agent**, which pulls relevant governance policies and
historical incident precedents from a RAG store and enriches the event with
IP/threat-intel context. A **Risk Scoring Agent** assigns a 0–100 risk score
and severity tier. A **Remediation Agent** recommends a concrete action
(log & monitor → throttle & alert → revoke credentials → quarantine agent),
and any destructive or high/critical-severity action is routed to a human
for approval before it is marked executed — with a live Slack alert sent
the moment approval is required.

## 2. Architecture

- **Backend** — FastAPI (`/backend`), SQLAlchemy models (Postgres in
  production / SQLite for local dev), API-key-secured mutating endpoints,
  structured JSON logging + request tracing middleware.
- **Agents** — [LangGraph](https://github.com/langchain-ai/langgraph)
  `StateGraph` (`app/agents/graph.py`) with 4 nodes (monitor, investigate,
  score_risk, remediate) and a conditional edge that short-circuits benign
  events. Each node prompt lives in `app/agents/prompts.py` for easy
  inspection/tracing.
- **LLM** — Real reasoning via `langchain-openai` (`gpt-4o-mini` by
  default) **or** a deterministic rule-based mock model
  (`app/agents/llm.py`) used automatically when no `OPENAI_API_KEY` is set.
  This means the entire platform — pipeline, tests, demo — runs with **zero
  external API keys**.
- **RAG** — Lightweight TF-IDF retrieval store (`app/rag/store.py`) over a
  seeded corpus of governance policies + historical incident precedents
  (`app/rag/policies.py`). New resolved incidents are added back into the
  store, so retrieval quality improves as the system operates.
- **External tool integrations** (≥2, as required):
  1. **Slack Incoming Webhook** — real-time alerts when an incident needs
     human approval, and confirmation messages on approve/reject.
  2. **IP threat-intel / geolocation lookup** (`ipapi.co`) — enriches the
     Investigator agent's context with network origin data.
  Both fail soft (log + fallback) if unreachable or unconfigured.
- **Observability** — Structured JSON logs for every HTTP request and every
  agent-node execution; optional LangSmith tracing via
  `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY`.
- **UI** — Streamlit dashboard (`/ui`): live incident feed with
  approve/reject controls, an event simulator with preset attack
  scenarios, and an analytics tab (risk-level breakdown, event-type
  volume).
- **Deployment** — Dockerfiles for backend + UI, `docker-compose.yml`
  wiring Postgres + backend + UI together.

See [`docs/architecture.md`](docs/architecture.md) for a deeper diagram and
[`docs/agent_prompt_design.md`](docs/agent_prompt_design.md) for the exact
prompt design and rationale behind each agent.

## 3. Quickstart (Docker Compose — recommended)

```bash
cp .env.example .env
# set OPENAI_API_KEY or USE_MOCK_LLM=0 for real LLM reasoning,
# and SLACK_WEBHOOK_URL for live Slack alerts. Works out of the box with
# neither (mock LLM mode).

docker compose up --build
```

- Backend API + docs: http://localhost:8000/docs
- Streamlit UI: http://localhost:8501
- Postgres: localhost:5432 (user/pass/db: `sentinelx`)

The backend auto-seeds 5 demo events on first startup so the UI has data
immediately.

## 4. Local development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export USE_MOCK_LLM=1 API_KEY=dev-local-key
uvicorn app.main:app --reload

# In a second terminal — UI
cd ui
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export BACKEND_URL=http://localhost:8000 SENTINELX_API_KEY=dev-local-key
streamlit run streamlit_app.py
```

## 5. Running tests

```bash
cd backend
pip install -r requirements.txt
USE_MOCK_LLM=1 pytest -v
```

11 tests cover: health, auth enforcement, full pipeline triage (benign vs.
suspicious), RAG retrieval, the mock-LLM heuristics, and the
approve/reject remediation flow (including double-decision conflict
handling).

## 6. API overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | – | Liveness check |
| POST | `/events` | `X-API-Key` | Ingest an agent activity event; runs the full pipeline synchronously |
| GET | `/events` | – | List ingested events |
| GET | `/incidents` | – | List incidents (optional `?status=`) |
| GET | `/incidents/{id}` | – | Incident detail incl. investigation notes + remediation |
| POST | `/remediation/{id}/approve` | `X-API-Key` | Human-approve & execute a pending remediation |
| POST | `/remediation/{id}/reject` | `X-API-Key` | Human-reject a pending remediation |
| GET | `/analytics/summary` | – | Aggregate counts, avg risk, breakdowns |

Interactive OpenAPI docs at `/docs`.

## 7. Deployment / Docker Hub

```bash
docker build -t <your-dockerhub-username>/sentinelx-backend:latest ./backend
docker build -t <your-dockerhub-username>/sentinelx-ui:latest ./ui
docker push <your-dockerhub-username>/sentinelx-backend:latest
docker push <your-dockerhub-username>/sentinelx-ui:latest
```

For a live URL, deploy `docker-compose.yml` to any container host (Railway,
Render, an EC2/DigitalOcean box with Docker, etc.) and point DNS/ports at
the `ui` (8501) and `backend` (8000) services.

## 8. Project structure

```
sentinelx/
├── backend/
│   ├── app/
│   │   ├── agents/        # LangGraph pipeline, prompts, LLM wrapper, tools
│   │   ├── rag/           # policy corpus + TF-IDF retrieval store
│   │   ├── routers/       # events, incidents, remediation, analytics, health
│   │   ├── main.py, config.py, database.py, models.py, schemas.py, services.py
│   ├── tests/
│   ├── requirements.txt, Dockerfile
├── ui/
│   ├── streamlit_app.py
│   ├── requirements.txt, Dockerfile
├── docs/
│   ├── architecture.md
│   └── agent_prompt_design.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## 9. Notes on the mock-LLM mode

`USE_MOCK_LLM=1` (the default whenever `OPENAI_API_KEY` is unset) makes
every agent node use a deterministic, keyword-driven heuristic instead of a
real LLM call. This is intentional: it keeps the full pipeline — including
CI, grading, and offline demos — reliable and free, while preserving the
exact same interfaces (`LLMResult.content` as JSON) so switching to a real
model is a one-line env-var change (`USE_MOCK_LLM=0` + `OPENAI_API_KEY=...`).

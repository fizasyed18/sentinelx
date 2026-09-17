import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, SessionLocal
from app.logging_conf import configure_logging, get_logger
from app.routers import events, incidents, remediation, analytics, health
from app.seed_data import seed

configure_logging()
log = get_logger("main")

app = FastAPI(
    title="SentinelX",
    description="Autonomous AI Security & Governance Platform -- multi-agent monitoring, "
    "investigation, risk scoring, and human-in-the-loop remediation for AI agent fleets.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    log.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(health.router)
app.include_router(events.router)
app.include_router(incidents.router)
app.include_router(remediation.router)
app.include_router(analytics.router)


@app.on_event("startup")
def on_startup():
    init_db()
    log.info("startup", env=settings.ENV, mock_llm=settings.USE_MOCK_LLM)
    if settings.ENV != "production":
        seed(SessionLocal)
        log.info("demo_data_seeded")

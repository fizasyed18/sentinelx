from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AgentEvent, Incident, RemediationAction, RemediationStatus, IncidentStatus, AuditLog
from app.schemas import EventIn
from app.agents.graph import run_pipeline
from app.rag.store import rag_store
from app.logging_conf import get_logger

log = get_logger("services")


def process_event(db: Session, payload: EventIn) -> AgentEvent:
    """Persist an incoming event and run it through the full agent pipeline.

    Shared by the HTTP ingestion endpoint and the startup demo-data seeder.
    """
    event = AgentEvent(
        source_agent=payload.source_agent,
        event_type=payload.event_type,
        description=payload.description,
        payload=payload.payload,
        ip_address=payload.ip_address,
        user_id=payload.user_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    log.info("event_ingested", event_id=event.id, source_agent=event.source_agent)

    result = run_pipeline(
        source_agent=event.source_agent,
        event_type=event.event_type,
        description=event.description,
        ip_address=event.ip_address,
    )

    if result.get("is_suspicious"):
        incident = Incident(
            event_id=event.id,
            status=IncidentStatus.awaiting_approval if result.get("requires_human_approval") else IncidentStatus.investigating,
            risk_score=result.get("risk_score", 0),
            risk_level=result.get("risk_level", "low"),
            summary=result.get("summary", ""),
            investigation_notes=result.get("investigation_notes", ""),
            retrieved_context=result.get("retrieved_context", []),
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        remediation = RemediationAction(
            incident_id=incident.id,
            action_type=result.get("action_type", "log_and_monitor"),
            justification=result.get("action_justification", ""),
            status=RemediationStatus.pending if result.get("requires_human_approval") else RemediationStatus.executed,
            requires_human_approval=1 if result.get("requires_human_approval") else 0,
            executed_at=None if result.get("requires_human_approval") else datetime.utcnow(),
        )
        db.add(remediation)

        if not result.get("requires_human_approval"):
            incident.status = IncidentStatus.resolved
            rag_store.add_document(
                f"Precedent: {incident.summary} -- auto-remediated with "
                f"'{remediation.action_type}' at risk score {incident.risk_score}."
            )

        db.add(AuditLog(actor="sentinelx-pipeline", action="incident_created", details={"incident_id": incident.id}))
        db.commit()

    return event

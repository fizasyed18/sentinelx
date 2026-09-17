from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import RemediationAction, RemediationStatus, Incident, IncidentStatus, AuditLog
from app.schemas import RemediationOut, RemediationDecision
from app.security import require_api_key
from app.agents.tools import send_slack_alert
from app.rag.store import rag_store

router = APIRouter(prefix="/remediation", tags=["remediation"])


def _get_pending(db: Session, remediation_id: str) -> RemediationAction:
    remediation = db.query(RemediationAction).filter(RemediationAction.id == remediation_id).first()
    if not remediation:
        raise HTTPException(status_code=404, detail="Remediation action not found")
    if remediation.status != RemediationStatus.pending:
        raise HTTPException(status_code=409, detail=f"Remediation already {remediation.status}")
    return remediation


@router.post("/{remediation_id}/approve", response_model=RemediationOut, dependencies=[Depends(require_api_key)])
def approve_remediation(remediation_id: str, decision: RemediationDecision, db: Session = Depends(get_db)):
    remediation = _get_pending(db, remediation_id)
    remediation.status = RemediationStatus.executed
    remediation.approved_by = decision.approved_by
    remediation.decided_at = datetime.utcnow()
    remediation.executed_at = datetime.utcnow()

    incident = db.query(Incident).filter(Incident.id == remediation.incident_id).first()
    if incident:
        incident.status = IncidentStatus.resolved
        rag_store.add_document(
            f"Precedent: {incident.summary} -- human-approved remediation "
            f"'{remediation.action_type}' executed by {decision.approved_by}."
        )

    db.add(AuditLog(
        actor=decision.approved_by,
        action="remediation_approved",
        details={"remediation_id": remediation.id, "reason": decision.reason},
    ))
    db.commit()
    db.refresh(remediation)
    send_slack_alert(f":white_check_mark: Remediation `{remediation.action_type}` approved and executed by {decision.approved_by}.")
    return remediation


@router.post("/{remediation_id}/reject", response_model=RemediationOut, dependencies=[Depends(require_api_key)])
def reject_remediation(remediation_id: str, decision: RemediationDecision, db: Session = Depends(get_db)):
    remediation = _get_pending(db, remediation_id)
    remediation.status = RemediationStatus.rejected
    remediation.approved_by = decision.approved_by
    remediation.decided_at = datetime.utcnow()

    incident = db.query(Incident).filter(Incident.id == remediation.incident_id).first()
    if incident:
        incident.status = IncidentStatus.dismissed

    db.add(AuditLog(
        actor=decision.approved_by,
        action="remediation_rejected",
        details={"remediation_id": remediation.id, "reason": decision.reason},
    ))
    db.commit()
    db.refresh(remediation)
    send_slack_alert(f":no_entry: Remediation `{remediation.action_type}` rejected by {decision.approved_by}.")
    return remediation

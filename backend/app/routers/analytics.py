from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AgentEvent, Incident, IncidentStatus
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db)):
    events = db.query(AgentEvent).all()
    incidents = db.query(Incident).all()

    total_incidents = len(incidents)
    avg_risk = round(sum(i.risk_score for i in incidents) / total_incidents, 1) if total_incidents else 0.0
    open_incidents = sum(1 for i in incidents if i.status == IncidentStatus.open)
    awaiting_approval = sum(1 for i in incidents if i.status == IncidentStatus.awaiting_approval)

    by_risk_level = dict(Counter(i.risk_level for i in incidents))
    by_event_type = dict(Counter(e.event_type for e in events))

    return AnalyticsSummary(
        total_events=len(events),
        total_incidents=total_incidents,
        open_incidents=open_incidents,
        awaiting_approval=awaiting_approval,
        avg_risk_score=avg_risk,
        by_risk_level=by_risk_level,
        by_event_type=by_event_type,
    )

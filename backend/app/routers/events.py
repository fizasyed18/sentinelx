from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EventIn, EventOut
from app.security import require_api_key
from app.services import process_event

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut, dependencies=[Depends(require_api_key)])
def ingest_event(payload: EventIn, db: Session = Depends(get_db)):
    return process_event(db, payload)


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db)):
    from app.models import AgentEvent
    return db.query(AgentEvent).order_by(AgentEvent.created_at.desc()).all()

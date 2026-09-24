import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return str(uuid.uuid4())


class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    awaiting_approval = "awaiting_approval"
    resolved = "resolved"
    dismissed = "dismissed"


class RemediationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executed = "executed"
    not_required = "not_required"


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id = Column(String, primary_key=True, default=gen_id)
    source_agent = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    incident = relationship("Incident", back_populates="event", uselist=False)


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=gen_id)
    event_id = Column(String, ForeignKey("agent_events.id"), nullable=False)
    status = Column(Enum(IncidentStatus), default=IncidentStatus.open)
    risk_score = Column(Integer, default=0)
    risk_level = Column(String, default="low")
    summary = Column(Text, default="")
    investigation_notes = Column(Text, default="")
    retrieved_context = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    event = relationship("AgentEvent", back_populates="incident")
    remediation = relationship("RemediationAction", back_populates="incident", uselist=False)


class RemediationAction(Base):
    __tablename__ = "remediation_actions"

    id = Column(String, primary_key=True, default=gen_id)
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False)
    action_type = Column(String, nullable=False)
    justification = Column(Text, default="")
    status = Column(Enum(RemediationStatus), default=RemediationStatus.pending)
    requires_human_approval = Column(Integer, default=1)  # 0/1 bool for sqlite compat
    approved_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    incident = relationship("Incident", back_populates="remediation")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    source_agent: str = Field(..., examples=["checkout-agent"])
    event_type: str = Field(..., examples=["data_access", "api_call", "prompt_injection", "network_egress"])
    description: str = Field(..., examples=["Agent queried production customer table without scoped credentials"])
    payload: dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_id: Optional[str] = None


class EventOut(EventIn):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class RemediationOut(BaseModel):
    id: str
    action_type: str
    justification: str
    status: str
    requires_human_approval: bool
    approved_by: Optional[str] = None
    created_at: datetime
    decided_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IncidentOut(BaseModel):
    id: str
    event_id: str
    status: str
    risk_score: int
    risk_level: str
    summary: str
    investigation_notes: str
    retrieved_context: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    event: Optional[EventOut] = None
    remediation: Optional[RemediationOut] = None

    class Config:
        from_attributes = True


class RemediationDecision(BaseModel):
    approved_by: str = Field(..., examples=["security-lead@example.com"])
    reason: Optional[str] = None


class AnalyticsSummary(BaseModel):
    total_events: int
    total_incidents: int
    open_incidents: int
    awaiting_approval: int
    avg_risk_score: float
    by_risk_level: dict[str, int]
    by_event_type: dict[str, int]

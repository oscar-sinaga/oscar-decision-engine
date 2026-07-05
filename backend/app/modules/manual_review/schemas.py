"""Manual review API schemas (docs/07 §7, docs/13)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.shared.domain.enums import (
    CasePriority,
    CaseStatus,
    DecisionType,
    DocumentStatus,
)

# Analyst resolutions allowed on a case (docs/13 §5).
ANALYST_DECISIONS = {
    DecisionType.APPROVE,
    DecisionType.REJECT,
    DecisionType.APPROVE_WITH_CONDITION,
    DecisionType.FRAUD_INVESTIGATION,
}


class CaseListItem(BaseModel):
    case_id: str
    application_id: str
    product_type: str
    channel: str
    system_decision: DecisionType
    system_reason_codes: list[str]
    status: CaseStatus
    priority: CasePriority
    assigned_to: str | None
    sla_due_at: datetime | None
    sla_breached: bool
    created_at: datetime


class CommentItem(BaseModel):
    id: str
    author_label: str
    body: str
    created_at: datetime


class DocumentItem(BaseModel):
    id: str
    name: str
    status: DocumentStatus
    requested_at: datetime
    resolved_at: datetime | None


class CaseListResponse(BaseModel):
    items: list[CaseListItem]
    total: int
    page: int
    page_size: int


class CaseDetailResponse(CaseListItem):
    decision_id: str
    trace_id: str | None
    risk_grade: str | None
    score: float | None
    applicant_summary: dict[str, Any]
    loan_summary: dict[str, Any]
    vehicle_summary: dict[str, Any]
    analyst_decision: DecisionType | None
    analyst_decided_by: str | None
    analyst_decided_at: datetime | None
    approved_limit: float | None
    approved_tenor_months: int | None
    override_reason_code: str | None
    override_reason: str | None
    escalated_to: str | None
    notes: str
    comments: list[CommentItem]
    documents: list[DocumentItem]
    closed_at: datetime | None


class AssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Defaults to the caller when omitted (self-assignment).
    assignee_username: str | None = None


class AnalystDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analyst_decision: DecisionType
    approved_limit: float | None = Field(default=None, gt=0)
    approved_tenor_months: int | None = Field(default=None, gt=0)
    override_reason_code: str | None = None
    override_reason: str = ""
    notes: str = ""


class EscalateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)
    escalated_to: str | None = Field(default=None, max_length=100)


class RequestDocumentsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1)
    document_names: list[str] | None = None


class CommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000)


class ResolveDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: DocumentStatus

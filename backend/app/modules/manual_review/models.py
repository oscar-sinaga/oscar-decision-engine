"""Manual review case model (docs/06 §2.10, docs/13)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.domain.enums import CasePriority, CaseStatus, DecisionType


class ManualReviewCase(Base):
    __tablename__ = "manual_review_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    application_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id")
    )
    decision_pk: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"))
    status: Mapped[CaseStatus] = mapped_column(String(30), default=CaseStatus.NEW, index=True)
    priority: Mapped[CasePriority] = mapped_column(
        String(20), default=CasePriority.MEDIUM, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    system_decision: Mapped[DecisionType] = mapped_column(String(40))
    analyst_decision: Mapped[DecisionType | None] = mapped_column(String(40), nullable=True)
    analyst_decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    analyst_decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    approved_tenor_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    override_reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    application = relationship("Application")
    decision_record = relationship("Decision")

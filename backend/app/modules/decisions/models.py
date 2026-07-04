"""Application, decision, and immutable decision-trace models (docs/06 §2.1–2.3)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.domain.enums import (
    ApplicationStatus,
    DecisionType,
    ExecutionMode,
    ProductType,
)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[str] = mapped_column(String(100), index=True)
    product_type: Mapped[ProductType] = mapped_column(String(50), index=True)
    channel: Mapped[str] = mapped_column(String(100), default="UNKNOWN")
    applicant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        String(30), default=ApplicationStatus.RECEIVED, index=True
    )
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (
        # Idempotency applies to production decisions only; simulations never persist here.
        Index(
            "uq_decisions_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_decisions_created_at", "created_at"),
    )

    # Server-generated defaults (created_at) are read back after commit in the
    # async session; eager_defaults avoids a lazy load outside greenlet context.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    application_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id")
    )
    external_application_id: Mapped[str] = mapped_column(String(100), index=True)
    decision: Mapped[DecisionType] = mapped_column(String(40), index=True)
    risk_grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    approved_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    approved_tenor_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pricing_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    reason_codes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_versions.id")
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        String(20), default=ExecutionMode.PRODUCTION
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[Application] = relationship()
    trace: Mapped["DecisionTrace"] = relationship(back_populates="decision_record")


class DecisionTrace(Base):
    """Immutable execution evidence. The application never updates or deletes rows."""

    __tablename__ = "decision_traces"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    decision_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id"), unique=True
    )
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        String(20), default=ExecutionMode.PRODUCTION
    )
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    feature_values: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    step_results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    score_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    final_output: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(150), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision_record: Mapped[Decision] = relationship(back_populates="trace")

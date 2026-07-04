"""Strategy identity, immutable versions, ordered steps (docs/06 §2.6–2.8)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.domain.enums import ConfigStatus, ProductType, StepOnError, StepType


class Strategy(Base):
    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("strategy_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_code: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    product_type: Mapped[ProductType] = mapped_column(String(50), index=True)
    segment: Mapped[str] = mapped_column(String(100), default="DEFAULT")
    owner_team: Mapped[str] = mapped_column(String(100), default="RISK")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["StrategyVersion"]] = relationship(
        back_populates="strategy", order_by="StrategyVersion.version"
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("strategies.id"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[ConfigStatus] = mapped_column(String(30), default=ConfigStatus.DRAFT, index=True)
    version_note: Mapped[str] = mapped_column(Text, default="")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    strategy: Mapped[Strategy] = relationship(back_populates="versions")
    steps: Mapped[list["StrategyStep"]] = relationship(
        back_populates="strategy_version", order_by="StrategyStep.step_order"
    )


class StrategyStep(Base):
    __tablename__ = "strategy_steps"
    __table_args__ = (UniqueConstraint("strategy_version_id", "step_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_versions.id")
    )
    step_order: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[StepType] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(200))
    # Code of the referenced rule set / decision table / scorecard / calculation profile.
    reference_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    on_error: Mapped[StepOnError] = mapped_column(String(30), default=StepOnError.FAIL)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    strategy_version: Mapped[StrategyVersion] = relationship(back_populates="steps")

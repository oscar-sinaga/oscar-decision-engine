"""Simulation session and result models (docs/12 §5)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.domain.enums import SimulationStatus, SimulationType


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    type: Mapped[SimulationType] = mapped_column(String(20), default=SimulationType.SINGLE)
    status: Mapped[SimulationStatus] = mapped_column(String(20))
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_versions.id")
    )
    compare_strategy_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_versions.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    results: Mapped[list["SimulationResult"]] = relationship(back_populates="simulation")


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_pk: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("simulations.id")
    )
    result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    trace_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    difference_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    simulation: Mapped[Simulation] = relationship(back_populates="results")

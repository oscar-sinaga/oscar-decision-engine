"""Scorecard and decision-table identities with immutable versions (docs/06 §3)."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base
from app.shared.domain.enums import ConfigStatus


class Scorecard(Base):
    __tablename__ = "scorecards"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["ScorecardVersion"]] = relationship(
        back_populates="scorecard", order_by="ScorecardVersion.version"
    )


class ScorecardVersion(Base):
    """Immutable score-band configuration.

    ``config_json`` shape::

        {
          "score_field": "model_outputs.credit_score",
          "model_version_field": "model_outputs.model_version",
          "bands": [
            {"min_score": 750, "risk_grade": "A"},
            {"min_score": 650, "risk_grade": "B"},
            ...
          ],
          "missing_score_decision": "MANUAL_REVIEW",
          "missing_score_reason_code": "SCORE_UNAVAILABLE"
        }
    """

    __tablename__ = "scorecard_versions"
    __table_args__ = (UniqueConstraint("scorecard_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scorecard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("scorecards.id"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[ConfigStatus] = mapped_column(String(30), default=ConfigStatus.DRAFT, index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    version_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scorecard: Mapped[Scorecard] = relationship(back_populates="versions")


class DecisionTable(Base):
    __tablename__ = "decision_tables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["DecisionTableVersion"]] = relationship(
        back_populates="decision_table", order_by="DecisionTableVersion.version"
    )


class DecisionTableVersion(Base):
    """Immutable decision matrix.

    ``config_json`` shape::

        {
          "hit_policy": "FIRST_MATCH" | "PRIORITY",
          "rows": [
            {
              "priority": 1,
              "conditions": [{"field": "...", "operator": "...", "value": ...}],
              "output": {
                "decision": "APPROVE",
                "reason_code": null,
                "approved_limit_pct_of": {"field": "vehicle.appraisal_value", "pct": 0.8},
                "approved_tenor_months": 24,
                "pricing_rate": 0.021
              }
            }
          ],
          "no_match_decision": "MANUAL_REVIEW",
          "no_match_reason_code": "NO_MATCHING_DECISION_ROW"
        }
    """

    __tablename__ = "decision_table_versions"
    __table_args__ = (UniqueConstraint("decision_table_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_table_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decision_tables.id")
    )
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[ConfigStatus] = mapped_column(String(30), default=ConfigStatus.DRAFT, index=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    version_note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    decision_table: Mapped[DecisionTable] = relationship(back_populates="versions")

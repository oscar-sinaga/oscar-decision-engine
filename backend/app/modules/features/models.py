"""Feature catalog / data dictionary (docs/06 §3, Phase 2).

The catalog is the governed vocabulary for rule conditions and decision-table
columns. Engine mechanics (how derived features are computed) remain in code
(`app/engine/features.py`); this table governs which feature *names* are valid,
their data type, source, and human documentation.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.domain.enums import FeatureDataType, FeatureSource


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    data_type: Mapped[FeatureDataType] = mapped_column(String(20))
    source: Mapped[FeatureSource] = mapped_column(String(20), index=True)
    category: Mapped[str] = mapped_column(String(50), index=True, default="GENERAL")
    # Optional allowed values for enumerable string features (governance aid).
    allowed_values: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

"""Model registry — catalog of external scoring-model versions (docs/05 Phase 2).

Records the model versions that scorecards consume (via ``model_outputs.model_version``
on the payload). It documents provenance and lifecycle; it does not execute models.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base


class RegisteredModel(Base):
    __tablename__ = "registered_models"
    __table_args__ = (UniqueConstraint("code", "version_label"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), index=True)
    version_label: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str] = mapped_column(String(100), default="INTERNAL")
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

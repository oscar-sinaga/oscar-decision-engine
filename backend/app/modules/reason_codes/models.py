"""Reason code registry (docs/06 §2.9)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.domain.enums import ReasonCodeCategory, ReasonSeverity


class ReasonCode(Base):
    __tablename__ = "reason_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[ReasonCodeCategory] = mapped_column(String(30))
    internal_message: Mapped[str] = mapped_column(Text)
    customer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[ReasonSeverity] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

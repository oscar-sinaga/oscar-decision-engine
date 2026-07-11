"""Rule identity, immutable rule versions, and rule sets (docs/06 §2.4–2.5)."""

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
from app.shared.domain.enums import ConfigStatus
from app.shared.domain.enums import RuleCategory as LegacyRuleCategory


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[LegacyRuleCategory] = mapped_column(String(30))
    owner_team: Mapped[str] = mapped_column(String(100), default="RISK")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    versions: Mapped[list["RuleVersion"]] = relationship(
        back_populates="rule", order_by="RuleVersion.version"
    )


class RuleVersion(Base):
    __tablename__ = "rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.id"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[ConfigStatus] = mapped_column(String(30), default=ConfigStatus.DRAFT, index=True)
    condition_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    action_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rule_kind: Mapped[str] = mapped_column(
        String(20), default="POLICY_OUTCOME", server_default="POLICY_OUTCOME"
    )
    expression_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_note: Mapped[str] = mapped_column(Text, default="")
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    rule: Mapped[Rule] = relationship(back_populates="versions")


class RuleSet(Base):
    """Named group of rules referenced by strategy RULE_SET steps."""

    __tablename__ = "rule_sets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    members: Mapped[list["RuleSetMember"]] = relationship(
        back_populates="rule_set", order_by="RuleSetMember.execution_order"
    )


class RuleSetMember(Base):
    __tablename__ = "rule_set_members"
    __table_args__ = (UniqueConstraint("rule_set_id", "rule_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rule_sets.id"))
    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.id"))
    execution_order: Mapped[int] = mapped_column(Integer, default=0)

    rule_set: Mapped[RuleSet] = relationship(back_populates="members")
    rule: Mapped[Rule] = relationship()


class RuleCategory(Base):
    """Managed category vocabulary referenced by ``rules.category`` by code."""

    __tablename__ = "rule_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    label: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

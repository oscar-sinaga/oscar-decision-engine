"""Business audit log API (docs/07 §8, screen spec §11)."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.shared.database import get_session

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogItem(BaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str
    entity_version: str | None
    action: str
    actor_type: str
    actor_label: str
    reason: str | None
    before_value: dict[str, Any] | None
    after_value: dict[str, Any] | None
    metadata: dict[str, Any]
    correlation_id: str | None
    request_id: str | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


@router.get("", response_model=AuditLogResponse)
async def list_audit_logs(
    session: Annotated[AsyncSession, Depends(get_session)],
    event_type: Annotated[str | None, Query()] = None,
    entity_type: Annotated[str | None, Query()] = None,
    entity_id: Annotated[str | None, Query()] = None,
    actor: Annotated[str | None, Query()] = None,
    correlation_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    user: User = require_permission(Permissions.AUDIT_VIEW),
) -> AuditLogResponse:
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if event_type is not None:
        query = query.where(AuditLog.event_type == event_type)
    if entity_type is not None:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if actor is not None:
        query = query.where(AuditLog.actor_label == actor)
    if correlation_id is not None:
        query = query.where(AuditLog.correlation_id == correlation_id)
    if date_from is not None:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        query = query.where(AuditLog.created_at <= date_to)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (await session.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    items = [
        AuditLogItem(
            id=str(row.id),
            event_type=row.event_type,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            entity_version=row.entity_version,
            action=row.action,
            actor_type=row.actor_type,
            actor_label=row.actor_label,
            reason=row.reason,
            before_value=row.before_value,
            after_value=row.after_value,
            metadata=row.metadata_json,
            correlation_id=row.correlation_id,
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AuditLogResponse(items=items, total=total, page=page, page_size=page_size)

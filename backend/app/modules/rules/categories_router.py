"""Managed rule-category catalog endpoints (Phase 3 P3.2)."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.rules.models import RuleCategory
from app.shared.database import get_session
from app.shared.domain.errors import ConflictError, NotFoundError

router = APIRouter(prefix="/rule-categories", tags=["rule-categories"])
Session = Annotated[AsyncSession, Depends(get_session)]


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
    label: str = Field(min_length=1, max_length=100)
    active: bool = True


class CategoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=100)
    active: bool | None = None


class CategoryResponse(BaseModel):
    id: str
    code: str
    label: str
    active: bool
    created_at: datetime | None


def _response(category: RuleCategory) -> CategoryResponse:
    return CategoryResponse(
        id=str(category.id),
        code=category.code,
        label=category.label,
        active=category.active,
        created_at=category.created_at,
    )


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    session: Session,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> list[CategoryResponse]:
    rows = (await session.scalars(select(RuleCategory).order_by(RuleCategory.code))).all()
    return [_response(row) for row in rows]


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    body: CategoryCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> CategoryResponse:
    duplicate = await session.scalar(select(RuleCategory).where(RuleCategory.code == body.code))
    if duplicate is not None:
        raise ConflictError(f"Rule category '{body.code}' already exists")
    category = RuleCategory(**body.model_dump())
    session.add(category)
    await session.flush()
    record_audit_event(
        session,
        event_type="RULE_CATEGORY_CREATED",
        entity_type="RULE_CATEGORY",
        entity_id=category.code,
        action="CREATE_RULE_CATEGORY",
        actor=user,
        after_value=body.model_dump(),
    )
    await session.commit()
    return _response(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> CategoryResponse:
    category = await session.get(RuleCategory, category_id)
    if category is None:
        raise NotFoundError(f"Rule category '{category_id}' not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _response(category)
    before = {key: getattr(category, key) for key in changes}
    for key, value in changes.items():
        setattr(category, key, value)
    record_audit_event(
        session,
        event_type="RULE_CATEGORY_UPDATED",
        entity_type="RULE_CATEGORY",
        entity_id=category.code,
        action="UPDATE_RULE_CATEGORY",
        actor=user,
        before_value=before,
        after_value=changes,
    )
    await session.commit()
    return _response(category)

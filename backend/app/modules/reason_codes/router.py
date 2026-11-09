"""Reason code management routes (docs/02 §6.7)."""

import uuid
from typing import Annotated, ClassVar

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.reason_codes.models import ReasonCode
from app.shared.database import get_session
from app.shared.database.constraints import flush_unique
from app.shared.domain.enums import ReasonCodeCategory, ReasonSeverity
from app.shared.domain.errors import ConflictError, NotFoundError
from app.shared.domain.request_models import PatchRequest, StorageRequest

router = APIRouter(prefix="/reason-codes", tags=["reason-codes"])

Session = Annotated[AsyncSession, Depends(get_session)]


class ReasonCodeCreateRequest(StorageRequest):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    category: ReasonCodeCategory
    severity: ReasonSeverity
    internal_message: str = Field(min_length=1)
    customer_message: str | None = None
    active: bool = True


class ReasonCodeUpdateRequest(PatchRequest):
    nullable_fields: ClassVar[frozenset[str]] = frozenset({"customer_message"})

    model_config = ConfigDict(extra="forbid")

    category: ReasonCodeCategory | None = None
    severity: ReasonSeverity | None = None
    internal_message: str | None = Field(default=None, min_length=1)
    customer_message: str | None = None
    active: bool | None = None


class ReasonCodeResponse(BaseModel):
    id: str
    code: str
    category: ReasonCodeCategory
    severity: ReasonSeverity
    internal_message: str
    customer_message: str | None
    active: bool


def _response(rc: ReasonCode) -> ReasonCodeResponse:
    return ReasonCodeResponse(
        id=str(rc.id),
        code=rc.code,
        category=rc.category,
        severity=rc.severity,
        internal_message=rc.internal_message,
        customer_message=rc.customer_message,
        active=rc.active,
    )


@router.get("", response_model=list[ReasonCodeResponse])
async def list_reason_codes(
    session: Session,
    user: User = require_permission(Permissions.REASON_CODE_VIEW),
) -> list[ReasonCodeResponse]:
    rows = (await session.scalars(select(ReasonCode).order_by(ReasonCode.code))).all()
    return [_response(rc) for rc in rows]


@router.post("", response_model=ReasonCodeResponse, status_code=201)
async def create_reason_code(
    body: ReasonCodeCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.REASON_CODE_MANAGE),
) -> ReasonCodeResponse:
    duplicate = await session.scalar(select(ReasonCode).where(ReasonCode.code == body.code))
    if duplicate is not None:
        raise ConflictError(f"Reason code '{body.code}' already exists")
    rc = ReasonCode(**body.model_dump())
    session.add(rc)
    await flush_unique(session, "Reason code already exists")
    record_audit_event(
        session,
        event_type="REASON_CODE_CREATED",
        entity_type="REASON_CODE",
        entity_id=rc.code,
        action="CREATE_REASON_CODE",
        actor=user,
        after_value=body.model_dump(),
    )
    await session.commit()
    return _response(rc)


@router.patch("/{reason_code_id}", response_model=ReasonCodeResponse)
async def update_reason_code(
    reason_code_id: uuid.UUID,
    body: ReasonCodeUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.REASON_CODE_MANAGE),
) -> ReasonCodeResponse:
    rc = await session.scalar(
        select(ReasonCode)
        .where(ReasonCode.id == reason_code_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if rc is None:
        raise NotFoundError(f"Reason code '{reason_code_id}' not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _response(rc)
    before = {key: getattr(rc, key) for key in changes}
    for key, value in changes.items():
        setattr(rc, key, value)
    record_audit_event(
        session,
        event_type="REASON_CODE_UPDATED",
        entity_type="REASON_CODE",
        entity_id=rc.code,
        action="UPDATE_REASON_CODE",
        actor=user,
        before_value=before,
        after_value=changes,
    )
    await session.commit()
    return _response(rc)

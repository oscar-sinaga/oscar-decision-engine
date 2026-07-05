"""Governance API: approval-request queue and admin RBAC (docs/14, screen spec §12)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import Query as QueryParam
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import CurrentUser, require_permission
from app.modules.auth.models import Role, User
from app.modules.auth.permissions import Permissions
from app.modules.governance.models import ApprovalRequest
from app.shared.database import get_session
from app.shared.domain.enums import ApprovalStatus
from app.shared.domain.errors import AuthorizationError, NotFoundError, ValidationFailedError

router = APIRouter(tags=["governance"])

Session = Annotated[AsyncSession, Depends(get_session)]

_APPROVER_PERMISSIONS = {Permissions.RULE_APPROVE, Permissions.STRATEGY_ACTIVATE}


async def _require_approver(user: CurrentUser) -> User:
    if not (_APPROVER_PERMISSIONS & user.permission_codes):
        raise AuthorizationError("Requires rule.approve or strategy.activate permission")
    return user


class ApprovalRequestItem(BaseModel):
    request_id: str
    entity_type: str
    entity_id: str
    entity_version: str | None
    status: ApprovalStatus
    change_summary: str
    request_reason: str
    simulation_ref: str | None
    decision_reason: str | None
    requested_by: str | None
    decided_by: str | None
    decided_at: datetime | None
    created_at: datetime


@router.get("/approvals", response_model=list[ApprovalRequestItem])
async def list_approval_requests(
    session: Session,
    status: Annotated[ApprovalStatus | None, QueryParam()] = None,
    user: User = Depends(_require_approver),
) -> list[ApprovalRequestItem]:
    query = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc())
    if status is not None:
        query = query.where(ApprovalRequest.status == status)
    requests = (await session.scalars(query)).all()

    async def username(user_id: object) -> str | None:
        if user_id is None:
            return None
        found = await session.get(User, user_id)
        return found.username if found else None

    return [
        ApprovalRequestItem(
            request_id=r.request_id,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            entity_version=r.entity_version,
            status=r.status,
            change_summary=r.change_summary,
            request_reason=r.request_reason,
            simulation_ref=r.simulation_ref,
            decision_reason=r.decision_reason,
            requested_by=await username(r.requested_by),
            decided_by=await username(r.decided_by),
            decided_at=r.decided_at,
            created_at=r.created_at,
        )
        for r in requests
    ]


class AdminUserItem(BaseModel):
    username: str
    full_name: str
    actor_type: str
    is_active: bool
    roles: list[str]


class RoleAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(min_length=0)


class RoleMatrixItem(BaseModel):
    code: str
    name: str
    permissions: list[str]


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.get("/users", response_model=list[AdminUserItem])
async def list_users(
    session: Session,
    user: User = require_permission(Permissions.ADMIN_MANAGE),
) -> list[AdminUserItem]:
    users = (await session.scalars(select(User).order_by(User.username))).all()
    return [
        AdminUserItem(
            username=u.username,
            full_name=u.full_name,
            actor_type=u.actor_type,
            is_active=u.is_active,
            roles=sorted(u.role_codes),
        )
        for u in users
    ]


@admin_router.get("/roles", response_model=list[RoleMatrixItem])
async def role_matrix(
    session: Session,
    user: User = require_permission(Permissions.ADMIN_MANAGE),
) -> list[RoleMatrixItem]:
    roles = (await session.scalars(select(Role).order_by(Role.code))).all()
    return [
        RoleMatrixItem(
            code=role.code,
            name=role.name,
            permissions=sorted(p.code for p in role.permissions),
        )
        for role in roles
    ]


@admin_router.put("/users/{username}/roles", response_model=AdminUserItem)
async def assign_roles(
    username: str,
    body: RoleAssignmentRequest,
    session: Session,
    user: User = require_permission(Permissions.ADMIN_MANAGE),
) -> AdminUserItem:
    target = await session.scalar(select(User).where(User.username == username))
    if target is None:
        raise NotFoundError(f"User '{username}' not found")
    roles = (await session.scalars(select(Role).where(Role.code.in_(body.roles)))).all()
    known = {r.code for r in roles}
    unknown = [code for code in body.roles if code not in known]
    if unknown:
        raise ValidationFailedError(
            "Unknown roles",
            details=[{"field": "roles", "issue": f"unknown: {code}"} for code in unknown],
        )
    before = sorted(target.role_codes)
    target.roles = list(roles)
    record_audit_event(
        session,
        event_type="USER_ROLES_CHANGED",
        entity_type="USER",
        entity_id=target.username,
        action="ASSIGN_ROLES",
        actor=user,
        before_value={"roles": before},
        after_value={"roles": sorted(body.roles)},
    )
    await session.commit()
    return AdminUserItem(
        username=target.username,
        full_name=target.full_name,
        actor_type=target.actor_type,
        is_active=target.is_active,
        roles=sorted(target.role_codes),
    )

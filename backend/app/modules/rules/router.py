"""Rule management API routes (docs/07 §5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.evaluator import evaluate_node
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.rules import service
from app.modules.rules.models import Rule, RuleVersion
from app.modules.rules.schemas import (
    RuleCreateRequest,
    RuleDetailResponse,
    RuleResponse,
    RuleTestRequest,
    RuleTestResponse,
    RuleVersionResponse,
    RuleVersionUpdateRequest,
)
from app.shared.database import get_session
from app.shared.domain.enums import ConfigStatus, RuleCategory

router = APIRouter(prefix="/rules", tags=["rules"])

Session = Annotated[AsyncSession, Depends(get_session)]


class LifecycleRequest(BaseModel):
    reason: str = ""


def _version_response(version: RuleVersion) -> RuleVersionResponse:
    return RuleVersionResponse(
        id=str(version.id),
        version=version.version,
        status=version.status,
        condition=version.condition_json,
        action=version.action_json,
        version_note=version.version_note,
        created_at=version.created_at,
        effective_from=version.effective_from,
        effective_to=version.effective_to,
    )


def _rule_response(rule: Rule) -> RuleResponse:
    active = next((v for v in rule.versions if v.status == ConfigStatus.ACTIVE), None)
    latest = max(rule.versions, key=lambda v: v.version)
    return RuleResponse(
        id=str(rule.id),
        rule_code=rule.rule_code,
        name=rule.name,
        description=rule.description,
        category=rule.category,
        owner_team=rule.owner_team,
        active_version=active.version if active else None,
        latest_version=latest.version,
        latest_status=latest.status,
        created_at=rule.created_at,
    )


def _rule_detail(rule: Rule) -> RuleDetailResponse:
    base = _rule_response(rule)
    return RuleDetailResponse(
        **base.model_dump(),
        versions=[_version_response(v) for v in sorted(rule.versions, key=lambda v: v.version)],
    )


@router.post("", response_model=RuleDetailResponse, status_code=201)
async def create_rule(
    body: RuleCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleDetailResponse:
    rule = await service.create_rule(session, body, user)
    return _rule_detail(rule)


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    session: Session,
    category: Annotated[RuleCategory | None, Query()] = None,
    status: Annotated[ConfigStatus | None, Query()] = None,
    owner_team: Annotated[str | None, Query()] = None,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> list[RuleResponse]:
    query = select(Rule).options(selectinload(Rule.versions)).order_by(Rule.rule_code)
    if category is not None:
        query = query.where(Rule.category == category)
    if owner_team is not None:
        query = query.where(Rule.owner_team == owner_team)
    rules = [rule for rule in (await session.scalars(query)).all() if rule.versions]
    if status is not None:
        rules = [rule for rule in rules if any(v.status == status for v in rule.versions)]
    return [_rule_response(rule) for rule in rules]


@router.get("/{rule_id}", response_model=RuleDetailResponse)
async def get_rule(
    rule_id: uuid.UUID,
    session: Session,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> RuleDetailResponse:
    rule = await service.get_rule(session, rule_id)
    return _rule_detail(rule)


@router.post("/{rule_id}/versions", response_model=RuleVersionResponse, status_code=201)
async def create_rule_version(
    rule_id: uuid.UUID,
    body: RuleVersionUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = await service.create_rule_version(session, rule, body, user)
    return _version_response(version)


@router.put("/{rule_id}/versions/{version_id}", response_model=RuleVersionResponse)
async def update_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    body: RuleVersionUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    return _version_response(await service.update_rule_version(session, rule, version, body, user))


@router.post("/{rule_id}/versions/{version_id}/submit-approval", response_model=RuleVersionResponse)
async def submit_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    return _version_response(await service.submit_rule_version(session, rule, version, user))


@router.post("/{rule_id}/versions/{version_id}/activate", response_model=RuleVersionResponse)
async def activate_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_APPROVE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    return _version_response(
        await service.activate_rule_version(session, rule, version, user, body.reason)
    )


@router.post("/{rule_id}/versions/{version_id}/reject", response_model=RuleVersionResponse)
async def reject_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_APPROVE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    return _version_response(
        await service.reject_rule_version(session, rule, version, user, body.reason)
    )


@router.post("/{rule_id}/versions/{version_id}/retire", response_model=RuleVersionResponse)
async def retire_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_APPROVE),
) -> RuleVersionResponse:
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    return _version_response(
        await service.retire_rule_version(session, rule, version, user, body.reason)
    )


@router.post("/{rule_id}/versions/{version_id}/test", response_model=RuleTestResponse)
async def test_rule_version(
    rule_id: uuid.UUID,
    version_id: uuid.UUID,
    body: RuleTestRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> RuleTestResponse:
    """Dry-run a rule version against a sample feature map. No side effects."""
    rule = await service.get_rule(session, rule_id)
    version = service.get_rule_version(rule, version_id)
    definition = await service.validate_rule_definition(
        session, version.condition_json, version.action_json
    )
    matched, details = evaluate_node(definition.condition, body.features)
    return RuleTestResponse(
        matched=matched,
        evaluated_conditions=details,
        action=version.action_json if matched else {},
    )

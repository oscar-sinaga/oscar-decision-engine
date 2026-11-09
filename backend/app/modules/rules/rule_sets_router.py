"""Rule set management: named groups of rules referenced by strategy steps."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.governance.locking import lock_policy
from app.modules.rules.models import Rule, RuleSet, RuleSetMember
from app.modules.strategies.models import StrategyNode, StrategyVersion
from app.shared.database import get_session
from app.shared.domain.enums import ConfigStatus, NodeType
from app.shared.domain.errors import ConflictError, NotFoundError, ValidationFailedError

router = APIRouter(prefix="/rule-sets", tags=["rule-sets"])

Session = Annotated[AsyncSession, Depends(get_session)]


class RuleSetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    rule_codes: list[str] = Field(min_length=1)


class RuleSetMembersRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_codes: list[str] = Field(min_length=1)


class RuleSetResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    rule_codes: list[str]


def _response(rule_set: RuleSet) -> RuleSetResponse:
    ordered = sorted(rule_set.members, key=lambda m: m.execution_order)
    return RuleSetResponse(
        id=str(rule_set.id),
        code=rule_set.code,
        name=rule_set.name,
        description=rule_set.description,
        rule_codes=[m.rule.rule_code for m in ordered],
    )


async def _resolve_rules(session: AsyncSession, rule_codes: list[str]) -> list[Rule]:
    rules = (await session.scalars(select(Rule).where(Rule.rule_code.in_(rule_codes)))).all()
    by_code = {r.rule_code: r for r in rules}
    missing = [code for code in rule_codes if code not in by_code]
    if missing:
        raise ValidationFailedError(
            "Rule set references unknown rules",
            details=[{"field": "rule_codes", "issue": f"unknown: {code}"} for code in missing],
        )
    if len(set(rule_codes)) != len(rule_codes):
        raise ValidationFailedError(
            "Rule set contains duplicate rules",
            details=[{"field": "rule_codes", "issue": "duplicates not allowed"}],
        )
    return [by_code[code] for code in rule_codes]


async def _get_rule_set(session: AsyncSession, rule_set_id: uuid.UUID) -> RuleSet:
    rule_set = await session.scalar(
        select(RuleSet)
        .where(RuleSet.id == rule_set_id)
        .options(selectinload(RuleSet.members).selectinload(RuleSetMember.rule))
        # Refresh identity-map instances so member replacements are visible.
        .execution_options(populate_existing=True)
    )
    if rule_set is None:
        raise NotFoundError(f"Rule set '{rule_set_id}' not found")
    return rule_set


@router.get("", response_model=list[RuleSetResponse])
async def list_rule_sets(
    session: Session,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> list[RuleSetResponse]:
    rule_sets = (
        await session.scalars(
            select(RuleSet)
            .options(selectinload(RuleSet.members).selectinload(RuleSetMember.rule))
            .order_by(RuleSet.code)
        )
    ).all()
    return [_response(rs) for rs in rule_sets]


@router.post("", response_model=RuleSetResponse, status_code=201)
async def create_rule_set(
    body: RuleSetRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleSetResponse:
    await lock_policy(session)
    duplicate = await session.scalar(select(RuleSet).where(RuleSet.code == body.code))
    if duplicate is not None:
        raise ConflictError(f"Rule set code '{body.code}' already exists")
    rules = await _resolve_rules(session, body.rule_codes)
    rule_set = RuleSet(code=body.code, name=body.name, description=body.description)
    session.add(rule_set)
    await session.flush()
    for order, rule in enumerate(rules, start=1):
        session.add(RuleSetMember(rule_set_id=rule_set.id, rule_id=rule.id, execution_order=order))
    record_audit_event(
        session,
        event_type="RULE_SET_CREATED",
        entity_type="RULE_SET",
        entity_id=body.code,
        action="CREATE_RULE_SET",
        actor=user,
        after_value={"name": body.name, "rule_codes": body.rule_codes},
    )
    await session.commit()
    return _response(await _get_rule_set(session, rule_set.id))


@router.put("/{rule_set_id}/members", response_model=RuleSetResponse)
async def replace_rule_set_members(
    rule_set_id: uuid.UUID,
    body: RuleSetMembersRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> RuleSetResponse:
    await lock_policy(session)
    rule_set = await _get_rule_set(session, rule_set_id)
    published = await session.scalar(
        select(StrategyNode.id)
        .join(StrategyVersion, StrategyNode.strategy_version_id == StrategyVersion.id)
        .where(
            StrategyNode.node_type == NodeType.RULE_SET,
            StrategyNode.reference_code == rule_set.code,
            StrategyVersion.status.in_(
                [ConfigStatus.ACTIVE, ConfigStatus.PENDING_APPROVAL, ConfigStatus.RETIRED]
            ),
        )
        .limit(1)
    )
    if published is not None:
        raise ConflictError(
            "Published rule-set membership is immutable; create a new set and strategy draft"
        )
    rules = await _resolve_rules(session, body.rule_codes)
    before = [m.rule.rule_code for m in sorted(rule_set.members, key=lambda m: m.execution_order)]
    for member in list(rule_set.members):
        await session.delete(member)
    await session.flush()
    for order, rule in enumerate(rules, start=1):
        session.add(RuleSetMember(rule_set_id=rule_set.id, rule_id=rule.id, execution_order=order))
    record_audit_event(
        session,
        event_type="RULE_SET_MEMBERS_UPDATED",
        entity_type="RULE_SET",
        entity_id=rule_set.code,
        action="UPDATE_RULE_SET_MEMBERS",
        actor=user,
        before_value={"rule_codes": before},
        after_value={"rule_codes": body.rule_codes},
    )
    await session.commit()
    return _response(await _get_rule_set(session, rule_set.id))

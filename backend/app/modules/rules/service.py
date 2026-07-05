"""Rule management service: validation, versioning, lifecycle, audit."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.dsl import RuleDefinition, collect_condition_fields, parse_rule_definition
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.features.service import active_feature_paths
from app.modules.governance.service import (
    ensure_maker_checker,
    open_approval_request,
    resolve_approval_request,
)
from app.modules.reason_codes.models import ReasonCode
from app.modules.rules.models import Rule, RuleVersion
from app.modules.rules.schemas import RuleCreateRequest, RuleVersionUpdateRequest
from app.shared.domain.enums import ApprovalStatus, ConfigStatus
from app.shared.domain.errors import ConflictError, NotFoundError, ValidationFailedError
from app.shared.domain.version_lifecycle import (
    activate_version,
    ensure_editable,
    reject_version,
    retire_version,
    submit_for_approval,
)
from app.shared.logging import get_logger

logger = get_logger("oscar.rules")


async def validate_rule_definition(
    session: AsyncSession, condition: dict[str, Any], action: dict[str, Any]
) -> RuleDefinition:
    """Validate DSL shape, feature registry membership, and reason code existence."""
    try:
        definition = parse_rule_definition(condition, action)
    except ValueError as exc:
        raise ValidationFailedError(
            "Rule definition is invalid",
            details=[{"field": "condition/action", "issue": str(exc)}],
        ) from exc

    known = await active_feature_paths(session)
    unknown = sorted(
        field for field in collect_condition_fields(definition.condition) if field not in known
    )
    if unknown:
        raise ValidationFailedError(
            "Rule references unknown or inactive features",
            details=[{"field": field, "issue": "unknown feature"} for field in unknown],
        )

    reason_code = definition.action.reason_code
    if reason_code:
        exists = await session.scalar(
            select(func.count()).select_from(ReasonCode).where(ReasonCode.code == reason_code)
        )
        if not exists:
            raise ValidationFailedError(
                "Rule action references unknown reason code",
                details=[{"field": "action.reason_code", "issue": f"unknown: {reason_code}"}],
            )
    return definition


async def get_rule(session: AsyncSession, rule_id: uuid.UUID) -> Rule:
    rule = await session.scalar(
        select(Rule).where(Rule.id == rule_id).options(selectinload(Rule.versions))
    )
    if rule is None:
        raise NotFoundError(f"Rule '{rule_id}' not found")
    return rule


def get_rule_version(rule: Rule, version_id: uuid.UUID) -> RuleVersion:
    for version in rule.versions:
        if version.id == version_id:
            return version
    raise NotFoundError(f"Rule version '{version_id}' not found for rule '{rule.rule_code}'")


async def create_rule(session: AsyncSession, request: RuleCreateRequest, actor: User) -> Rule:
    await validate_rule_definition(session, request.condition, request.action)
    duplicate = await session.scalar(select(Rule).where(Rule.rule_code == request.rule_code))
    if duplicate is not None:
        raise ConflictError(f"Rule code '{request.rule_code}' already exists")

    rule = Rule(
        rule_code=request.rule_code,
        name=request.name,
        description=request.description,
        category=request.category,
        owner_team=request.owner_team,
        created_by=actor.id,
    )
    session.add(rule)
    await session.flush()
    version = RuleVersion(
        rule_id=rule.id,
        version=1,
        status=ConfigStatus.DRAFT,
        condition_json=request.condition,
        action_json=request.action,
        version_note=request.version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()

    record_audit_event(
        session,
        event_type="RULE_CREATED",
        entity_type="RULE",
        entity_id=rule.rule_code,
        entity_version="1",
        action="CREATE_RULE",
        actor=actor,
        after_value={
            "name": rule.name,
            "category": rule.category,
            "condition": request.condition,
            "action": request.action,
            "status": ConfigStatus.DRAFT,
        },
    )
    await session.commit()
    logger.info("rule.created", extra={"rule_code": rule.rule_code})
    return await get_rule(session, rule.id)


async def create_rule_version(
    session: AsyncSession, rule: Rule, request: RuleVersionUpdateRequest, actor: User
) -> RuleVersion:
    await validate_rule_definition(session, request.condition, request.action)
    open_versions = [
        v for v in rule.versions if v.status in (ConfigStatus.DRAFT, ConfigStatus.PENDING_APPROVAL)
    ]
    if open_versions:
        raise ConflictError(
            f"Rule '{rule.rule_code}' already has an open draft/pending version "
            f"(v{open_versions[0].version})"
        )
    next_version = max((v.version for v in rule.versions), default=0) + 1
    version = RuleVersion(
        rule_id=rule.id,
        version=next_version,
        status=ConfigStatus.DRAFT,
        condition_json=request.condition,
        action_json=request.action,
        version_note=request.version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()
    record_audit_event(
        session,
        event_type="RULE_VERSION_CREATED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(next_version),
        action="CREATE_RULE_VERSION",
        actor=actor,
        after_value={"condition": request.condition, "action": request.action},
    )
    await session.commit()
    return version


async def update_rule_version(
    session: AsyncSession,
    rule: Rule,
    version: RuleVersion,
    request: RuleVersionUpdateRequest,
    actor: User,
) -> RuleVersion:
    ensure_editable(version)
    await validate_rule_definition(session, request.condition, request.action)
    before = {"condition": version.condition_json, "action": version.action_json}
    version.condition_json = request.condition
    version.action_json = request.action
    version.version_note = request.version_note or version.version_note
    record_audit_event(
        session,
        event_type="RULE_VERSION_UPDATED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        action="UPDATE_RULE_VERSION",
        actor=actor,
        before_value=before,
        after_value={"condition": request.condition, "action": request.action},
    )
    await session.commit()
    return version


async def submit_rule_version(
    session: AsyncSession, rule: Rule, version: RuleVersion, actor: User
) -> RuleVersion:
    before = version.status
    submit_for_approval(version)
    approval = open_approval_request(
        session,
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        requested_by=actor,
        change_summary=version.version_note,
    )
    record_audit_event(
        session,
        event_type="RULE_VERSION_SUBMITTED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        action="SUBMIT_FOR_APPROVAL",
        actor=actor,
        before_value={"status": before},
        after_value={"status": version.status},
        metadata={"approval_request_id": approval.request_id},
    )
    await session.commit()
    return version


async def activate_rule_version(
    session: AsyncSession, rule: Rule, version: RuleVersion, actor: User, reason: str | None
) -> RuleVersion:
    ensure_maker_checker(version.created_by, actor)
    previous_active = next((v for v in rule.versions if v.status == ConfigStatus.ACTIVE), None)
    before = version.status
    activate_version(version, previous_active)
    version.approved_by = actor.id
    approval = await resolve_approval_request(
        session,
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        status=ApprovalStatus.APPROVED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="RULE_VERSION_ACTIVATED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        action="ACTIVATE_RULE_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={
            "status": version.status,
            "retired_version": previous_active.version if previous_active else None,
        },
        metadata={"approval_request_id": approval.request_id if approval else None},
    )
    await session.commit()
    logger.info(
        "rule.version_activated",
        extra={"rule_code": rule.rule_code, "version": version.version},
    )
    return version


async def reject_rule_version(
    session: AsyncSession, rule: Rule, version: RuleVersion, actor: User, reason: str
) -> RuleVersion:
    before = version.status
    reject_version(version)
    await resolve_approval_request(
        session,
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        status=ApprovalStatus.REJECTED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="RULE_VERSION_REJECTED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        action="REJECT_RULE_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version


async def retire_rule_version(
    session: AsyncSession, rule: Rule, version: RuleVersion, actor: User, reason: str
) -> RuleVersion:
    before = version.status
    retire_version(version)
    record_audit_event(
        session,
        event_type="RULE_VERSION_RETIRED",
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
        action="RETIRE_RULE_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version

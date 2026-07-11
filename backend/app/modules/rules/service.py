"""Rule management service: validation, versioning, lifecycle, audit."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.dsl import (
    AllGroup,
    AnyGroup,
    BranchedRuleDefinition,
    Condition,
    ConditionNode,
    NotGroup,
    Operator,
    RuleAction,
    collect_condition_fields,
    normalize_rule_definition,
)
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.features.models import Feature
from app.modules.governance.service import (
    ensure_maker_checker,
    open_approval_request,
    resolve_approval_request,
)
from app.modules.reason_codes.models import ReasonCode
from app.modules.rules.models import Rule, RuleCategory, RuleSet, RuleSetMember, RuleVersion
from app.modules.rules.schemas import RuleCreateRequest, RuleVersionUpdateRequest
from app.modules.strategies.models import Strategy, StrategyStep, StrategyVersion
from app.shared.domain.enums import ApprovalStatus, ConfigStatus, FeatureDataType
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
    session: AsyncSession, condition: dict[str, Any], action: dict[str, Any] | None
) -> BranchedRuleDefinition:
    """Validate DSL shape, feature registry membership, and reason code existence."""
    try:
        definition = normalize_rule_definition(condition, action)
    except ValueError as exc:
        raise ValidationFailedError(
            "Rule definition is invalid",
            details=[{"field": "condition/action", "issue": str(exc)}],
        ) from exc

    features = {
        feature.path: feature
        for feature in (
            await session.scalars(select(Feature).where(Feature.active.is_(True)))
        ).all()
    }
    fields = set().union(*(collect_condition_fields(branch.when) for branch in definition.branches))
    unknown = sorted(field for field in fields if field not in features)
    if unknown:
        raise ValidationFailedError(
            "Rule references unknown or inactive features",
            details=[{"field": field, "issue": "unknown feature"} for field in unknown],
        )

    details: list[dict[str, str]] = []
    for branch_index, branch in enumerate(definition.branches):
        _validate_condition_types(branch.when, features, details, f"branches[{branch_index}].when")

    actions = [action for branch in definition.branches for action in branch.then]
    actions.extend(definition.default or [])
    for index, rule_action in enumerate(actions):
        if rule_action.target:
            target = features.get(rule_action.target)
            if target is None:
                details.append(
                    {"field": rule_action.target, "issue": "unknown or inactive SET_OUTPUT target"}
                )
            elif not target.writable:
                details.append(
                    {"field": rule_action.target, "issue": "SET_OUTPUT target is not writable"}
                )
            else:
                issue = _value_type_issue(
                    FeatureDataType(target.data_type), Operator.EQ, rule_action.value
                )
                if issue:
                    details.append({"field": rule_action.target, "issue": issue})
        await _validate_reason_code(session, rule_action, index, details)
    if details:
        raise ValidationFailedError("Rule definition is invalid", details=details)
    return definition


_OPERATORS_BY_TYPE: dict[FeatureDataType, frozenset[Operator]] = {
    FeatureDataType.NUMBER: frozenset(Operator),
    FeatureDataType.STRING: frozenset(
        {Operator.EQ, Operator.NEQ, Operator.IN, Operator.NOT_IN, Operator.EXISTS, Operator.IS_NULL}
    ),
    FeatureDataType.BOOLEAN: frozenset(
        {Operator.EQ, Operator.NEQ, Operator.EXISTS, Operator.IS_NULL}
    ),
    FeatureDataType.DATE: frozenset(
        {
            Operator.EQ,
            Operator.NEQ,
            Operator.GT,
            Operator.GTE,
            Operator.LT,
            Operator.LTE,
            Operator.EXISTS,
            Operator.IS_NULL,
        }
    ),
}


def _conditions(node: ConditionNode) -> list[Condition]:
    if isinstance(node, Condition):
        return [node]
    children: list[ConditionNode]
    if isinstance(node, AllGroup):
        children = node.all
    elif isinstance(node, AnyGroup):
        children = node.any
    elif isinstance(node, NotGroup):
        children = [node.not_]
    else:  # pragma: no cover - closed DSL union
        return []
    return [condition for child in children for condition in _conditions(child)]


def _validate_condition_types(
    node: ConditionNode,
    features: dict[str, Feature],
    details: list[dict[str, str]],
    prefix: str,
) -> None:
    for index, condition in enumerate(_conditions(node)):
        feature = features.get(condition.field)
        if feature is None:
            continue
        data_type = FeatureDataType(feature.data_type)
        field = f"{prefix}.conditions[{index}]"
        if condition.operator not in _OPERATORS_BY_TYPE[data_type]:
            details.append(
                {
                    "field": condition.field,
                    "issue": (
                        f"operator '{condition.operator.value}' not allowed for "
                        f"{data_type.value} feature"
                    ),
                }
            )
            continue
        issue = _value_type_issue(data_type, condition.operator, condition.value)
        if issue:
            details.append({"field": field, "issue": issue})


def _value_type_issue(data_type: FeatureDataType, operator: Operator, value: Any) -> str | None:
    if operator in {Operator.EXISTS, Operator.IS_NULL}:
        return None
    values = value if operator in {Operator.IN, Operator.NOT_IN} else [value]
    if not isinstance(values, list):
        return f"operator '{operator.value}' requires a list value"
    for item in values:
        valid = False
        if data_type is FeatureDataType.NUMBER:
            valid = isinstance(item, (int, float)) and not isinstance(item, bool)
        elif data_type is FeatureDataType.STRING:
            valid = isinstance(item, str)
        elif data_type is FeatureDataType.BOOLEAN:
            valid = isinstance(item, bool)
        elif data_type is FeatureDataType.DATE and isinstance(item, str):
            try:
                date.fromisoformat(item)
                valid = True
            except ValueError:
                valid = False
        if not valid:
            return f"value does not match {data_type.value} feature type"
    return None


async def _validate_reason_code(
    session: AsyncSession,
    action: RuleAction,
    index: int,
    details: list[dict[str, str]],
) -> None:
    if not action.reason_code:
        return
    exists = await session.scalar(
        select(func.count()).select_from(ReasonCode).where(ReasonCode.code == action.reason_code)
    )
    if not exists:
        details.append(
            {
                "field": f"actions[{index}].reason_code",
                "issue": f"unknown: {action.reason_code}",
            }
        )


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


def normalize_stored_definition(version: RuleVersion) -> BranchedRuleDefinition:
    return normalize_rule_definition(version.condition_json, version.action_json)


async def get_rule_usage(session: AsyncSession, rule: Rule) -> dict[str, Any]:
    rule_sets = (
        await session.scalars(
            select(RuleSet)
            .join(RuleSetMember, RuleSetMember.rule_set_id == RuleSet.id)
            .where(RuleSetMember.rule_id == rule.id)
            .order_by(RuleSet.code)
        )
    ).all()
    codes = [rule_set.code for rule_set in rule_sets]
    strategies: dict[uuid.UUID, dict[str, Any]] = {}
    if codes:
        rows = (
            await session.execute(
                select(Strategy, StrategyVersion)
                .join(StrategyVersion, StrategyVersion.strategy_id == Strategy.id)
                .join(StrategyStep, StrategyStep.strategy_version_id == StrategyVersion.id)
                .where(
                    StrategyStep.step_type == "RULE_SET",
                    StrategyStep.reference_code.in_(codes),
                )
                .order_by(Strategy.strategy_code, StrategyVersion.version)
            )
        ).all()
        for strategy, version in rows:
            item = strategies.setdefault(
                strategy.id,
                {
                    "id": str(strategy.id),
                    "strategy_code": strategy.strategy_code,
                    "versions_using": [],
                    "active_version_uses": False,
                },
            )
            if version.version not in item["versions_using"]:
                item["versions_using"].append(version.version)
            if version.status == ConfigStatus.ACTIVE:
                item["active_version_uses"] = True
    return {
        "rule_code": rule.rule_code,
        "rule_sets": [
            {"id": str(rule_set.id), "code": rule_set.code, "name": rule_set.name}
            for rule_set in rule_sets
        ],
        "strategies": list(strategies.values()),
    }


async def create_rule(session: AsyncSession, request: RuleCreateRequest, actor: User) -> Rule:
    condition, action = request.storage_body()
    await validate_rule_definition(session, condition, action)
    category = await session.scalar(
        select(RuleCategory).where(
            RuleCategory.code == request.category, RuleCategory.active.is_(True)
        )
    )
    if category is None:
        raise ValidationFailedError(
            "Rule category is unknown or inactive",
            details=[{"field": "category", "issue": f"unknown or inactive: {request.category}"}],
        )
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
        condition_json=condition,
        action_json=action,
        rule_kind=request.rule_kind,
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
            "condition": condition,
            "action": action,
            "rule_kind": request.rule_kind,
            "status": ConfigStatus.DRAFT,
        },
    )
    await session.commit()
    logger.info("rule.created", extra={"rule_code": rule.rule_code})
    return await get_rule(session, rule.id)


async def create_rule_version(
    session: AsyncSession, rule: Rule, request: RuleVersionUpdateRequest, actor: User
) -> RuleVersion:
    condition, action = request.storage_body()
    await validate_rule_definition(session, condition, action)
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
        condition_json=condition,
        action_json=action,
        rule_kind=request.rule_kind,
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
        after_value={"condition": condition, "action": action, "rule_kind": request.rule_kind},
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
    condition, action = request.storage_body()
    await validate_rule_definition(session, condition, action)
    before = {
        "condition": version.condition_json,
        "action": version.action_json,
        "rule_kind": version.rule_kind,
    }
    version.condition_json = condition
    version.action_json = action
    version.rule_kind = request.rule_kind
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
        after_value={"condition": condition, "action": action, "rule_kind": request.rule_kind},
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

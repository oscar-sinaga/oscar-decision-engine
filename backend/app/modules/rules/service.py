"""Rule management service: validation, versioning, lifecycle, audit."""

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.dsl import (
    ActionType,
    AllGroup,
    AnyGroup,
    BranchedRuleDefinition,
    Condition,
    ConditionNode,
    ExpressionRuleDefinition,
    NotGroup,
    Operator,
    RuleAction,
    collect_condition_fields,
    normalize_rule_definition,
)
from app.engine.expression import (
    ExpressionError,
    ast_from_json,
    ast_to_json,
    render_expression,
    validate_expression,
)
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.features.models import Feature
from app.modules.governance.locking import lock_policy
from app.modules.governance.service import (
    ensure_independent_approver,
    open_approval_request,
    resolve_approval_request,
)
from app.modules.reason_codes.models import ReasonCode
from app.modules.rules.models import Rule, RuleCategory, RuleSet, RuleSetMember, RuleVersion
from app.modules.rules.schemas import RuleCreateRequest, RuleVersionUpdateRequest
from app.modules.strategies.models import Strategy, StrategyNode, StrategyVersion
from app.shared.domain.enums import ApprovalStatus, ConfigStatus, FeatureDataType
from app.shared.domain.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.shared.domain.version_lifecycle import (
    activate_version,
    ensure_editable,
    reject_version,
    retire_version,
    submit_for_approval,
)
from app.shared.logging import get_logger

logger = get_logger("oscar.rules")

type StoredRuleDefinition = BranchedRuleDefinition | ExpressionRuleDefinition


async def active_feature_map(session: AsyncSession) -> dict[str, Feature]:
    return {
        feature.path: feature
        for feature in (
            await session.scalars(select(Feature).where(Feature.active.is_(True)))
        ).all()
    }


def expression_feature_types(features: dict[str, Feature]) -> dict[str, str]:
    return {
        path: (
            "STRING"
            if FeatureDataType(feature.data_type) is FeatureDataType.DATE
            else feature.data_type
        )
        for path, feature in features.items()
    }


def _ensure_expression_permission(actor: User) -> None:
    if Permissions.RULE_AUTHOR_EXPRESSION not in actor.permission_codes:
        raise AuthorizationError(f"Missing permission: {Permissions.RULE_AUTHOR_EXPRESSION}")


def _expression_error_details(field: str, exc: ExpressionError) -> list[dict[str, Any]]:
    return [{"field": field, "issue": exc.message, "line": exc.line, "col": exc.col}]


def _validate_expression_output_type(
    target: Feature, inferred_type: str, details: list[dict[str, Any]]
) -> None:
    target_type = FeatureDataType(target.data_type).value
    expected_type = "STRING" if target_type == FeatureDataType.DATE.value else target_type
    if inferred_type not in {expected_type, "NULL", "UNKNOWN"}:
        details.append(
            {
                "field": target.path,
                "issue": (
                    f"expression produces {inferred_type}, expected {target_type} output type"
                ),
            }
        )


async def validate_rule_definition(
    session: AsyncSession,
    condition: dict[str, Any],
    action: dict[str, Any] | None,
    *,
    actor: User | None = None,
) -> BranchedRuleDefinition:
    """Validate and compile builder DSL, feature references, and actions."""
    features = await active_feature_map(session)
    # Report catalog operator errors before the stricter scalar-shape parser rejects them.
    # This preserves the documented field-specific validation envelope.
    raw_nodes: list[Any] = [condition]
    visited = 0
    while raw_nodes:
        raw = raw_nodes.pop()
        visited += 1
        if visited > 10_000:
            raise ValidationFailedError("Rule condition exceeds the supported complexity")
        if isinstance(raw, list):
            raw_nodes.extend(raw)
        elif isinstance(raw, dict):
            path, operator = raw.get("field"), raw.get("operator")
            feature = features.get(path) if isinstance(path, str) else None
            if feature is not None and isinstance(operator, str):
                parsed_operator: Operator | None
                try:
                    parsed_operator = Operator(operator)
                except ValueError:
                    parsed_operator = None
                data_type = FeatureDataType(feature.data_type)
                if (
                    parsed_operator is not None
                    and parsed_operator not in _OPERATORS_BY_TYPE[data_type]
                ):
                    raise ValidationFailedError(
                        "Rule definition is invalid",
                        details=[
                            {
                                "field": path,
                                "issue": (
                                    f"operator '{operator}' not allowed for {data_type.value} feature"
                                ),
                            }
                        ],
                    )
            raw_nodes.extend(
                raw[key] for key in ("all", "any", "not", "branches", "when") if key in raw
            )
    try:
        definition = normalize_rule_definition(condition, action)
    except ValueError as exc:
        raise ValidationFailedError(
            "Rule definition is invalid",
            details=[{"field": "condition/action", "issue": str(exc)}],
        ) from exc

    feature_types = expression_feature_types(features)
    fields = set().union(*(collect_condition_fields(branch.when) for branch in definition.branches))
    unknown = sorted(field for field in fields if field not in features)
    if unknown:
        raise ValidationFailedError(
            "Rule references unknown or inactive features",
            details=[{"field": field, "issue": "unknown feature"} for field in unknown],
        )

    details: list[dict[str, Any]] = []
    for branch_index, branch in enumerate(definition.branches):
        _validate_condition_types(branch.when, features, details, f"branches[{branch_index}].when")

    actions = [item for branch in definition.branches for item in branch.then]
    actions.extend(definition.default or [])
    for index, rule_action in enumerate(actions):
        if rule_action.type is ActionType.SET_OUTPUT and not rule_action.target:
            details.append(
                {"field": f"actions[{index}].target", "issue": "SET_OUTPUT target is required"}
            )
        target = features.get(rule_action.target) if rule_action.target else None
        if rule_action.target and target is None:
            details.append(
                {"field": rule_action.target, "issue": "unknown or inactive SET_OUTPUT target"}
            )
        elif target is not None and not target.writable:
            details.append(
                {"field": rule_action.target, "issue": "SET_OUTPUT target is not writable"}
            )
        elif target is not None and rule_action.expression is None:
            issue = _value_type_issue(
                FeatureDataType(target.data_type), Operator.EQ, rule_action.value
            )
            if issue:
                details.append({"field": rule_action.target, "issue": issue})

        if rule_action.expression is not None:
            if actor is not None:
                _ensure_expression_permission(actor)
            try:
                validated = validate_expression(
                    rule_action.expression, feature_types, expects="value"
                )
                rule_action.expression_ast = ast_to_json(validated.root)
                if target is not None and target.writable:
                    _validate_expression_output_type(target, validated.inferred_type, details)
            except ExpressionError as exc:
                details.extend(_expression_error_details(f"actions[{index}].expression", exc))
        await _validate_reason_code(session, rule_action, index, details)
    if details:
        raise ValidationFailedError("Rule definition is invalid", details=details)
    return definition


async def prepare_rule_storage(
    session: AsyncSession,
    request: RuleCreateRequest | RuleVersionUpdateRequest,
    actor: User,
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    """Compile an API authoring body into the immutable stored representation."""
    if request.expression is not None:
        _ensure_expression_permission(actor)
        assert request.output_target is not None
        features = await active_feature_map(session)
        target = features.get(request.output_target)
        details: list[dict[str, Any]] = []
        if target is None:
            details.append({"field": "output_target", "issue": "unknown or inactive feature"})
        elif not target.writable:
            details.append({"field": "output_target", "issue": "output target is not writable"})
        try:
            validated = validate_expression(
                request.expression, expression_feature_types(features), expects="value"
            )
            if target is not None and target.writable:
                _validate_expression_output_type(target, validated.inferred_type, details)
        except ExpressionError as exc:
            details.extend(_expression_error_details("expression", exc))
            validated = None
        if details or validated is None:
            raise ValidationFailedError("Expression rule is invalid", details=details)
        return (
            {
                "expression_ast": ast_to_json(validated.root),
                "output_target": request.output_target,
            },
            None,
            request.expression,
        )

    condition, action = request.storage_body()
    definition = await validate_rule_definition(session, condition, action, actor=actor)
    if action is not None:
        compiled_model = definition.branches[0].then[0]
        if compiled_model.expression_ast is None:
            return condition, action, None
        compiled_action = dict(action)
        compiled_action["expression_ast"] = compiled_model.expression_ast
        return condition, compiled_action, None
    return definition.model_dump(mode="json", by_alias=True, exclude_none=True), None, None


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


def normalize_stored_definition(version: RuleVersion) -> StoredRuleDefinition:
    if version.rule_kind == "EXPRESSION":
        raw_ast = version.condition_json.get("expression_ast")
        output_target = version.condition_json.get("output_target")
        if not isinstance(raw_ast, dict) or not isinstance(output_target, str):
            raise ValidationFailedError(
                "Stored expression rule is invalid",
                details=[{"field": "condition_json", "issue": "missing compiled expression"}],
            )
        ast = ast_from_json(raw_ast)
        return ExpressionRuleDefinition(
            expression_ast=ast_to_json(ast),
            output_target=output_target,
            expression_text=version.expression_text or render_expression(ast),
        )
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
                .join(StrategyNode, StrategyNode.strategy_version_id == StrategyVersion.id)
                .where(
                    StrategyNode.node_type == "RULE_SET",
                    StrategyNode.reference_code.in_(codes),
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
    await lock_policy(session)
    condition, action, expression_text = await prepare_rule_storage(session, request, actor)
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
        expression_text=expression_text,
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
            "expression_text": expression_text,
            "status": ConfigStatus.DRAFT,
        },
    )
    await session.commit()
    logger.info("rule.created", extra={"rule_code": rule.rule_code})
    return await get_rule(session, rule.id)


async def create_rule_version(
    session: AsyncSession, rule: Rule, request: RuleVersionUpdateRequest, actor: User
) -> RuleVersion:
    await lock_policy(session, rule)
    condition, action, expression_text = await prepare_rule_storage(session, request, actor)
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
        expression_text=expression_text,
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
        after_value={
            "condition": condition,
            "action": action,
            "rule_kind": request.rule_kind,
            "expression_text": expression_text,
        },
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
    await lock_policy(session, rule, version)
    ensure_editable(version)
    condition, action, expression_text = await prepare_rule_storage(session, request, actor)
    before = {
        "condition": version.condition_json,
        "action": version.action_json,
        "rule_kind": version.rule_kind,
        "expression_text": version.expression_text,
    }
    version.condition_json = condition
    version.action_json = action
    version.rule_kind = request.rule_kind
    version.expression_text = expression_text
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
        after_value={
            "condition": condition,
            "action": action,
            "rule_kind": request.rule_kind,
            "expression_text": expression_text,
        },
    )
    await session.commit()
    return version


async def submit_rule_version(
    session: AsyncSession, rule: Rule, version: RuleVersion, actor: User
) -> RuleVersion:
    await lock_policy(session, rule, version)
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
    await lock_policy(session, rule, version)
    await ensure_independent_approver(
        session,
        version.created_by,
        actor,
        entity_type="RULE_VERSION",
        entity_id=rule.rule_code,
        entity_version=str(version.version),
    )
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
    await lock_policy(session, rule, version)
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
    await lock_policy(session, rule, version)
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

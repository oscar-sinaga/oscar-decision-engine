"""Build a version-pinned engine graph from stored strategy configuration."""

import uuid

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.decision_table import DecisionTableConfig, parse_decision_table_config
from app.engine.dsl import (
    BranchedRuleDefinition,
    ConditionNode,
    ExpressionRuleDefinition,
    normalize_rule_definition,
)
from app.engine.executor import ExecutablePlan, NodePlan, ResolvedRule
from app.engine.expression import ast_from_json, ast_to_json, render_expression
from app.engine.scorecard import ScorecardConfig, parse_scorecard_config
from app.modules.rules.models import RuleSet, RuleSetMember, RuleVersion
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.modules.strategies.models import Strategy, StrategyNode, StrategyVersion
from app.shared.domain.enums import ConfigStatus, NodeType
from app.shared.domain.errors import ConfigurationError

_CONDITION_ADAPTER: TypeAdapter[ConditionNode] = TypeAdapter(ConditionNode)


async def resolve_active_strategy_version(
    session: AsyncSession, product_type: str, segment: str
) -> StrategyVersion:
    result = await session.scalar(
        select(StrategyVersion)
        .join(Strategy, StrategyVersion.strategy_id == Strategy.id)
        .where(
            Strategy.product_type == product_type,
            Strategy.segment == segment,
            StrategyVersion.status == ConfigStatus.ACTIVE,
        )
        .options(
            selectinload(StrategyVersion.strategy),
            selectinload(StrategyVersion.nodes),
            selectinload(StrategyVersion.edges),
        )
        .order_by(StrategyVersion.version.desc())
        .limit(1)
    )
    if result is None:
        raise ConfigurationError(
            f"No active strategy for product '{product_type}' segment '{segment}'"
        )
    return result


async def get_strategy_version(
    session: AsyncSession, strategy_version_id: uuid.UUID
) -> StrategyVersion | None:
    version: StrategyVersion | None = await session.scalar(
        select(StrategyVersion)
        .where(StrategyVersion.id == strategy_version_id)
        .options(
            selectinload(StrategyVersion.strategy),
            selectinload(StrategyVersion.nodes),
            selectinload(StrategyVersion.edges),
        )
    )
    return version


async def build_plan(session: AsyncSession, strategy_version: StrategyVersion) -> ExecutablePlan:
    strategy = strategy_version.strategy
    nodes: dict[str, NodePlan] = {}
    start_keys: list[str] = []
    for stored in strategy_version.nodes:
        node = await _build_node(session, stored)
        nodes[node.node_key] = node
        if node.node_type is NodeType.START:
            start_keys.append(node.node_key)
    if len(start_keys) != 1:
        raise ConfigurationError("Stored strategy graph must contain exactly one START node")

    edges: dict[str, dict[str | None, str]] = {}
    for edge in strategy_version.edges:
        branch = edges.setdefault(edge.from_node_key, {})
        branch[edge.label] = edge.to_node_key

    return ExecutablePlan(
        strategy_code=strategy.strategy_code,
        strategy_version=strategy_version.version,
        strategy_version_id=str(strategy_version.id),
        product_type=strategy.product_type,
        segment=strategy.segment,
        nodes=nodes,
        edges=edges,
        start_key=start_keys[0],
    )


async def _build_node(session: AsyncSession, stored: StrategyNode) -> NodePlan:
    config = stored.config_json or {}
    node_type = NodeType(stored.node_type)
    plan = NodePlan(
        node_key=stored.node_key,
        node_type=node_type,
        name=stored.name,
        reference_code=stored.reference_code,
        on_error=stored.on_error,
        config=config,
    )
    if node_type is NodeType.CONDITION:
        raw = config.get("condition")
        if not isinstance(raw, dict):
            raise ConfigurationError(f"Condition node '{stored.node_key}' has no condition")
        plan.condition = _CONDITION_ADAPTER.validate_python(raw)
    elif node_type is NodeType.RULE_SET:
        plan.rules = await _resolve_rule_set(session, stored.reference_code)
    elif node_type is NodeType.DECISION_TABLE:
        plan.decision_table, plan.reference_version = await _resolve_decision_table(
            session, stored.reference_code
        )
    elif node_type is NodeType.SCORECARD:
        plan.scorecard, plan.reference_version = await _resolve_scorecard(
            session, stored.reference_code
        )
    return plan


async def _resolve_rule_set(
    session: AsyncSession, reference_code: str | None
) -> list[ResolvedRule]:
    rule_set = await session.scalar(
        select(RuleSet)
        .where(RuleSet.code == reference_code)
        .options(selectinload(RuleSet.members).selectinload(RuleSetMember.rule))
    )
    if rule_set is None:
        raise ConfigurationError(f"Rule set '{reference_code}' not found")

    resolved: list[ResolvedRule] = []
    for member in sorted(rule_set.members, key=lambda item: item.execution_order):
        version = await session.scalar(
            select(RuleVersion)
            .where(
                RuleVersion.rule_id == member.rule_id,
                RuleVersion.status == ConfigStatus.ACTIVE,
            )
            .order_by(RuleVersion.version.desc())
            .limit(1)
        )
        if version is None:
            continue
        definition: BranchedRuleDefinition | ExpressionRuleDefinition
        if version.rule_kind == "EXPRESSION":
            raw_ast = version.condition_json.get("expression_ast")
            output_target = version.condition_json.get("output_target")
            if not isinstance(raw_ast, dict) or not isinstance(output_target, str):
                raise ConfigurationError(
                    f"Expression rule '{member.rule.rule_code}' has invalid compiled storage"
                )
            expression_ast = ast_from_json(raw_ast)
            definition = ExpressionRuleDefinition(
                expression_ast=ast_to_json(expression_ast),
                output_target=output_target,
                expression_text=version.expression_text or render_expression(expression_ast),
            )
        else:
            definition = normalize_rule_definition(version.condition_json, version.action_json)
        resolved.append(
            ResolvedRule(
                rule_code=member.rule.rule_code,
                version=version.version,
                rule_kind=version.rule_kind,
                definition=definition,
            )
        )
    return resolved


async def _resolve_decision_table(
    session: AsyncSession, reference_code: str | None
) -> tuple[DecisionTableConfig, int]:
    table = await session.scalar(select(DecisionTable).where(DecisionTable.code == reference_code))
    if table is None:
        raise ConfigurationError(f"Decision table '{reference_code}' not found")
    version = await session.scalar(
        select(DecisionTableVersion)
        .where(
            DecisionTableVersion.decision_table_id == table.id,
            DecisionTableVersion.status == ConfigStatus.ACTIVE,
        )
        .order_by(DecisionTableVersion.version.desc())
        .limit(1)
    )
    if version is None:
        raise ConfigurationError(f"Decision table '{reference_code}' has no active version")
    return parse_decision_table_config(version.config_json), version.version


async def _resolve_scorecard(
    session: AsyncSession, reference_code: str | None
) -> tuple[ScorecardConfig, int]:
    scorecard = await session.scalar(select(Scorecard).where(Scorecard.code == reference_code))
    if scorecard is None:
        raise ConfigurationError(f"Scorecard '{reference_code}' not found")
    version = await session.scalar(
        select(ScorecardVersion)
        .where(
            ScorecardVersion.scorecard_id == scorecard.id,
            ScorecardVersion.status == ConfigStatus.ACTIVE,
        )
        .order_by(ScorecardVersion.version.desc())
        .limit(1)
    )
    if version is None:
        raise ConfigurationError(f"Scorecard '{reference_code}' has no active version")
    return parse_scorecard_config(version.config_json), version.version

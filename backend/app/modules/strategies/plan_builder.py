"""Builds a version-pinned :class:`ExecutablePlan` from stored configuration.

Every referenced rule/decision-table/scorecard is resolved to its exact
ACTIVE version at build time, so the resulting trace can name the precise
configuration used (docs/18 §5).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.decision_table import DecisionTableConfig, parse_decision_table_config
from app.engine.dsl import normalize_rule_definition
from app.engine.executor import ExecutablePlan, ResolvedRule, StepPlan
from app.engine.scorecard import ScorecardConfig, parse_scorecard_config
from app.modules.rules.models import RuleSet, RuleSetMember, RuleVersion
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.modules.strategies.models import Strategy, StrategyStep, StrategyVersion
from app.shared.domain.enums import ConfigStatus, StepType
from app.shared.domain.errors import ConfigurationError


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
            selectinload(StrategyVersion.steps),
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
            selectinload(StrategyVersion.steps),
        )
    )
    return version


async def build_plan(session: AsyncSession, strategy_version: StrategyVersion) -> ExecutablePlan:
    strategy = strategy_version.strategy
    steps: list[StepPlan] = []
    for step in sorted(strategy_version.steps, key=lambda s: s.step_order):
        steps.append(await _build_step(session, step))
    return ExecutablePlan(
        strategy_code=strategy.strategy_code,
        strategy_version=strategy_version.version,
        strategy_version_id=str(strategy_version.id),
        product_type=strategy.product_type,
        segment=strategy.segment,
        steps=steps,
    )


async def _build_step(session: AsyncSession, step: StrategyStep) -> StepPlan:
    plan = StepPlan(
        order=step.step_order,
        step_type=step.step_type,
        name=step.name,
        reference_code=step.reference_code,
        on_error=step.on_error,
        config=step.config_json or {},
    )
    if step.step_type == StepType.RULE_SET:
        plan.rules = await _resolve_rule_set(session, step)
    elif step.step_type in (StepType.DECISION_TABLE, StepType.OUTPUT):
        plan.decision_table, plan.reference_version = await _resolve_decision_table(session, step)
    elif step.step_type == StepType.SCORECARD:
        plan.scorecard, plan.reference_version = await _resolve_scorecard(session, step)
    return plan


async def _resolve_rule_set(session: AsyncSession, step: StrategyStep) -> list[ResolvedRule]:
    rule_set = await session.scalar(
        select(RuleSet)
        .where(RuleSet.code == step.reference_code)
        .options(selectinload(RuleSet.members).selectinload(RuleSetMember.rule))
    )
    if rule_set is None:
        raise ConfigurationError(f"Rule set '{step.reference_code}' not found")

    resolved: list[ResolvedRule] = []
    for member in sorted(rule_set.members, key=lambda m: m.execution_order):
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
            # A rule without an active version is skipped deliberately: rule
            # sets may contain drafts pending activation.
            continue
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
    session: AsyncSession, step: StrategyStep
) -> tuple[DecisionTableConfig, int]:
    table = await session.scalar(
        select(DecisionTable).where(DecisionTable.code == step.reference_code)
    )
    if table is None:
        raise ConfigurationError(f"Decision table '{step.reference_code}' not found")
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
        raise ConfigurationError(f"Decision table '{step.reference_code}' has no active version")
    return parse_decision_table_config(version.config_json), version.version


async def _resolve_scorecard(
    session: AsyncSession, step: StrategyStep
) -> tuple[ScorecardConfig, int]:
    scorecard = await session.scalar(select(Scorecard).where(Scorecard.code == step.reference_code))
    if scorecard is None:
        raise ConfigurationError(f"Scorecard '{step.reference_code}' not found")
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
        raise ConfigurationError(f"Scorecard '{step.reference_code}' has no active version")
    return parse_scorecard_config(version.config_json), version.version

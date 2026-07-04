"""Strategy management service: step validation, versioning, activation, rollback.

Activation enforces the single-active invariant per product+segment across
*all* strategies (docs/02 §6.3) and verifies every referenced configuration
is resolvable so the runtime cannot load an unexecutable strategy.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.features import DERIVED_FEATURES, KNOWN_FEATURES
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.governance.service import (
    ensure_maker_checker,
    open_approval_request,
    resolve_approval_request,
)
from app.modules.rules.models import RuleSet
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.modules.strategies.models import Strategy, StrategyStep, StrategyVersion
from app.modules.strategies.schemas import (
    StepRequest,
    StrategyCreateRequest,
    StrategyVersionCreateRequest,
)
from app.shared.domain.enums import ApprovalStatus, ConfigStatus, StepType
from app.shared.domain.errors import ConflictError, NotFoundError, ValidationFailedError
from app.shared.domain.version_lifecycle import (
    ensure_editable,
    reject_version,
    submit_for_approval,
)
from app.shared.logging import get_logger

logger = get_logger("oscar.strategies")


async def get_strategy(session: AsyncSession, strategy_id: uuid.UUID) -> Strategy:
    strategy = await session.scalar(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(selectinload(Strategy.versions).selectinload(StrategyVersion.steps))
    )
    if strategy is None:
        raise NotFoundError(f"Strategy '{strategy_id}' not found")
    return strategy


def get_version(strategy: Strategy, version_id: uuid.UUID) -> StrategyVersion:
    for version in strategy.versions:
        if version.id == version_id:
            return version
    raise NotFoundError(f"Strategy version '{version_id}' not found for '{strategy.strategy_code}'")


async def validate_steps(session: AsyncSession, steps: list[StepRequest]) -> None:
    """Reject steps referencing unknown configs, features, or calculations."""
    details: list[dict[str, str]] = []
    for step in steps:
        prefix = f"steps[order={step.order}]"
        if step.type == StepType.VALIDATION:
            for field in step.config.get("required_fields", []):
                if field not in KNOWN_FEATURES:
                    details.append(
                        {"field": f"{prefix}.required_fields", "issue": f"unknown feature: {field}"}
                    )
        elif step.type == StepType.CALCULATION:
            for code in step.config.get("calculations", []):
                if code not in DERIVED_FEATURES:
                    details.append(
                        {"field": f"{prefix}.calculations", "issue": f"unknown calculation: {code}"}
                    )
        elif step.type == StepType.RULE_SET:
            if not step.reference_code or not await session.scalar(
                select(RuleSet).where(RuleSet.code == step.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown rule set: {step.reference_code}",
                    }
                )
        elif step.type in (StepType.DECISION_TABLE, StepType.OUTPUT):
            if not step.reference_code or not await session.scalar(
                select(DecisionTable).where(DecisionTable.code == step.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown decision table: {step.reference_code}",
                    }
                )
        elif step.type == StepType.SCORECARD:
            if not step.reference_code or not await session.scalar(
                select(Scorecard).where(Scorecard.code == step.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown scorecard: {step.reference_code}",
                    }
                )
    if details:
        raise ValidationFailedError("Strategy steps are invalid", details=details)


async def _verify_references_activatable(session: AsyncSession, version: StrategyVersion) -> None:
    """Every referenced table/scorecard must have an ACTIVE version at activation."""
    details: list[dict[str, str]] = []
    for step in version.steps:
        if step.step_type in (StepType.DECISION_TABLE, StepType.OUTPUT):
            table = await session.scalar(
                select(DecisionTable).where(DecisionTable.code == step.reference_code)
            )
            active = table and await session.scalar(
                select(DecisionTableVersion).where(
                    DecisionTableVersion.decision_table_id == table.id,
                    DecisionTableVersion.status == ConfigStatus.ACTIVE,
                )
            )
            if not active:
                details.append(
                    {
                        "field": step.reference_code or "",
                        "issue": "decision table has no active version",
                    }
                )
        elif step.step_type == StepType.SCORECARD:
            scorecard = await session.scalar(
                select(Scorecard).where(Scorecard.code == step.reference_code)
            )
            active = scorecard and await session.scalar(
                select(ScorecardVersion).where(
                    ScorecardVersion.scorecard_id == scorecard.id,
                    ScorecardVersion.status == ConfigStatus.ACTIVE,
                )
            )
            if not active:
                details.append(
                    {"field": step.reference_code or "", "issue": "scorecard has no active version"}
                )
    if details:
        raise ValidationFailedError(
            "Strategy references configuration without an active version", details=details
        )


async def create_strategy(
    session: AsyncSession, request: StrategyCreateRequest, actor: User
) -> Strategy:
    duplicate = await session.scalar(
        select(Strategy).where(Strategy.strategy_code == request.strategy_code)
    )
    if duplicate is not None:
        raise ConflictError(f"Strategy code '{request.strategy_code}' already exists")
    strategy = Strategy(
        strategy_code=request.strategy_code,
        name=request.name,
        product_type=request.product_type,
        segment=request.segment,
        owner_team=request.owner_team,
    )
    session.add(strategy)
    await session.flush()
    record_audit_event(
        session,
        event_type="STRATEGY_CREATED",
        entity_type="STRATEGY",
        entity_id=strategy.strategy_code,
        action="CREATE_STRATEGY",
        actor=actor,
        after_value={
            "name": request.name,
            "product_type": request.product_type,
            "segment": request.segment,
        },
    )
    await session.commit()
    return await get_strategy(session, strategy.id)


def _steps_snapshot(version: StrategyVersion) -> list[dict[str, object]]:
    return [
        {
            "order": s.step_order,
            "type": s.step_type,
            "name": s.name,
            "reference_code": s.reference_code,
            "on_error": s.on_error,
            "config": s.config_json,
        }
        for s in sorted(version.steps, key=lambda s: s.step_order)
    ]


async def create_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    request: StrategyVersionCreateRequest,
    actor: User,
) -> StrategyVersion:
    await validate_steps(session, request.steps)
    open_versions = [
        v
        for v in strategy.versions
        if v.status in (ConfigStatus.DRAFT, ConfigStatus.PENDING_APPROVAL)
    ]
    if open_versions:
        raise ConflictError(
            f"Strategy '{strategy.strategy_code}' already has an open draft/pending version"
        )
    next_version = max((v.version for v in strategy.versions), default=0) + 1
    version = StrategyVersion(
        strategy_id=strategy.id,
        version=next_version,
        status=ConfigStatus.DRAFT,
        version_note=request.version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()
    _apply_steps(session, version, request.steps)
    await session.flush()
    await session.refresh(version, ["steps"])
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_CREATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(next_version),
        action="CREATE_STRATEGY_VERSION",
        actor=actor,
        after_value={"steps": _steps_snapshot(version)},
    )
    await session.commit()
    return version


def _apply_steps(session: AsyncSession, version: StrategyVersion, steps: list[StepRequest]) -> None:
    for step in steps:
        session.add(
            StrategyStep(
                strategy_version_id=version.id,
                step_order=step.order,
                step_type=step.type,
                name=step.name or f"{step.type.title()} step",
                reference_code=step.reference_code,
                on_error=step.on_error,
                config_json=step.config,
            )
        )


async def update_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    request: StrategyVersionCreateRequest,
    actor: User,
) -> StrategyVersion:
    ensure_editable(version)
    await validate_steps(session, request.steps)
    before = {"steps": _steps_snapshot(version)}
    for step in list(version.steps):
        await session.delete(step)
    await session.flush()
    _apply_steps(session, version, request.steps)
    version.version_note = request.version_note or version.version_note
    await session.flush()
    await session.refresh(version, ["steps"])
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_UPDATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="UPDATE_STRATEGY_VERSION",
        actor=actor,
        before_value=before,
        after_value={"steps": _steps_snapshot(version)},
    )
    await session.commit()
    return version


async def submit_strategy_version(
    session: AsyncSession, strategy: Strategy, version: StrategyVersion, actor: User
) -> StrategyVersion:
    before = version.status
    submit_for_approval(version)
    open_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        requested_by=actor,
        change_summary=version.version_note,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_SUBMITTED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="SUBMIT_FOR_APPROVAL",
        actor=actor,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version


async def reject_strategy_version(
    session: AsyncSession, strategy: Strategy, version: StrategyVersion, actor: User, reason: str
) -> StrategyVersion:
    before = version.status
    reject_version(version)
    await resolve_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        status=ApprovalStatus.REJECTED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_REJECTED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="REJECT_STRATEGY_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version


async def _retire_competing_active_versions(
    session: AsyncSession, strategy: Strategy, keep: StrategyVersion
) -> list[str]:
    """Retire ACTIVE versions of any strategy sharing product+segment."""
    competing = (
        await session.scalars(
            select(StrategyVersion)
            .join(Strategy, StrategyVersion.strategy_id == Strategy.id)
            .where(
                Strategy.product_type == strategy.product_type,
                Strategy.segment == strategy.segment,
                StrategyVersion.status == ConfigStatus.ACTIVE,
                StrategyVersion.id != keep.id,
            )
            .options(selectinload(StrategyVersion.strategy))
        )
    ).all()
    retired: list[str] = []
    for version in competing:
        version.status = ConfigStatus.RETIRED
        version.effective_to = datetime.now(UTC)
        retired.append(f"{version.strategy.strategy_code}_V{version.version}")
    return retired


async def activate_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    actor: User,
    reason: str | None,
) -> StrategyVersion:
    if version.status != ConfigStatus.PENDING_APPROVAL:
        raise ConflictError(
            f"Version {version.version} is {version.status}; submit for approval first"
        )
    ensure_maker_checker(version.created_by, actor)
    await _verify_references_activatable(session, version)
    before = version.status
    retired = await _retire_competing_active_versions(session, strategy, version)
    version.status = ConfigStatus.ACTIVE
    version.activated_at = datetime.now(UTC)
    version.activated_by = actor.id
    version.effective_from = datetime.now(UTC)
    await resolve_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        status=ApprovalStatus.APPROVED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_ACTIVATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="ACTIVATE_STRATEGY_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": ConfigStatus.ACTIVE, "retired_versions": retired},
        metadata={"product_type": strategy.product_type, "segment": strategy.segment},
    )
    await session.commit()
    logger.info(
        "strategy.version_activated",
        extra={
            "strategy_code": strategy.strategy_code,
            "version": version.version,
            "retired_versions": retired,
        },
    )
    return version


async def rollback_to_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    actor: User,
    reason: str,
) -> StrategyVersion:
    """Reactivate a previously retired version (docs/14 §8)."""
    if not reason.strip():
        raise ValidationFailedError(
            "Rollback requires a reason",
            details=[{"field": "reason", "issue": "required"}],
        )
    if version.status != ConfigStatus.RETIRED:
        raise ConflictError(
            f"Only RETIRED versions can be rolled back to (current: {version.status})"
        )
    await _verify_references_activatable(session, version)
    retired = await _retire_competing_active_versions(session, strategy, version)
    version.status = ConfigStatus.ACTIVE
    version.activated_at = datetime.now(UTC)
    version.activated_by = actor.id
    version.effective_from = datetime.now(UTC)
    version.effective_to = None
    record_audit_event(
        session,
        event_type="STRATEGY_ROLLED_BACK",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="ROLLBACK_STRATEGY",
        actor=actor,
        reason=reason,
        before_value={"status": ConfigStatus.RETIRED, "previously_active": retired},
        after_value={"status": ConfigStatus.ACTIVE},
    )
    await session.commit()
    logger.info(
        "strategy.rolled_back",
        extra={"strategy_code": strategy.strategy_code, "version": version.version},
    )
    return version

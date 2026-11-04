"""Side-effect-free simulation service (docs/12).

Simulation runs the same engine as production but persists **only**
simulation records: no application, decision, decision-trace, or
manual-review rows are created, and no production configuration is touched.
"""

import uuid
from collections import Counter
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.executor import ExecutablePlan, ExecutionResult, run_strategy
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.simulations.models import Simulation, SimulationResult
from app.modules.simulations.schemas import (
    BatchSimulationRequest,
    BatchSimulationResponse,
    DecisionShift,
    SegmentImpact,
    SimulationDifference,
    SimulationOutcome,
    SingleSimulationRequest,
    SingleSimulationResponse,
    StrategyAggregate,
)
from app.modules.strategies.models import StrategyVersion
from app.modules.strategies.plan_builder import (
    build_plan,
    get_strategy_version,
    resolve_active_strategy_version,
)
from app.shared.domain.enums import (
    DecisionType,
    ExecutionMode,
    SimulationStatus,
    SimulationType,
)
from app.shared.domain.errors import NotFoundError
from app.shared.logging import get_correlation_id, get_logger, get_request_id
from app.shared.utils.ids import display_id
from app.shared.utils.masking import redact, sanitize_snapshot

logger = get_logger("oscar.simulations")

_APPROVE_DECISIONS = {DecisionType.APPROVE.value, DecisionType.APPROVE_WITH_CONDITION.value}
_REVIEW_DECISIONS = {DecisionType.MANUAL_REVIEW.value, DecisionType.FRAUD_INVESTIGATION.value}

_COMPARED_FIELDS = (
    "decision",
    "risk_grade",
    "approved_limit",
    "approved_tenor_months",
    "pricing_rate",
    "reason_codes",
)


def _outcome(plan: ExecutablePlan, result: ExecutionResult) -> SimulationOutcome:
    return SimulationOutcome(
        strategy_version=f"{plan.strategy_code}_V{plan.strategy_version}",
        decision=result.final_decision.value,
        risk_grade=result.risk_grade,
        score=result.score,
        approved_limit=result.approved_limit,
        approved_tenor_months=result.approved_tenor_months,
        pricing_rate=result.pricing_rate,
        reason_codes=result.reason_codes,
        validation_failures=[f.model_dump() for f in result.validation_failures],
    )


def _simulation_trace(
    plan: ExecutablePlan, result: ExecutionResult, payload: dict[str, Any]
) -> dict[str, Any]:
    return {
        "execution_mode": ExecutionMode.SIMULATION.value,
        "strategy": {
            "strategy_code": plan.strategy_code,
            "version": plan.strategy_version,
            "execution": "GRAPH",
        },
        "input_snapshot": sanitize_snapshot(payload),
        "feature_values": sanitize_snapshot(result.feature_values),
        "outputs": sanitize_snapshot(
            {
                key: value
                for key, value in result.feature_values.items()
                if key.startswith("outputs.")
            }
        ),
        "steps": redact(result.step_results),
        "score_result": redact(result.score_result),
        "final_decision": {
            "decision": result.final_decision.value,
            "reason_codes": result.reason_codes,
        },
        "errors": redact(result.errors),
        "metadata": {
            "latency_ms": result.latency_ms,
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
            "executed_at": result.executed_at,
        },
    }


def _differences(active: SimulationOutcome, draft: SimulationOutcome) -> list[SimulationDifference]:
    diffs: list[SimulationDifference] = []
    for field in _COMPARED_FIELDS:
        active_value = getattr(active, field)
        draft_value = getattr(draft, field)
        if active_value != draft_value:
            diffs.append(SimulationDifference(field=field, active=active_value, draft=draft_value))
    return diffs


async def _version_by_id(session: AsyncSession, strategy_version_id: str) -> StrategyVersion:
    try:
        version_uuid = uuid.UUID(strategy_version_id)
    except ValueError as exc:
        raise NotFoundError(f"Strategy version '{strategy_version_id}' not found") from exc
    version = await get_strategy_version(session, version_uuid)
    if version is None:
        raise NotFoundError(f"Strategy version '{strategy_version_id}' not found")
    return version


async def _resolve_target_version(
    session: AsyncSession, request: SingleSimulationRequest
) -> StrategyVersion:
    if request.strategy_version_id is not None:
        return await _version_by_id(session, request.strategy_version_id)
    return await resolve_active_strategy_version(
        session,
        request.application_payload.product_type.value,
        request.application_payload.segment,
    )


async def run_single_simulation(
    session: AsyncSession, request: SingleSimulationRequest, actor: User
) -> SingleSimulationResponse:
    payload = request.application_payload.to_payload()

    target_version = await _resolve_target_version(session, request)
    target_plan = await build_plan(session, target_version)
    target_result = run_strategy(target_plan, payload)
    draft_outcome = _outcome(target_plan, target_result)

    active_outcome: SimulationOutcome | None = None
    active_trace: dict[str, Any] | None = None
    differences: list[SimulationDifference] = []
    compare_version: StrategyVersion | None = None
    if request.compare_with_active:
        compare_version = await resolve_active_strategy_version(
            session,
            request.application_payload.product_type.value,
            request.application_payload.segment,
        )
        if compare_version.id != target_version.id:
            active_plan = await build_plan(session, compare_version)
            active_result = run_strategy(active_plan, payload)
            active_outcome = _outcome(active_plan, active_result)
            active_trace = _simulation_trace(active_plan, active_result, payload)
            differences = _differences(active_outcome, draft_outcome)
        else:
            compare_version = None

    simulation = Simulation(
        simulation_id=display_id("SIM"),
        name=request.simulation_name,
        type=SimulationType.SINGLE,
        status=SimulationStatus.COMPLETED,
        strategy_version_id=target_version.id,
        compare_strategy_version_id=compare_version.id if compare_version else None,
        created_by=actor.id,
    )
    session.add(simulation)
    await session.flush()
    session.add(
        SimulationResult(
            simulation_pk=simulation.id,
            result_json={
                "draft_result": draft_outcome.model_dump(),
                "active_result": active_outcome.model_dump() if active_outcome else None,
            },
            trace_json={
                "draft_trace": _simulation_trace(target_plan, target_result, payload),
                "active_trace": active_trace,
            },
            difference_json=[d.model_dump() for d in differences],
        )
    )
    record_audit_event(
        session,
        event_type="SIMULATION_EXECUTED",
        entity_type="SIMULATION",
        entity_id=simulation.simulation_id,
        action="RUN_SIMULATION",
        actor=actor,
        after_value={
            "strategy_version": draft_outcome.strategy_version,
            "decision": draft_outcome.decision,
            "compared_with_active": active_outcome is not None,
        },
        metadata={"simulation_name": request.simulation_name},
    )
    await session.commit()
    logger.info(
        "simulation.executed",
        extra={
            "simulation_id": simulation.simulation_id,
            "strategy_version": draft_outcome.strategy_version,
            "decision": draft_outcome.decision,
            "duration_ms": target_result.latency_ms,
        },
    )
    return SingleSimulationResponse(
        simulation_id=simulation.simulation_id,
        draft_result=draft_outcome,
        active_result=active_outcome,
        differences=differences,
    )


def _aggregate(strategy_version: str, results: list[ExecutionResult]) -> StrategyAggregate:
    total = len(results)
    decision_counts: Counter[str] = Counter()
    reason_dist: Counter[str] = Counter()
    grade_dist: Counter[str] = Counter()
    for result in results:
        decision_counts[result.final_decision.value] += 1
        for code in result.reason_codes:
            reason_dist[code] += 1
        if result.risk_grade:
            grade_dist[result.risk_grade] += 1

    def rate(values: set[str]) -> float:
        if total == 0:
            return 0.0
        return round(sum(decision_counts.get(v, 0) for v in values) / total, 4)

    return StrategyAggregate(
        strategy_version=strategy_version,
        decision_counts=dict(decision_counts),
        approval_rate=rate(_APPROVE_DECISIONS),
        reject_rate=rate({DecisionType.REJECT.value}),
        manual_review_rate=rate(_REVIEW_DECISIONS),
        error_rate=rate({DecisionType.ERROR.value}),
        reason_code_distribution=dict(reason_dist.most_common()),
        risk_grade_distribution=dict(sorted(grade_dist.items())),
    )


async def run_batch_simulation(
    session: AsyncSession, request: BatchSimulationRequest, actor: User
) -> BatchSimulationResponse:
    """Policy impact analysis over a synthetic population (docs/12 §7).

    Persists only simulation records; no production rows are created. The
    candidate (target) strategy version is applied to every payload; the active
    strategy for each payload's product/segment provides the comparison.
    """
    target_version = await _version_by_id(session, request.strategy_version_id)
    target_plan = await build_plan(session, target_version)
    target_label = f"{target_plan.strategy_code}_V{target_plan.strategy_version}"

    active_plan_cache: dict[tuple[str, str], ExecutablePlan | None] = {}

    async def active_plan_for(product: str, segment: str) -> ExecutablePlan | None:
        key = (product, segment)
        if key not in active_plan_cache:
            try:
                version = await resolve_active_strategy_version(session, product, segment)
                active_plan_cache[key] = await build_plan(session, version)
            except NotFoundError:
                active_plan_cache[key] = None
        return active_plan_cache[key]

    target_results: list[ExecutionResult] = []
    active_results: list[ExecutionResult] = []
    shifts: Counter[tuple[str, str]] = Counter()
    segment_rows: dict[str, dict[str, Counter[str]]] = {}

    for item in request.application_payloads:
        payload = item.to_payload()
        target_result = run_strategy(target_plan, payload)
        target_results.append(target_result)

        segment_key = f"{item.product_type.value}/{item.channel}"
        seg = segment_rows.setdefault(segment_key, {"target": Counter(), "active": Counter()})
        seg["target"][target_result.final_decision.value] += 1

        if request.compare_with_active:
            active_plan = await active_plan_for(item.product_type.value, item.segment)
            if active_plan is not None:
                active_result = run_strategy(active_plan, payload)
                active_results.append(active_result)
                seg["active"][active_result.final_decision.value] += 1
                shifts[
                    (active_result.final_decision.value, target_result.final_decision.value)
                ] += 1

    target_aggregate = _aggregate(target_label, target_results)
    active_aggregate = (
        _aggregate("ACTIVE", active_results)
        if request.compare_with_active and active_results
        else None
    )
    decision_shifts = [
        DecisionShift(from_decision=from_d, to_decision=to_d, count=count)
        for (from_d, to_d), count in sorted(shifts.items(), key=lambda kv: -kv[1])
        if from_d != to_d
    ]
    segment_impact = [
        SegmentImpact(
            segment=key,
            total=sum(counters["target"].values()),
            target_decision_counts=dict(counters["target"]),
            active_decision_counts=(
                dict(counters["active"]) if request.compare_with_active else None
            ),
        )
        for key, counters in sorted(segment_rows.items())
    ]

    simulation = Simulation(
        simulation_id=display_id("SIM"),
        name=request.simulation_name,
        type=SimulationType.BATCH,
        status=SimulationStatus.COMPLETED,
        strategy_version_id=target_version.id,
        created_by=actor.id,
    )
    session.add(simulation)
    await session.flush()
    session.add(
        SimulationResult(
            simulation_pk=simulation.id,
            result_json={
                "total_records": len(target_results),
                "target": target_aggregate.model_dump(),
                "active": active_aggregate.model_dump() if active_aggregate else None,
            },
            trace_json={"execution_mode": ExecutionMode.SIMULATION.value},
            difference_json=[s.model_dump() for s in decision_shifts],
        )
    )
    record_audit_event(
        session,
        event_type="SIMULATION_EXECUTED",
        entity_type="SIMULATION",
        entity_id=simulation.simulation_id,
        action="RUN_BATCH_SIMULATION",
        actor=actor,
        after_value={
            "strategy_version": target_label,
            "total_records": len(target_results),
            "compared_with_active": active_aggregate is not None,
        },
        metadata={"simulation_name": request.simulation_name},
    )
    await session.commit()
    logger.info(
        "simulation.batch_executed",
        extra={
            "simulation_id": simulation.simulation_id,
            "strategy_version": target_label,
            "total_records": len(target_results),
        },
    )
    return BatchSimulationResponse(
        simulation_id=simulation.simulation_id,
        total_records=len(target_results),
        target=target_aggregate,
        active=active_aggregate,
        decision_shifts=decision_shifts,
        segment_impact=segment_impact,
    )

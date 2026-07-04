"""Side-effect-free simulation service (docs/12).

Simulation runs the same engine as production but persists **only**
simulation records: no application, decision, decision-trace, or
manual-review rows are created, and no production configuration is touched.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.executor import ExecutablePlan, ExecutionResult, run_strategy
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.simulations.models import Simulation, SimulationResult
from app.modules.simulations.schemas import (
    SimulationDifference,
    SimulationOutcome,
    SingleSimulationRequest,
    SingleSimulationResponse,
)
from app.modules.strategies.models import StrategyVersion
from app.modules.strategies.plan_builder import (
    build_plan,
    get_strategy_version,
    resolve_active_strategy_version,
)
from app.shared.domain.enums import ExecutionMode, SimulationStatus, SimulationType
from app.shared.domain.errors import NotFoundError
from app.shared.logging import get_correlation_id, get_logger, get_request_id
from app.shared.utils.ids import display_id
from app.shared.utils.masking import sanitize_snapshot

logger = get_logger("oscar.simulations")

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
        "strategy": {"strategy_code": plan.strategy_code, "version": plan.strategy_version},
        "input_snapshot": sanitize_snapshot(payload),
        "feature_values": result.feature_values,
        "steps": result.step_results,
        "score_result": result.score_result,
        "final_decision": {
            "decision": result.final_decision.value,
            "reason_codes": result.reason_codes,
        },
        "errors": result.errors,
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


async def _resolve_target_version(
    session: AsyncSession, request: SingleSimulationRequest
) -> StrategyVersion:
    if request.strategy_version_id is not None:
        try:
            version_uuid = uuid.UUID(request.strategy_version_id)
        except ValueError as exc:
            raise NotFoundError(
                f"Strategy version '{request.strategy_version_id}' not found"
            ) from exc
        version = await get_strategy_version(session, version_uuid)
        if version is None:
            raise NotFoundError(f"Strategy version '{request.strategy_version_id}' not found")
        return version
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

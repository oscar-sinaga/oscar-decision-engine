"""Decision runtime service.

Orchestrates one production decision:
payload → active strategy plan → engine execution → decision + immutable
trace + manual-review case + business audit event, all persisted in one
transaction. If any mandatory persistence (including the audit event) fails,
the whole decision fails — no silent unaudited decisions (docs/18 §12).
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.executor import ExecutionResult, run_strategy
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.decisions.models import Application, Decision, DecisionTrace
from app.modules.decisions.schemas import (
    DecisionRequest,
    DecisionResponse,
    ReasonCodeItem,
    TraceResponse,
    TraceStrategyRef,
)
from app.modules.manual_review.models import ManualReviewCase
from app.modules.manual_review.service import sla_due_at
from app.modules.reason_codes.models import ReasonCode
from app.modules.strategies.plan_builder import build_plan, resolve_active_strategy_version
from app.shared.domain.enums import (
    ApplicationStatus,
    CasePriority,
    CaseStatus,
    DecisionType,
    ExecutionMode,
)
from app.shared.domain.errors import ValidationFailedError
from app.shared.logging import get_correlation_id, get_logger, get_request_id
from app.shared.utils.ids import display_id
from app.shared.utils.masking import sanitize_snapshot

logger = get_logger("oscar.decisions")

REVIEW_DECISIONS = {DecisionType.MANUAL_REVIEW, DecisionType.FRAUD_INVESTIGATION}


async def execute_decision(
    session: AsyncSession,
    request: DecisionRequest,
    *,
    actor: User,
    idempotency_key: str | None = None,
) -> DecisionResponse:
    if idempotency_key:
        existing = await session.scalar(
            select(Decision).where(Decision.idempotency_key == idempotency_key)
        )
        if existing is not None:
            logger.info(
                "decision.idempotent_replay",
                extra={"decision_id": existing.decision_id, "idempotency_key_present": True},
            )
            return await build_decision_response(session, existing)

    payload = request.to_payload()
    strategy_version = await resolve_active_strategy_version(
        session, request.product_type.value, request.segment
    )
    plan = await build_plan(session, strategy_version)
    result = run_strategy(plan, payload)

    snapshot = sanitize_snapshot(payload)

    application = Application(
        application_id=request.application_id,
        product_type=request.product_type,
        channel=request.channel,
        applicant_id=str(request.applicant.get("customer_id") or "") or None,
        status=ApplicationStatus.RECEIVED,
        payload_snapshot=snapshot,
    )
    session.add(application)
    # Assign python-side UUID defaults before other rows reference them.
    await session.flush()

    if result.validation_failures:
        application.status = ApplicationStatus.ERROR
        record_audit_event(
            session,
            event_type="DECISION_VALIDATION_FAILED",
            entity_type="APPLICATION",
            entity_id=request.application_id,
            action="EXECUTE_DECISION",
            actor=actor,
            metadata={
                "strategy_version": f"{plan.strategy_code}_V{plan.strategy_version}",
                "missing_fields": [f.field for f in result.validation_failures],
            },
        )
        await session.commit()
        raise ValidationFailedError(
            "Application payload is missing required decision inputs",
            details=[f.model_dump() for f in result.validation_failures],
        )

    decision = _build_decision_row(request, application, strategy_version.id, result)
    decision.idempotency_key = idempotency_key
    session.add(decision)
    try:
        await session.flush()
    except IntegrityError:
        # Idempotency race: another request with the same key persisted first.
        await session.rollback()
        if idempotency_key:
            existing = await session.scalar(
                select(Decision).where(Decision.idempotency_key == idempotency_key)
            )
            if existing is not None:
                return await build_decision_response(session, existing)
        raise

    trace = _build_trace_row(decision, snapshot, result)
    session.add(trace)

    case: ManualReviewCase | None = None
    if result.final_decision in REVIEW_DECISIONS:
        priority = (
            CasePriority.HIGH
            if result.final_decision is DecisionType.FRAUD_INVESTIGATION
            else CasePriority.MEDIUM
        )
        case = ManualReviewCase(
            case_id=display_id("CASE"),
            application_pk=application.id,
            decision_pk=decision.id,
            system_decision=result.final_decision,
            status=CaseStatus.NEW,
            priority=priority,
            sla_due_at=sla_due_at(priority, datetime.now(UTC)),
        )
        session.add(case)
        application.status = ApplicationStatus.PENDING_REVIEW
    else:
        application.status = ApplicationStatus.DECIDED

    record_audit_event(
        session,
        event_type="DECISION_EXECUTED",
        entity_type="DECISION",
        entity_id=decision.decision_id,
        entity_version=f"{plan.strategy_code}_V{plan.strategy_version}",
        action="EXECUTE_DECISION",
        actor=actor,
        after_value={
            "decision": result.final_decision.value,
            "reason_codes": result.reason_codes,
            "risk_grade": result.risk_grade,
        },
        metadata={
            "application_id": request.application_id,
            "product_type": request.product_type.value,
            "channel": request.channel,
            "trace_id": trace.trace_id,
            "manual_review_case_id": case.case_id if case else None,
        },
    )
    if case is not None:
        record_audit_event(
            session,
            event_type="MANUAL_REVIEW_CASE_CREATED",
            entity_type="MANUAL_REVIEW_CASE",
            entity_id=case.case_id,
            action="CREATE_CASE",
            actor=actor,
            after_value={
                "system_decision": result.final_decision.value,
                "priority": case.priority.value,
                "status": case.status.value,
            },
            metadata={"decision_id": decision.decision_id},
        )

    await session.commit()

    logger.info(
        "decision.executed",
        extra={
            "decision_id": decision.decision_id,
            "application_id": request.application_id,
            "decision": result.final_decision.value,
            "strategy_version": f"{plan.strategy_code}_V{plan.strategy_version}",
            "duration_ms": result.latency_ms,
        },
    )
    return await build_decision_response(session, decision, case_id=case.case_id if case else None)


def _build_decision_row(
    request: DecisionRequest,
    application: Application,
    strategy_version_id: Any,
    result: ExecutionResult,
) -> Decision:
    return Decision(
        decision_id=display_id("DEC"),
        application_pk=application.id,
        external_application_id=request.application_id,
        decision=result.final_decision,
        risk_grade=result.risk_grade,
        score=Decimal(str(result.score)) if result.score is not None else None,
        approved_limit=(
            Decimal(str(result.approved_limit)) if result.approved_limit is not None else None
        ),
        approved_tenor_months=result.approved_tenor_months,
        pricing_rate=(
            Decimal(str(result.pricing_rate)) if result.pricing_rate is not None else None
        ),
        reason_codes_json=[{"code": code} for code in result.reason_codes],
        strategy_version_id=strategy_version_id,
        execution_mode=ExecutionMode.PRODUCTION,
    )


def _build_trace_row(
    decision: Decision, snapshot: dict[str, Any], result: ExecutionResult
) -> DecisionTrace:
    return DecisionTrace(
        trace_id=display_id("TRC"),
        decision_pk=decision.id,
        execution_mode=ExecutionMode.PRODUCTION,
        input_snapshot=snapshot,
        feature_values=result.feature_values,
        step_results=result.step_results,
        score_results=result.score_result,
        final_output={
            "decision": result.final_decision.value,
            "reason_codes": result.reason_codes,
            "risk_grade": result.risk_grade,
            "score": result.score,
            "approved_limit": result.approved_limit,
            "approved_tenor_months": result.approved_tenor_months,
            "pricing_rate": result.pricing_rate,
        },
        errors=result.errors,
        latency_ms=result.latency_ms,
        request_id=get_request_id(),
        correlation_id=get_correlation_id(),
    )


async def resolve_reason_messages(session: AsyncSession, codes: list[str]) -> list[ReasonCodeItem]:
    if not codes:
        return []
    rows = await session.scalars(select(ReasonCode).where(ReasonCode.code.in_(codes)))
    messages = {row.code: row.internal_message for row in rows}
    return [ReasonCodeItem(code=code, message=messages.get(code, code)) for code in codes]


async def build_decision_response(
    session: AsyncSession, decision: Decision, *, case_id: str | None = None
) -> DecisionResponse:
    from app.modules.strategies.models import Strategy, StrategyVersion

    trace = await session.scalar(
        select(DecisionTrace).where(DecisionTrace.decision_pk == decision.id)
    )
    strategy_version = await session.get(StrategyVersion, decision.strategy_version_id)
    strategy = (
        await session.get(Strategy, strategy_version.strategy_id) if strategy_version else None
    )
    if case_id is None:
        case = await session.scalar(
            select(ManualReviewCase).where(ManualReviewCase.decision_pk == decision.id)
        )
        case_id = case.case_id if case else None

    codes = [item["code"] for item in decision.reason_codes_json]
    return DecisionResponse(
        decision_id=decision.decision_id,
        application_id=decision.external_application_id,
        decision=decision.decision,
        risk_grade=decision.risk_grade,
        score=float(decision.score) if decision.score is not None else None,
        approved_limit=(
            float(decision.approved_limit) if decision.approved_limit is not None else None
        ),
        approved_tenor_months=decision.approved_tenor_months,
        pricing_rate=float(decision.pricing_rate) if decision.pricing_rate is not None else None,
        reason_codes=await resolve_reason_messages(session, codes),
        strategy_version=(
            f"{strategy.strategy_code}_V{strategy_version.version}"
            if strategy and strategy_version
            else str(decision.strategy_version_id)
        ),
        trace_id=trace.trace_id if trace else "",
        manual_review_case_id=case_id,
        execution_mode=decision.execution_mode,
        execution_time_ms=trace.latency_ms if trace else 0,
        correlation_id=get_correlation_id(),
        created_at=decision.created_at.isoformat() if decision.created_at else None,
    )


async def build_trace_response(session: AsyncSession, decision: Decision) -> TraceResponse | None:
    from app.modules.strategies.models import Strategy, StrategyVersion

    trace = await session.scalar(
        select(DecisionTrace).where(DecisionTrace.decision_pk == decision.id)
    )
    if trace is None:
        return None
    strategy_version = await session.get(StrategyVersion, decision.strategy_version_id)
    strategy = (
        await session.get(Strategy, strategy_version.strategy_id) if strategy_version else None
    )
    return TraceResponse(
        trace_id=trace.trace_id,
        decision_id=decision.decision_id,
        application_id=decision.external_application_id,
        execution_mode=trace.execution_mode,
        strategy=TraceStrategyRef(
            strategy_id=str(strategy.id) if strategy else None,
            version_id=str(strategy_version.id) if strategy_version else None,
            strategy_code=strategy.strategy_code if strategy else "UNKNOWN",
            version=strategy_version.version if strategy_version else 0,
            execution="GRAPH",
        ),
        input_snapshot=trace.input_snapshot,
        feature_values=trace.feature_values,
        outputs=sanitize_snapshot(
            {
                key: value
                for key, value in trace.feature_values.items()
                if key.startswith("outputs.")
            }
        ),
        steps=trace.step_results,
        score_result=trace.score_results,
        final_decision=trace.final_output,
        errors=trace.errors,
        metadata={
            "latency_ms": trace.latency_ms,
            "request_id": trace.request_id,
            "correlation_id": trace.correlation_id,
        },
        created_at=trace.created_at.isoformat() if trace.created_at else "",
    )

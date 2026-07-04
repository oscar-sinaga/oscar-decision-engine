"""Manual review service: assignment, analyst decision, override control (docs/13)."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.decisions.models import Application, Decision
from app.modules.manual_review.models import ManualReviewCase
from app.modules.manual_review.schemas import ANALYST_DECISIONS, AnalystDecisionRequest
from app.modules.reason_codes.models import ReasonCode
from app.shared.domain.enums import ApplicationStatus, CaseStatus, DecisionType
from app.shared.domain.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.shared.logging import get_logger

logger = get_logger("oscar.manual_review")

OPEN_STATUSES = {
    CaseStatus.NEW,
    CaseStatus.ASSIGNED,
    CaseStatus.IN_REVIEW,
    CaseStatus.PENDING_DOCUMENTS,
    CaseStatus.ESCALATED,
}


async def get_case(session: AsyncSession, case_id: str) -> ManualReviewCase:
    case = await session.scalar(select(ManualReviewCase).where(ManualReviewCase.case_id == case_id))
    if case is None:
        raise NotFoundError(f"Manual review case '{case_id}' not found")
    return case


def _ensure_open(case: ManualReviewCase) -> None:
    if case.status not in OPEN_STATUSES:
        raise ConflictError(f"Case '{case.case_id}' is {case.status} and cannot be modified")


async def assign_case(
    session: AsyncSession, case: ManualReviewCase, assignee: User, actor: User
) -> ManualReviewCase:
    _ensure_open(case)
    before = {"status": case.status, "assigned_to": str(case.assigned_to or "")}
    case.assigned_to = assignee.id
    if case.status == CaseStatus.NEW:
        case.status = CaseStatus.ASSIGNED
    record_audit_event(
        session,
        event_type="MANUAL_REVIEW_CASE_ASSIGNED",
        entity_type="MANUAL_REVIEW_CASE",
        entity_id=case.case_id,
        action="ASSIGN_CASE",
        actor=actor,
        before_value=before,
        after_value={"status": case.status, "assigned_to": assignee.username},
    )
    await session.commit()
    return case


async def _validate_reason_code(session: AsyncSession, code: str) -> None:
    exists = await session.scalar(select(ReasonCode).where(ReasonCode.code == code))
    if exists is None:
        raise ValidationFailedError(
            "Unknown override reason code",
            details=[{"field": "override_reason_code", "issue": f"unknown: {code}"}],
        )


async def decide_case(
    session: AsyncSession,
    case: ManualReviewCase,
    request: AnalystDecisionRequest,
    actor: User,
) -> ManualReviewCase:
    _ensure_open(case)

    if request.analyst_decision not in ANALYST_DECISIONS:
        raise ValidationFailedError(
            "Unsupported analyst decision",
            details=[
                {
                    "field": "analyst_decision",
                    "issue": f"must be one of {sorted(d.value for d in ANALYST_DECISIONS)}",
                }
            ],
        )

    is_override = request.analyst_decision != case.system_decision
    if is_override and not request.override_reason.strip():
        raise ValidationFailedError(
            "Override requires a reason",
            details=[{"field": "override_reason", "issue": "required when decision differs"}],
        )

    # Contradicting a fraud-investigation routing is a high-risk override and
    # needs the dedicated permission (docs/13 §6, docs/14 §7) — see ADR-008.
    approve_like = request.analyst_decision in (
        DecisionType.APPROVE,
        DecisionType.APPROVE_WITH_CONDITION,
    )
    if (
        case.system_decision == DecisionType.FRAUD_INVESTIGATION
        and approve_like
        and Permissions.MANUAL_REVIEW_OVERRIDE not in actor.permission_codes
    ):
        raise AuthorizationError(
            "Approving a fraud-investigation case requires manual_review.override"
        )

    if request.analyst_decision == DecisionType.REJECT and not request.override_reason_code:
        raise ValidationFailedError(
            "Reject requires a reason code",
            details=[{"field": "override_reason_code", "issue": "required for REJECT"}],
        )
    if request.override_reason_code:
        await _validate_reason_code(session, request.override_reason_code)

    before = {
        "status": case.status,
        "analyst_decision": case.analyst_decision,
        "system_decision": case.system_decision,
    }
    now = datetime.now(UTC)
    case.analyst_decision = request.analyst_decision
    case.analyst_decided_by = actor.id
    case.analyst_decided_at = now
    case.approved_limit = (
        Decimal(str(request.approved_limit)) if request.approved_limit is not None else None
    )
    case.approved_tenor_months = request.approved_tenor_months
    case.override_reason_code = request.override_reason_code
    case.override_reason = request.override_reason or None
    if request.notes:
        case.notes = f"{case.notes}\n{request.notes}".strip()
    case.status = (
        CaseStatus.REJECTED_BY_ANALYST
        if request.analyst_decision == DecisionType.REJECT
        else CaseStatus.APPROVED_BY_ANALYST
    )
    case.closed_at = now

    application = await session.get(Application, case.application_pk)
    if application is not None:
        application.status = ApplicationStatus.DECIDED

    after = {
        "status": case.status,
        "analyst_decision": request.analyst_decision,
        "approved_limit": request.approved_limit,
        "approved_tenor_months": request.approved_tenor_months,
        "override_reason_code": request.override_reason_code,
    }
    record_audit_event(
        session,
        event_type="MANUAL_REVIEW_DECIDED",
        entity_type="MANUAL_REVIEW_CASE",
        entity_id=case.case_id,
        action="ANALYST_DECISION",
        actor=actor,
        reason=request.override_reason or None,
        before_value=before,
        after_value=after,
    )
    if is_override:
        record_audit_event(
            session,
            event_type="MANUAL_REVIEW_OVERRIDDEN",
            entity_type="MANUAL_REVIEW_CASE",
            entity_id=case.case_id,
            action="OVERRIDE_SYSTEM_DECISION",
            actor=actor,
            reason=request.override_reason,
            before_value={"system_decision": case.system_decision},
            after_value={"analyst_decision": request.analyst_decision},
            metadata={"override_reason_code": request.override_reason_code},
        )
    await session.commit()
    logger.info(
        "manual_review.decided",
        extra={
            "case_id": case.case_id,
            "analyst_decision": request.analyst_decision.value,
            "is_override": is_override,
        },
    )
    return case


async def escalate_case(
    session: AsyncSession, case: ManualReviewCase, reason: str, actor: User
) -> ManualReviewCase:
    _ensure_open(case)
    before = {"status": case.status}
    case.status = CaseStatus.ESCALATED
    record_audit_event(
        session,
        event_type="MANUAL_REVIEW_ESCALATED",
        entity_type="MANUAL_REVIEW_CASE",
        entity_id=case.case_id,
        action="ESCALATE_CASE",
        actor=actor,
        reason=reason,
        before_value=before,
        after_value={"status": case.status},
    )
    await session.commit()
    return case


async def request_documents(
    session: AsyncSession, case: ManualReviewCase, message: str, actor: User
) -> ManualReviewCase:
    _ensure_open(case)
    before = {"status": case.status}
    case.status = CaseStatus.PENDING_DOCUMENTS
    case.notes = f"{case.notes}\n[DOCUMENT REQUEST] {message}".strip()
    record_audit_event(
        session,
        event_type="MANUAL_REVIEW_DOCUMENTS_REQUESTED",
        entity_type="MANUAL_REVIEW_CASE",
        entity_id=case.case_id,
        action="REQUEST_DOCUMENTS",
        actor=actor,
        reason=message,
        before_value=before,
        after_value={"status": case.status},
    )
    await session.commit()
    return case


async def load_case_context(
    session: AsyncSession, case: ManualReviewCase
) -> tuple[Decision | None, Application | None]:
    decision = await session.get(Decision, case.decision_pk)
    application = await session.get(Application, case.application_pk)
    return decision, application

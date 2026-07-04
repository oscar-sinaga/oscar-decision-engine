"""Manual review API routes (docs/07 §7)."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.decisions.models import Application, Decision, DecisionTrace
from app.modules.manual_review import service
from app.modules.manual_review.models import ManualReviewCase
from app.modules.manual_review.schemas import (
    AnalystDecisionRequest,
    AssignRequest,
    CaseDetailResponse,
    CaseListItem,
    CaseListResponse,
    EscalateRequest,
    RequestDocumentsRequest,
)
from app.shared.database import get_session
from app.shared.domain.enums import CasePriority, CaseStatus, ProductType
from app.shared.domain.errors import NotFoundError
from app.shared.utils.masking import redact

router = APIRouter(prefix="/manual-review", tags=["manual-review"])

Session = Annotated[AsyncSession, Depends(get_session)]


async def _username(session: AsyncSession, user_id: Any) -> str | None:
    if user_id is None:
        return None
    user = await session.get(User, user_id)
    return user.username if user else None


def _summary(snapshot: dict[str, Any], section: str) -> dict[str, Any]:
    data = snapshot.get(section, {})
    return redact(data) if isinstance(data, dict) else {}


async def _list_item(
    session: AsyncSession, case: ManualReviewCase, decision: Decision, application: Application
) -> CaseListItem:
    return CaseListItem(
        case_id=case.case_id,
        application_id=decision.external_application_id,
        product_type=application.product_type,
        channel=application.channel,
        system_decision=case.system_decision,
        system_reason_codes=[item["code"] for item in decision.reason_codes_json],
        status=case.status,
        priority=case.priority,
        assigned_to=await _username(session, case.assigned_to),
        created_at=case.created_at,
    )


@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    session: Session,
    status: Annotated[CaseStatus | None, Query()] = None,
    priority: Annotated[CasePriority | None, Query()] = None,
    assigned_to: Annotated[str | None, Query()] = None,
    product_type: Annotated[ProductType | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    user: User = require_permission(Permissions.MANUAL_REVIEW_VIEW),
) -> CaseListResponse:
    from sqlalchemy import func

    query = (
        select(ManualReviewCase, Decision, Application)
        .join(Decision, ManualReviewCase.decision_pk == Decision.id)
        .join(Application, ManualReviewCase.application_pk == Application.id)
        .order_by(ManualReviewCase.created_at.desc())
    )
    if status is not None:
        query = query.where(ManualReviewCase.status == status)
    if priority is not None:
        query = query.where(ManualReviewCase.priority == priority)
    if assigned_to is not None:
        assignee = await session.scalar(select(User).where(User.username == assigned_to))
        query = query.where(ManualReviewCase.assigned_to == (assignee.id if assignee else None))
    if product_type is not None:
        query = query.where(Application.product_type == product_type)
    if date_from is not None:
        query = query.where(ManualReviewCase.created_at >= date_from)
    if date_to is not None:
        query = query.where(ManualReviewCase.created_at <= date_to)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (await session.execute(query.offset((page - 1) * page_size).limit(page_size))).all()
    items = [
        await _list_item(session, case, decision, application)
        for case, decision, application in rows
    ]
    return CaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    case_id: str,
    session: Session,
    user: User = require_permission(Permissions.MANUAL_REVIEW_VIEW),
) -> CaseDetailResponse:
    case = await service.get_case(session, case_id)
    decision, application = await service.load_case_context(session, case)
    if decision is None or application is None:
        raise NotFoundError(f"Case '{case_id}' context not found")
    trace = await session.scalar(
        select(DecisionTrace).where(DecisionTrace.decision_pk == decision.id)
    )
    base = await _list_item(session, case, decision, application)
    snapshot = application.payload_snapshot or {}
    return CaseDetailResponse(
        **base.model_dump(),
        decision_id=decision.decision_id,
        trace_id=trace.trace_id if trace else None,
        risk_grade=decision.risk_grade,
        score=float(decision.score) if decision.score is not None else None,
        applicant_summary=_summary(snapshot, "applicant"),
        loan_summary=_summary(snapshot, "loan"),
        vehicle_summary=_summary(snapshot, "vehicle"),
        analyst_decision=case.analyst_decision,
        analyst_decided_by=await _username(session, case.analyst_decided_by),
        analyst_decided_at=case.analyst_decided_at,
        approved_limit=float(case.approved_limit) if case.approved_limit is not None else None,
        approved_tenor_months=case.approved_tenor_months,
        override_reason_code=case.override_reason_code,
        override_reason=case.override_reason,
        notes=case.notes,
        closed_at=case.closed_at,
    )


@router.post("/cases/{case_id}/assign", response_model=CaseDetailResponse)
async def assign_case(
    case_id: str,
    body: AssignRequest,
    session: Session,
    user: User = require_permission(Permissions.MANUAL_REVIEW_DECIDE),
) -> CaseDetailResponse:
    case = await service.get_case(session, case_id)
    assignee = user
    if body.assignee_username:
        found = await session.scalar(select(User).where(User.username == body.assignee_username))
        if found is None:
            raise NotFoundError(f"User '{body.assignee_username}' not found")
        assignee = found
    await service.assign_case(session, case, assignee, user)
    return await get_case_detail(case_id, session, user)


@router.post("/cases/{case_id}/decision", response_model=CaseDetailResponse)
async def decide_case(
    case_id: str,
    body: AnalystDecisionRequest,
    session: Session,
    user: User = require_permission(Permissions.MANUAL_REVIEW_DECIDE),
) -> CaseDetailResponse:
    case = await service.get_case(session, case_id)
    await service.decide_case(session, case, body, user)
    return await get_case_detail(case_id, session, user)


@router.post("/cases/{case_id}/escalate", response_model=CaseDetailResponse)
async def escalate_case(
    case_id: str,
    body: EscalateRequest,
    session: Session,
    user: User = require_permission(Permissions.MANUAL_REVIEW_DECIDE),
) -> CaseDetailResponse:
    case = await service.get_case(session, case_id)
    await service.escalate_case(session, case, body.reason, user)
    return await get_case_detail(case_id, session, user)


@router.post("/cases/{case_id}/request-documents", response_model=CaseDetailResponse)
async def request_documents(
    case_id: str,
    body: RequestDocumentsRequest,
    session: Session,
    user: User = require_permission(Permissions.MANUAL_REVIEW_DECIDE),
) -> CaseDetailResponse:
    case = await service.get_case(session, case_id)
    await service.request_documents(session, case, body.message, user)
    return await get_case_detail(case_id, session, user)

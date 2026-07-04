"""Runtime Decision API and decision history routes (docs/07 §2–3, docs/02 §6.6)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.decisions.models import Application, Decision
from app.modules.decisions.schemas import DecisionRequest, DecisionResponse, TraceResponse
from app.modules.decisions.service import (
    build_decision_response,
    build_trace_response,
    execute_decision,
)
from app.shared.database import get_session
from app.shared.domain.enums import DecisionType, ProductType
from app.shared.domain.errors import NotFoundError

router = APIRouter(prefix="/decisions", tags=["decisions"])


class DecisionHistoryItem(BaseModel):
    decision_id: str
    application_id: str
    product_type: ProductType
    channel: str
    decision: DecisionType
    risk_grade: str | None
    score: float | None
    approved_limit: float | None
    strategy_version_id: str
    reason_codes: list[str]
    created_at: datetime


class DecisionHistoryResponse(BaseModel):
    items: list[DecisionHistoryItem]
    total: int
    page: int
    page_size: int


@router.post("", response_model=DecisionResponse, status_code=201)
async def submit_decision(
    body: DecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    user: User = require_permission(Permissions.DECISION_EXECUTE),
) -> DecisionResponse:
    return await execute_decision(session, body, actor=user, idempotency_key=idempotency_key)


@router.get("", response_model=DecisionHistoryResponse)
async def list_decisions(
    session: Annotated[AsyncSession, Depends(get_session)],
    application_id: Annotated[str | None, Query()] = None,
    decision: Annotated[DecisionType | None, Query()] = None,
    product_type: Annotated[ProductType | None, Query()] = None,
    channel: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    user: User = require_permission(Permissions.DECISION_VIEW),
) -> DecisionHistoryResponse:
    query = (
        select(Decision, Application)
        .join(Application, Decision.application_pk == Application.id)
        .order_by(Decision.created_at.desc())
    )
    if application_id is not None:
        query = query.where(Decision.external_application_id == application_id)
    if decision is not None:
        query = query.where(Decision.decision == decision)
    if product_type is not None:
        query = query.where(Application.product_type == product_type)
    if channel is not None:
        query = query.where(Application.channel == channel)
    if date_from is not None:
        query = query.where(Decision.created_at >= date_from)
    if date_to is not None:
        query = query.where(Decision.created_at <= date_to)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (await session.execute(query.offset((page - 1) * page_size).limit(page_size))).all()
    items = [
        DecisionHistoryItem(
            decision_id=dec.decision_id,
            application_id=dec.external_application_id,
            product_type=app.product_type,
            channel=app.channel,
            decision=dec.decision,
            risk_grade=dec.risk_grade,
            score=float(dec.score) if dec.score is not None else None,
            approved_limit=float(dec.approved_limit) if dec.approved_limit is not None else None,
            strategy_version_id=str(dec.strategy_version_id),
            reason_codes=[item["code"] for item in dec.reason_codes_json],
            created_at=dec.created_at,
        )
        for dec, app in rows
    ]
    return DecisionHistoryResponse(items=items, total=total, page=page, page_size=page_size)


async def _get_decision(session: AsyncSession, decision_id: str) -> Decision:
    decision = await session.scalar(select(Decision).where(Decision.decision_id == decision_id))
    if decision is None:
        raise NotFoundError(f"Decision '{decision_id}' not found")
    return decision


@router.get("/{decision_id}", response_model=DecisionResponse)
async def get_decision(
    decision_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = require_permission(Permissions.DECISION_VIEW),
) -> DecisionResponse:
    decision = await _get_decision(session, decision_id)
    return await build_decision_response(session, decision)


@router.get("/{decision_id}/trace", response_model=TraceResponse)
async def get_decision_trace(
    decision_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = require_permission(Permissions.DECISION_TRACE_VIEW),
) -> TraceResponse:
    decision = await _get_decision(session, decision_id)
    trace = await build_trace_response(session, decision)
    if trace is None:
        raise NotFoundError(f"Trace for decision '{decision_id}' not found")
    # Trace content is sensitive evidence; access itself is audited (docs/18 §7).
    record_audit_event(
        session,
        event_type="DECISION_TRACE_VIEWED",
        entity_type="DECISION_TRACE",
        entity_id=trace.trace_id,
        action="VIEW_TRACE",
        actor=user,
        metadata={"decision_id": decision_id},
    )
    await session.commit()
    return trace

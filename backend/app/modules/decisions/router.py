"""Runtime Decision API routes (docs/07 §2–3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.decisions.models import Decision
from app.modules.decisions.schemas import DecisionRequest, DecisionResponse, TraceResponse
from app.modules.decisions.service import (
    build_decision_response,
    build_trace_response,
    execute_decision,
)
from app.shared.database import get_session
from app.shared.domain.errors import NotFoundError

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.post("", response_model=DecisionResponse, status_code=201)
async def submit_decision(
    body: DecisionRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    user: User = require_permission(Permissions.DECISION_EXECUTE),
) -> DecisionResponse:
    return await execute_decision(session, body, actor=user, idempotency_key=idempotency_key)


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
    return trace

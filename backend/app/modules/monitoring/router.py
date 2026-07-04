"""Operational and risk monitoring metrics (docs/07 §9, docs/18 §10).

Aggregates are computed over persisted decisions/traces/cases. Metric labels
never include PII or high-cardinality customer identifiers.
"""

from collections import Counter
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.decisions.models import Application, Decision, DecisionTrace
from app.modules.manual_review.models import ManualReviewCase
from app.modules.manual_review.service import OPEN_STATUSES
from app.shared.database import get_session
from app.shared.domain.enums import DecisionType, ProductType

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

APPROVE_DECISIONS = {DecisionType.APPROVE, DecisionType.APPROVE_WITH_CONDITION}
REVIEW_DECISIONS = {DecisionType.MANUAL_REVIEW, DecisionType.FRAUD_INVESTIGATION}


class ReasonCodeCount(BaseModel):
    code: str
    count: int


class DecisionSummaryResponse(BaseModel):
    total_applications: int
    approval_rate: float
    reject_rate: float
    manual_review_rate: float
    error_rate: float
    decision_counts: dict[str, int]
    top_reason_codes: list[ReasonCodeCount]
    api_latency_p95_ms: float | None
    manual_review_queue_size: int


def _filtered(
    query: Select[Any],
    product_type: ProductType | None,
    channel: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select[Any]:
    query = query.join(Application, Decision.application_pk == Application.id)
    if product_type is not None:
        query = query.where(Application.product_type == product_type)
    if channel is not None:
        query = query.where(Application.channel == channel)
    if date_from is not None:
        query = query.where(Decision.created_at >= date_from)
    if date_to is not None:
        query = query.where(Decision.created_at <= date_to)
    return query


@router.get("/decision-summary", response_model=DecisionSummaryResponse)
async def decision_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    product_type: Annotated[ProductType | None, Query()] = None,
    channel: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    user: User = require_permission(Permissions.MONITORING_VIEW),
) -> DecisionSummaryResponse:
    decision_rows = (
        await session.execute(
            _filtered(
                select(Decision.decision, func.count())
                .select_from(Decision)
                .group_by(Decision.decision),
                product_type,
                channel,
                date_from,
                date_to,
            )
        )
    ).all()
    decision_counts = {str(decision): count for decision, count in decision_rows}
    total = sum(decision_counts.values())

    def rate(decisions: set[DecisionType]) -> float:
        if total == 0:
            return 0.0
        matched: int = sum(decision_counts.get(d.value, 0) for d in decisions)
        return round(matched / total, 4)

    reason_rows = (
        await session.scalars(
            _filtered(
                select(Decision.reason_codes_json).select_from(Decision),
                product_type,
                channel,
                date_from,
                date_to,
            )
        )
    ).all()
    reason_counter: Counter[str] = Counter()
    for codes in reason_rows:
        for item in codes:
            reason_counter[item["code"]] += 1

    latency_p95 = await session.scalar(
        _filtered(
            select(func.percentile_cont(0.95).within_group(DecisionTrace.latency_ms))
            .select_from(Decision)
            .join(DecisionTrace, DecisionTrace.decision_pk == Decision.id),
            product_type,
            channel,
            date_from,
            date_to,
        )
    )

    queue_size = (
        await session.scalar(
            select(func.count())
            .select_from(ManualReviewCase)
            .where(ManualReviewCase.status.in_(OPEN_STATUSES))
        )
        or 0
    )

    return DecisionSummaryResponse(
        total_applications=total,
        approval_rate=rate(APPROVE_DECISIONS),
        reject_rate=rate({DecisionType.REJECT}),
        manual_review_rate=rate(REVIEW_DECISIONS),
        error_rate=rate({DecisionType.ERROR}),
        decision_counts=decision_counts,
        top_reason_codes=[
            ReasonCodeCount(code=code, count=count)
            for code, count in reason_counter.most_common(10)
        ],
        api_latency_p95_ms=float(latency_p95) if latency_p95 is not None else None,
        manual_review_queue_size=queue_size,
    )

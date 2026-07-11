"""Strategy management API routes (docs/07 §6)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.strategies import service
from app.modules.strategies.models import Strategy, StrategyVersion
from app.modules.strategies.schemas import (
    StrategyCreateRequest,
    StrategyDetailResponse,
    StrategyResponse,
    StrategyVersionCreateRequest,
    StrategyVersionResponse,
)
from app.shared.database import get_session
from app.shared.domain.enums import ConfigStatus

router = APIRouter(prefix="/strategies", tags=["strategies"])

Session = Annotated[AsyncSession, Depends(get_session)]


class LifecycleRequest(BaseModel):
    reason: str = ""


class SubmitApprovalRequest(BaseModel):
    # Simulation evidence of this exact strategy version (full maker-checker).
    simulation_id: str | None = None


def _version_response(version: StrategyVersion) -> StrategyVersionResponse:
    return StrategyVersionResponse(
        id=str(version.id),
        version=version.version,
        status=version.status,
        version_note=version.version_note,
        graph=service.graph_response(version),
        steps=service.derive_linear_steps(version),
        created_at=version.created_at,
        activated_at=version.activated_at,
        effective_from=version.effective_from,
        effective_to=version.effective_to,
    )


def _strategy_response(strategy: Strategy) -> StrategyResponse:
    active = next((v for v in strategy.versions if v.status == ConfigStatus.ACTIVE), None)
    latest = max(strategy.versions, key=lambda v: v.version) if strategy.versions else None
    return StrategyResponse(
        id=str(strategy.id),
        strategy_code=strategy.strategy_code,
        name=strategy.name,
        product_type=strategy.product_type,
        segment=strategy.segment,
        owner_team=strategy.owner_team,
        active_version=active.version if active else None,
        latest_version=latest.version if latest else None,
        latest_status=latest.status if latest else None,
    )


def _strategy_detail(strategy: Strategy) -> StrategyDetailResponse:
    base = _strategy_response(strategy)
    return StrategyDetailResponse(
        **base.model_dump(),
        versions=[_version_response(v) for v in sorted(strategy.versions, key=lambda v: v.version)],
    )


@router.post("", response_model=StrategyDetailResponse, status_code=201)
async def create_strategy(
    body: StrategyCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_CREATE),
) -> StrategyDetailResponse:
    strategy = await service.create_strategy(session, body, user)
    return _strategy_detail(strategy)


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_VIEW),
) -> list[StrategyResponse]:
    strategies = (
        await session.scalars(
            select(Strategy)
            .options(
                selectinload(Strategy.versions).selectinload(StrategyVersion.nodes),
                selectinload(Strategy.versions).selectinload(StrategyVersion.edges),
            )
            .order_by(Strategy.strategy_code)
        )
    ).all()
    return [_strategy_response(s) for s in strategies]


@router.get("/{strategy_id}", response_model=StrategyDetailResponse)
async def get_strategy(
    strategy_id: uuid.UUID,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_VIEW),
) -> StrategyDetailResponse:
    strategy = await service.get_strategy(session, strategy_id)
    return _strategy_detail(strategy)


@router.post("/{strategy_id}/versions", response_model=StrategyVersionResponse, status_code=201)
async def create_strategy_version(
    strategy_id: uuid.UUID,
    body: StrategyVersionCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_CREATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = await service.create_strategy_version(session, strategy, body, user)
    return _version_response(version)


@router.put("/{strategy_id}/versions/{version_id}", response_model=StrategyVersionResponse)
async def update_strategy_version(
    strategy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: StrategyVersionCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_CREATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = service.get_version(strategy, version_id)
    return _version_response(
        await service.update_strategy_version(session, strategy, version, body, user)
    )


@router.post(
    "/{strategy_id}/versions/{version_id}/submit-approval",
    response_model=StrategyVersionResponse,
)
async def submit_strategy_version(
    strategy_id: uuid.UUID,
    version_id: uuid.UUID,
    session: Session,
    body: SubmitApprovalRequest | None = None,
    user: User = require_permission(Permissions.STRATEGY_CREATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = service.get_version(strategy, version_id)
    simulation_id = body.simulation_id if body else None
    return _version_response(
        await service.submit_strategy_version(session, strategy, version, user, simulation_id)
    )


@router.post(
    "/{strategy_id}/versions/{version_id}/activate", response_model=StrategyVersionResponse
)
async def activate_strategy_version(
    strategy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_ACTIVATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = service.get_version(strategy, version_id)
    return _version_response(
        await service.activate_strategy_version(session, strategy, version, user, body.reason)
    )


@router.post("/{strategy_id}/versions/{version_id}/reject", response_model=StrategyVersionResponse)
async def reject_strategy_version(
    strategy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_ACTIVATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = service.get_version(strategy, version_id)
    return _version_response(
        await service.reject_strategy_version(session, strategy, version, user, body.reason)
    )


@router.post(
    "/{strategy_id}/versions/{version_id}/rollback", response_model=StrategyVersionResponse
)
async def rollback_strategy_version(
    strategy_id: uuid.UUID,
    version_id: uuid.UUID,
    body: LifecycleRequest,
    session: Session,
    user: User = require_permission(Permissions.STRATEGY_ACTIVATE),
) -> StrategyVersionResponse:
    strategy = await service.get_strategy(session, strategy_id)
    version = service.get_version(strategy, version_id)
    return _version_response(
        await service.rollback_to_version(session, strategy, version, user, body.reason)
    )

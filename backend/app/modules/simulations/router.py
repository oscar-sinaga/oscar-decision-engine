"""Simulation API routes (docs/07 §4)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.simulations.models import Simulation
from app.modules.simulations.schemas import (
    SimulationDetailResponse,
    SimulationListItem,
    SingleSimulationRequest,
    SingleSimulationResponse,
)
from app.modules.simulations.service import run_single_simulation
from app.shared.database import get_session
from app.shared.domain.errors import NotFoundError

router = APIRouter(prefix="/simulations", tags=["simulations"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post("/single", response_model=SingleSimulationResponse, status_code=201)
async def simulate_single(
    body: SingleSimulationRequest,
    session: Session,
    user: User = require_permission(Permissions.SIMULATION_RUN),
) -> SingleSimulationResponse:
    return await run_single_simulation(session, body, user)


@router.get("", response_model=list[SimulationListItem])
async def list_simulations(
    session: Session,
    user: User = require_permission(Permissions.SIMULATION_VIEW),
) -> list[SimulationListItem]:
    simulations = (
        await session.scalars(select(Simulation).order_by(Simulation.created_at.desc()))
    ).all()
    return [
        SimulationListItem(
            simulation_id=s.simulation_id,
            name=s.name,
            type=s.type,
            status=s.status,
            strategy_version_id=str(s.strategy_version_id),
            compare_strategy_version_id=(
                str(s.compare_strategy_version_id) if s.compare_strategy_version_id else None
            ),
            created_at=s.created_at,
        )
        for s in simulations
    ]


@router.get("/{simulation_id}", response_model=SimulationDetailResponse)
async def get_simulation(
    simulation_id: str,
    session: Session,
    user: User = require_permission(Permissions.SIMULATION_VIEW),
) -> SimulationDetailResponse:
    simulation = await session.scalar(
        select(Simulation)
        .where(Simulation.simulation_id == simulation_id)
        .options(selectinload(Simulation.results))
    )
    if simulation is None:
        raise NotFoundError(f"Simulation '{simulation_id}' not found")
    result = simulation.results[0] if simulation.results else None
    return SimulationDetailResponse(
        simulation_id=simulation.simulation_id,
        name=simulation.name,
        type=simulation.type,
        status=simulation.status,
        strategy_version_id=str(simulation.strategy_version_id),
        compare_strategy_version_id=(
            str(simulation.compare_strategy_version_id)
            if simulation.compare_strategy_version_id
            else None
        ),
        created_at=simulation.created_at,
        result=result.result_json if result else {},
        trace=result.trace_json if result else {},
        differences=result.difference_json if result else None,
    )

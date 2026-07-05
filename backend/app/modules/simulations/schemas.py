"""Simulation API schemas (docs/07 §4, docs/12)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.decisions.schemas import DecisionRequest
from app.shared.domain.enums import SimulationStatus, SimulationType


class SingleSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_name: str = Field(default="", max_length=200)
    application_payload: DecisionRequest
    # Target strategy version (draft or active). Defaults to the active
    # strategy for the payload's product/segment.
    strategy_version_id: str | None = None
    compare_with_active: bool = False


class SimulationOutcome(BaseModel):
    strategy_version: str
    decision: str
    risk_grade: str | None
    score: float | None
    approved_limit: float | None
    approved_tenor_months: int | None
    pricing_rate: float | None
    reason_codes: list[str]
    validation_failures: list[dict[str, Any]]


class SimulationDifference(BaseModel):
    field: str
    active: Any
    draft: Any


class SingleSimulationResponse(BaseModel):
    simulation_id: str
    mode: str = "SIMULATION"
    draft_result: SimulationOutcome
    active_result: SimulationOutcome | None = None
    differences: list[SimulationDifference] = []


class BatchSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    simulation_name: str = Field(default="", max_length=200)
    # Candidate (target) strategy version to evaluate the population against.
    strategy_version_id: str
    application_payloads: list[DecisionRequest] = Field(min_length=1, max_length=5000)
    compare_with_active: bool = True


class StrategyAggregate(BaseModel):
    strategy_version: str
    decision_counts: dict[str, int]
    approval_rate: float
    reject_rate: float
    manual_review_rate: float
    error_rate: float
    reason_code_distribution: dict[str, int]
    risk_grade_distribution: dict[str, int]


class DecisionShift(BaseModel):
    from_decision: str
    to_decision: str
    count: int


class SegmentImpact(BaseModel):
    segment: str
    total: int
    target_decision_counts: dict[str, int]
    active_decision_counts: dict[str, int] | None


class BatchSimulationResponse(BaseModel):
    simulation_id: str
    mode: str = "SIMULATION"
    total_records: int
    target: StrategyAggregate
    active: StrategyAggregate | None = None
    decision_shifts: list[DecisionShift] = []
    segment_impact: list[SegmentImpact] = []


class SimulationListItem(BaseModel):
    simulation_id: str
    name: str
    type: SimulationType
    status: SimulationStatus
    strategy_version_id: str
    compare_strategy_version_id: str | None
    created_at: datetime


class SimulationDetailResponse(SimulationListItem):
    result: dict[str, Any]
    trace: dict[str, Any]
    differences: list[dict[str, Any]] | None

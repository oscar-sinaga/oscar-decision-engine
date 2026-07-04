"""Strategy management API schemas (docs/07 §6)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.domain.enums import ConfigStatus, ProductType, StepOnError, StepType


class StrategyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_code: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    product_type: ProductType
    segment: str = Field(default="DEFAULT", max_length=100)
    owner_team: str = "RISK"


class StepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    type: StepType
    name: str = ""
    reference_code: str | None = None
    on_error: StepOnError = StepOnError.FAIL
    config: dict[str, Any] = Field(default_factory=dict)


class StrategyVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_note: str = ""
    steps: list[StepRequest] = Field(min_length=1)

    @field_validator("steps")
    @classmethod
    def _orders_unique(cls, steps: list[StepRequest]) -> list[StepRequest]:
        orders = [step.order for step in steps]
        if len(set(orders)) != len(orders):
            raise ValueError("step orders must be unique")
        return steps


class StepResponse(BaseModel):
    order: int
    type: StepType
    name: str
    reference_code: str | None
    on_error: StepOnError
    config: dict[str, Any]


class StrategyVersionResponse(BaseModel):
    id: str
    version: int
    status: ConfigStatus
    version_note: str
    steps: list[StepResponse]
    created_at: datetime | None
    activated_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None


class StrategyResponse(BaseModel):
    id: str
    strategy_code: str
    name: str
    product_type: ProductType
    segment: str
    owner_team: str
    active_version: int | None
    latest_version: int | None
    latest_status: ConfigStatus | None


class StrategyDetailResponse(StrategyResponse):
    versions: list[StrategyVersionResponse]

"""Strategy management API schemas, including Phase 3 graph compatibility."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.shared.domain.enums import (
    ConfigStatus,
    NodeType,
    ProductType,
    StepOnError,
    StepType,
)


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


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = 0
    y: int = 0


class NodeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_key: str | None = Field(default=None, min_length=1, max_length=50)
    node_type: NodeType
    name: str = Field(default="", max_length=200)
    reference_code: str | None = Field(default=None, max_length=100)
    on_error: StepOnError = StepOnError.FAIL
    config: dict[str, Any] = Field(default_factory=dict)
    position: Position = Field(default_factory=Position)


class EdgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_node_key: str = Field(alias="from", min_length=1, max_length=50)
    to_node_key: str = Field(alias="to", min_length=1, max_length=50)
    label: str | None = Field(default=None, max_length=10)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class GraphRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[NodeRequest] = Field(min_length=1)
    edges: list[EdgeRequest] = Field(default_factory=list)


class StrategyVersionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_note: str = ""
    steps: list[StepRequest] | None = None
    graph: GraphRequest | None = None

    @model_validator(mode="after")
    def exactly_one_shape(self) -> "StrategyVersionCreateRequest":
        if (self.steps is None) == (self.graph is None):
            raise ValueError("provide exactly one of steps or graph")
        if self.steps is not None:
            if not self.steps:
                raise ValueError("steps must contain at least one item")
            orders = [step.order for step in self.steps]
            if len(set(orders)) != len(orders):
                raise ValueError("step orders must be unique")
        return self


class StepResponse(BaseModel):
    order: int
    type: StepType
    name: str
    reference_code: str | None
    on_error: StepOnError
    config: dict[str, Any]


class NodeResponse(BaseModel):
    node_key: str
    node_type: NodeType
    name: str
    reference_code: str | None
    on_error: StepOnError
    config: dict[str, Any]
    position: Position


class EdgeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    from_node_key: str = Field(alias="from")
    to_node_key: str = Field(alias="to")
    label: str | None = None


class GraphResponse(BaseModel):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]


class StrategyVersionResponse(BaseModel):
    id: str
    version: int
    status: ConfigStatus
    version_note: str
    graph: GraphResponse
    steps: list[StepResponse] | None = None
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

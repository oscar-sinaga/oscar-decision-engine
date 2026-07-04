"""Runtime Decision API schemas (docs/07 §2–3)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.shared.domain.enums import DecisionType, ExecutionMode, ProductType


class DecisionRequest(BaseModel):
    """Application payload envelope.

    Section contents stay schemaless dictionaries on purpose: which fields are
    required is configurable policy (VALIDATION strategy steps + the feature
    registry), not a hardcoded API schema.
    """

    model_config = ConfigDict(extra="forbid")

    application_id: str = Field(min_length=1, max_length=100)
    product_type: ProductType
    channel: str = Field(default="UNKNOWN", max_length=100)
    segment: str = Field(default="DEFAULT", max_length=100)
    applicant: dict[str, Any] = Field(default_factory=dict)
    loan: dict[str, Any] = Field(default_factory=dict)
    vehicle: dict[str, Any] = Field(default_factory=dict)
    bureau: dict[str, Any] = Field(default_factory=dict)
    fraud: dict[str, Any] = Field(default_factory=dict)
    model_outputs: dict[str, Any] = Field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class ReasonCodeItem(BaseModel):
    code: str
    message: str


class DecisionResponse(BaseModel):
    decision_id: str
    application_id: str
    decision: DecisionType
    risk_grade: str | None = None
    score: float | None = None
    approved_limit: float | None = None
    approved_tenor_months: int | None = None
    pricing_rate: float | None = None
    reason_codes: list[ReasonCodeItem]
    strategy_version: str
    trace_id: str
    manual_review_case_id: str | None = None
    execution_mode: ExecutionMode = ExecutionMode.PRODUCTION
    execution_time_ms: int
    correlation_id: str | None = None
    created_at: str | None = None


class TraceStrategyRef(BaseModel):
    strategy_code: str
    version: int


class TraceResponse(BaseModel):
    trace_id: str
    decision_id: str
    application_id: str
    execution_mode: ExecutionMode
    strategy: TraceStrategyRef
    input_snapshot: dict[str, Any]
    feature_values: dict[str, Any]
    steps: list[dict[str, Any]]
    score_result: dict[str, Any] | None
    final_decision: dict[str, Any]
    # docs/07 names the aggregate output "final_decision"; it mirrors the
    # trace row's final_output column.
    errors: list[dict[str, Any]]
    metadata: dict[str, Any]
    created_at: str

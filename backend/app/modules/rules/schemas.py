"""Rule management API schemas (docs/phase3/08 §1)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.domain.enums import ConfigStatus

RuleKind = Literal["POLICY_OUTCOME", "STATEMENT", "CLASSIFICATION", "EXPRESSION"]


class _RuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_kind: RuleKind = "POLICY_OUTCOME"
    condition: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    branches: list[dict[str, Any]] | None = None
    default: list[dict[str, Any]] | None = None
    expression: str | None = Field(default=None, min_length=1, max_length=2_000)
    output_target: str | None = Field(default=None, min_length=1, max_length=200)
    version_note: str = ""

    @model_validator(mode="after")
    def _exactly_one_authoring_form(self) -> "_RuleBody":
        legacy = self.condition is not None or self.action is not None
        branched = self.branches is not None or self.default is not None
        expression = self.expression is not None or self.output_target is not None
        if sum((legacy, branched, expression)) != 1:
            raise ValueError(
                "provide exactly one authoring form: condition+action, branches, "
                "or expression+output_target"
            )
        if legacy and (self.condition is None or self.action is None):
            raise ValueError("legacy authoring requires both condition and action")
        if branched and self.branches is None:
            raise ValueError("branched authoring requires branches")
        if expression and (self.expression is None or self.output_target is None):
            raise ValueError("expression authoring requires expression and output_target")
        if expression and self.rule_kind != "EXPRESSION":
            raise ValueError("expression authoring requires rule_kind EXPRESSION")
        if not expression and self.rule_kind == "EXPRESSION":
            raise ValueError("rule_kind EXPRESSION requires expression authoring")
        return self

    def storage_body(self) -> tuple[dict[str, Any], dict[str, Any] | None]:
        if self.expression is not None:
            raise ValueError("expression rules require compilation before storage")
        if self.branches is not None:
            body: dict[str, Any] = {"branches": self.branches}
            if self.default is not None:
                body["default"] = self.default
            return body, None
        assert self.condition is not None and self.action is not None
        return self.condition, self.action


class RuleCreateRequest(_RuleBody):
    rule_code: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
    owner_team: str = "RISK"


class RuleVersionUpdateRequest(_RuleBody):
    pass


class RuleVersionResponse(BaseModel):
    id: str
    version: int
    status: ConfigStatus
    rule_kind: RuleKind
    condition: dict[str, Any] | None
    action: dict[str, Any] | None
    branches: list[dict[str, Any]]
    default: list[dict[str, Any]] | None
    expression: str | None = None
    output_target: str | None = None
    sql_preview: str
    version_note: str
    created_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None


class RuleResponse(BaseModel):
    id: str
    rule_code: str
    name: str
    description: str
    category: str
    owner_team: str
    active_version: int | None
    latest_version: int
    latest_status: ConfigStatus
    created_at: datetime | None


class RuleDetailResponse(RuleResponse):
    versions: list[RuleVersionResponse]


class RuleTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: dict[str, Any] = Field(
        description="Flat feature map, e.g. {'affordability.dti': 0.41}"
    )


class RuleTestResponse(BaseModel):
    matched: bool
    evaluated_conditions: list[dict[str, Any]]
    action: dict[str, Any]
    matched_branch: int | Literal["default"] | None = None
    actions_applied: list[dict[str, Any]] = Field(default_factory=list)
    outputs_after: dict[str, Any] = Field(default_factory=dict)


class RuleSetUsageItem(BaseModel):
    id: str
    code: str
    name: str


class StrategyUsageItem(BaseModel):
    id: str
    strategy_code: str
    versions_using: list[int]
    active_version_uses: bool


class RuleUsageResponse(BaseModel):
    rule_code: str
    rule_sets: list[RuleSetUsageItem]
    strategies: list[StrategyUsageItem]

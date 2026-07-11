"""Rule management API schemas (docs/phase3/08 §1)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.domain.enums import ConfigStatus, RuleCategory

RuleKind = Literal["POLICY_OUTCOME", "STATEMENT", "CLASSIFICATION", "EXPRESSION"]


class _RuleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_kind: RuleKind = "POLICY_OUTCOME"
    condition: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    branches: list[dict[str, Any]] | None = None
    default: list[dict[str, Any]] | None = None
    version_note: str = ""

    @model_validator(mode="after")
    def _exactly_one_authoring_form(self) -> "_RuleBody":
        legacy = self.condition is not None or self.action is not None
        branched = self.branches is not None or self.default is not None
        if legacy == branched:
            raise ValueError("provide exactly one authoring form: condition+action or branches")
        if legacy and (self.condition is None or self.action is None):
            raise ValueError("legacy authoring requires both condition and action")
        if branched and self.branches is None:
            raise ValueError("branched authoring requires branches")
        return self

    def storage_body(self) -> tuple[dict[str, Any], dict[str, Any] | None]:
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
    category: RuleCategory
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
    version_note: str
    created_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None


class RuleResponse(BaseModel):
    id: str
    rule_code: str
    name: str
    description: str
    category: RuleCategory
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

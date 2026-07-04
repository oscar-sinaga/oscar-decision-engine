"""Rule management API schemas (docs/07 §5)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.shared.domain.enums import ConfigStatus, RuleCategory


class RuleCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_code: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: RuleCategory
    owner_team: str = "RISK"
    condition: dict[str, Any]
    action: dict[str, Any]
    version_note: str = ""


class RuleVersionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition: dict[str, Any]
    action: dict[str, Any]
    version_note: str = ""


class RuleVersionResponse(BaseModel):
    id: str
    version: int
    status: ConfigStatus
    condition: dict[str, Any]
    action: dict[str, Any]
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

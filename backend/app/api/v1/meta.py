"""Metadata endpoints powering workbench dropdowns and the condition builder."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.engine.dsl import Operator
from app.engine.features import DERIVED_FEATURES, KNOWN_FEATURES
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.shared.domain.enums import (
    CasePriority,
    CaseStatus,
    ConfigStatus,
    DecisionType,
    ProductType,
    ReasonCodeCategory,
    ReasonSeverity,
    RuleCategory,
    StepOnError,
    StepType,
)

router = APIRouter(prefix="/meta", tags=["meta"])


class FeatureItem(BaseModel):
    path: str
    description: str
    derived: bool


class MetaResponse(BaseModel):
    features: list[FeatureItem]
    operators: list[str]
    decisions: list[str]
    product_types: list[str]
    rule_categories: list[str]
    config_statuses: list[str]
    step_types: list[str]
    step_on_error: list[str]
    case_statuses: list[str]
    case_priorities: list[str]
    reason_categories: list[str]
    reason_severities: list[str]


@router.get("", response_model=MetaResponse)
async def get_meta(user: Annotated[User, Depends(get_current_user)]) -> MetaResponse:
    return MetaResponse(
        features=[
            FeatureItem(path=path, description=desc, derived=path in DERIVED_FEATURES)
            for path, desc in sorted(KNOWN_FEATURES.items())
        ],
        operators=[op.value for op in Operator],
        decisions=[d.value for d in DecisionType],
        product_types=[p.value for p in ProductType],
        rule_categories=[c.value for c in RuleCategory],
        config_statuses=[s.value for s in ConfigStatus],
        step_types=[s.value for s in StepType],
        step_on_error=[s.value for s in StepOnError],
        case_statuses=[s.value for s in CaseStatus],
        case_priorities=[p.value for p in CasePriority],
        reason_categories=[c.value for c in ReasonCodeCategory],
        reason_severities=[s.value for s in ReasonSeverity],
    )

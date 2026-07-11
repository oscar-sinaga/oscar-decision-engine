"""Metadata endpoints powering workbench dropdowns and the condition builder."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.dsl import ActionType, Operator
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.features.models import Feature
from app.modules.rules.models import RuleCategory
from app.shared.database import get_session
from app.shared.domain.enums import (
    CasePriority,
    CaseStatus,
    ConfigStatus,
    DecisionType,
    FeatureSource,
    ProductType,
    ReasonCodeCategory,
    ReasonSeverity,
    StepOnError,
    StepType,
)

router = APIRouter(prefix="/meta", tags=["meta"])


class FeatureItem(BaseModel):
    path: str
    label: str
    description: str
    derived: bool
    data_type: str
    writable: bool
    category: str


class CategoryItem(BaseModel):
    code: str
    label: str


class WritableOutputItem(BaseModel):
    path: str
    data_type: str
    label: str


class MetaResponse(BaseModel):
    features: list[FeatureItem]
    operators: list[str]
    operators_by_type: dict[str, list[str]]
    decisions: list[str]
    product_types: list[str]
    rule_categories: list[CategoryItem]
    rule_kinds: list[str]
    action_types: list[str]
    node_types: list[str]
    edge_labels: list[str]
    writable_outputs: list[WritableOutputItem]
    config_statuses: list[str]
    step_types: list[str]
    step_on_error: list[str]
    case_statuses: list[str]
    case_priorities: list[str]
    reason_categories: list[str]
    reason_severities: list[str]


@router.get("", response_model=MetaResponse)
async def get_meta(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MetaResponse:
    features = (
        await session.scalars(
            select(Feature).where(Feature.active.is_(True)).order_by(Feature.path)
        )
    ).all()
    categories = (
        await session.scalars(
            select(RuleCategory).where(RuleCategory.active.is_(True)).order_by(RuleCategory.code)
        )
    ).all()
    operators_by_type = {
        "NUMBER": ["=", "!=", ">", ">=", "<", "<=", "in", "not_in", "exists", "is_null"],
        "STRING": ["=", "!=", "in", "not_in", "exists", "is_null"],
        "BOOLEAN": ["=", "!=", "exists", "is_null"],
        "DATE": ["=", "!=", ">", ">=", "<", "<=", "exists", "is_null"],
    }
    return MetaResponse(
        features=[
            FeatureItem(
                path=f.path,
                label=f.label,
                description=f.description,
                derived=f.source == FeatureSource.DERIVED,
                data_type=f.data_type,
                writable=f.writable,
                category=f.category,
            )
            for f in features
        ],
        operators=[op.value for op in Operator],
        operators_by_type=operators_by_type,
        decisions=[d.value for d in DecisionType],
        product_types=[p.value for p in ProductType],
        rule_categories=[CategoryItem(code=c.code, label=c.label) for c in categories],
        rule_kinds=["POLICY_OUTCOME", "STATEMENT", "CLASSIFICATION", "EXPRESSION"],
        action_types=[
            action.value for action in ActionType if action is not ActionType.SET_ATTRIBUTE
        ],
        node_types=[
            "START",
            "VALIDATION",
            "CALCULATION",
            "RULE_SET",
            "SCORECARD",
            "DECISION_TABLE",
            "CONDITION",
            "END",
        ],
        edge_labels=["TRUE", "FALSE"],
        writable_outputs=[
            WritableOutputItem(path=f.path, data_type=f.data_type, label=f.label)
            for f in features
            if f.writable
        ],
        config_statuses=[s.value for s in ConfigStatus],
        step_types=[s.value for s in StepType],
        step_on_error=[s.value for s in StepOnError],
        case_statuses=[s.value for s in CaseStatus],
        case_priorities=[p.value for p in CasePriority],
        reason_categories=[c.value for c in ReasonCodeCategory],
        reason_severities=[s.value for s in ReasonSeverity],
    )

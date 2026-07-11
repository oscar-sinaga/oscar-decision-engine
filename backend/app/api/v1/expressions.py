"""Admin-gated validation for the safe OSCAR expression language."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.expression import ExpressionError, validate_expression
from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.rules.service import active_feature_map, expression_feature_types
from app.shared.database import get_session
from app.shared.domain.errors import ValidationFailedError

router = APIRouter(prefix="/expressions", tags=["expressions"])


class ExpressionValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field(min_length=1, max_length=2_000)
    expects: Literal["value", "boolean"] = "value"


class ExpressionValidationResponse(BaseModel):
    valid: Literal[True] = True
    inferred_type: str
    referenced_features: list[str]
    normalized_preview: str
    ast_node_count: int


@router.post("/validate", response_model=ExpressionValidationResponse)
async def validate_expression_text(
    body: ExpressionValidationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: User = require_permission(Permissions.RULE_AUTHOR_EXPRESSION),
) -> ExpressionValidationResponse:
    features = await active_feature_map(session)
    try:
        result = validate_expression(
            body.expression,
            expression_feature_types(features),
            expects=body.expects,
        )
    except ExpressionError as exc:
        raise ValidationFailedError(
            "Expression is invalid",
            details=[
                {
                    "field": "expression",
                    "issue": exc.message,
                    "line": exc.line,
                    "col": exc.col,
                }
            ],
        ) from exc

    record_audit_event(
        session,
        event_type="EXPRESSION_VALIDATED",
        entity_type="EXPRESSION",
        entity_id="ad-hoc",
        action="VALIDATE_EXPRESSION",
        actor=user,
        metadata={
            "expects": body.expects,
            "inferred_type": result.inferred_type,
            "referenced_feature_count": len(result.referenced_features),
            "ast_node_count": result.node_count,
        },
    )
    await session.commit()
    return ExpressionValidationResponse(
        inferred_type=result.inferred_type,
        referenced_features=list(result.referenced_features),
        normalized_preview=result.normalized_preview,
        ast_node_count=result.node_count,
    )

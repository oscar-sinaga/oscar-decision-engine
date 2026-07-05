"""Feature catalog / data dictionary API (Phase 2).

Managed with the same rule.* permissions as other policy configuration.
Retiring (deactivating) a feature does not rewrite history: existing rule
versions keep referencing it, but new/edited rules can no longer use it.
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import record_audit_event
from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.features.models import Feature
from app.shared.database import get_session
from app.shared.domain.enums import FeatureDataType, FeatureSource
from app.shared.domain.errors import ConflictError, NotFoundError

router = APIRouter(prefix="/features", tags=["features"])

Session = Annotated[AsyncSession, Depends(get_session)]

_PATH_PATTERN = r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"


class FeatureCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=3, max_length=200, pattern=_PATH_PATTERN)
    label: str = Field(min_length=1, max_length=200)
    description: str = ""
    data_type: FeatureDataType
    source: FeatureSource
    category: str = Field(default="GENERAL", max_length=50)
    allowed_values: list[Any] | None = None


class FeatureUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    description: str | None = None
    data_type: FeatureDataType | None = None
    category: str | None = None
    allowed_values: list[Any] | None = None
    active: bool | None = None


class FeatureResponse(BaseModel):
    id: str
    path: str
    label: str
    description: str
    data_type: FeatureDataType
    source: FeatureSource
    category: str
    allowed_values: list[Any] | None
    active: bool
    created_at: datetime | None


def _response(feature: Feature) -> FeatureResponse:
    return FeatureResponse(
        id=str(feature.id),
        path=feature.path,
        label=feature.label,
        description=feature.description,
        data_type=feature.data_type,
        source=feature.source,
        category=feature.category,
        allowed_values=feature.allowed_values,
        active=feature.active,
        created_at=feature.created_at,
    )


@router.get("", response_model=list[FeatureResponse])
async def list_features(
    session: Session,
    source: Annotated[FeatureSource | None, Query()] = None,
    category: Annotated[str | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
    user: User = require_permission(Permissions.RULE_VIEW),
) -> list[FeatureResponse]:
    query = select(Feature).order_by(Feature.path)
    if source is not None:
        query = query.where(Feature.source == source)
    if category is not None:
        query = query.where(Feature.category == category)
    if active is not None:
        query = query.where(Feature.active.is_(active))
    rows = (await session.scalars(query)).all()
    return [_response(f) for f in rows]


@router.post("", response_model=FeatureResponse, status_code=201)
async def create_feature(
    body: FeatureCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> FeatureResponse:
    duplicate = await session.scalar(select(Feature).where(Feature.path == body.path))
    if duplicate is not None:
        raise ConflictError(f"Feature '{body.path}' already exists")
    feature = Feature(**body.model_dump())
    session.add(feature)
    await session.flush()
    record_audit_event(
        session,
        event_type="FEATURE_CREATED",
        entity_type="FEATURE",
        entity_id=feature.path,
        action="CREATE_FEATURE",
        actor=user,
        after_value=body.model_dump(),
    )
    await session.commit()
    return _response(feature)


@router.patch("/{feature_id}", response_model=FeatureResponse)
async def update_feature(
    feature_id: uuid.UUID,
    body: FeatureUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.RULE_CREATE),
) -> FeatureResponse:
    feature = await session.get(Feature, feature_id)
    if feature is None:
        raise NotFoundError(f"Feature '{feature_id}' not found")
    changes = dict(body.model_dump(exclude_unset=True).items())
    if not changes:
        return _response(feature)
    before = {key: getattr(feature, key) for key in changes}
    for key, value in changes.items():
        setattr(feature, key, value)
    record_audit_event(
        session,
        event_type="FEATURE_UPDATED",
        entity_type="FEATURE",
        entity_id=feature.path,
        action="UPDATE_FEATURE",
        actor=user,
        before_value=before,
        after_value=changes,
    )
    await session.commit()
    return _response(feature)

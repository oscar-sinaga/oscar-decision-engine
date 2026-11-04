"""Model registry API (docs/05 Phase 2)."""

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
from app.modules.model_registry.models import RegisteredModel
from app.shared.database import get_session
from app.shared.database.constraints import flush_unique
from app.shared.domain.errors import ConflictError, NotFoundError
from app.shared.domain.request_models import PatchRequest, StorageRequest

router = APIRouter(prefix="/models", tags=["models"])

Session = Annotated[AsyncSession, Depends(get_session)]


class ModelCreateRequest(StorageRequest):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    version_label: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(default="INTERNAL", max_length=100)
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelUpdateRequest(PatchRequest):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=200)
    provider: str | None = Field(default=None, max_length=100)
    description: str | None = None
    active: bool | None = None
    metadata: dict[str, Any] | None = None


class ModelResponse(BaseModel):
    id: str
    code: str
    version_label: str
    name: str
    provider: str
    description: str
    active: bool
    metadata: dict[str, Any]
    created_at: datetime | None


def _response(model: RegisteredModel) -> ModelResponse:
    return ModelResponse(
        id=str(model.id),
        code=model.code,
        version_label=model.version_label,
        name=model.name,
        provider=model.provider,
        description=model.description,
        active=model.active,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


@router.get("", response_model=list[ModelResponse])
async def list_models(
    session: Session,
    code: Annotated[str | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
    user: User = require_permission(Permissions.MODEL_VIEW),
) -> list[ModelResponse]:
    query = select(RegisteredModel).order_by(RegisteredModel.code, RegisteredModel.version_label)
    if code is not None:
        query = query.where(RegisteredModel.code == code)
    if active is not None:
        query = query.where(RegisteredModel.active.is_(active))
    rows = (await session.scalars(query)).all()
    return [_response(m) for m in rows]


@router.post("", response_model=ModelResponse, status_code=201)
async def register_model(
    body: ModelCreateRequest,
    session: Session,
    user: User = require_permission(Permissions.MODEL_MANAGE),
) -> ModelResponse:
    duplicate = await session.scalar(
        select(RegisteredModel).where(
            RegisteredModel.code == body.code,
            RegisteredModel.version_label == body.version_label,
        )
    )
    if duplicate is not None:
        raise ConflictError(f"Model '{body.code}' version '{body.version_label}' already exists")
    model = RegisteredModel(
        code=body.code,
        version_label=body.version_label,
        name=body.name,
        provider=body.provider,
        description=body.description,
        metadata_json=body.metadata,
        created_by=user.id,
    )
    session.add(model)
    await flush_unique(session, "Model code and version already exist")
    record_audit_event(
        session,
        event_type="MODEL_REGISTERED",
        entity_type="REGISTERED_MODEL",
        entity_id=f"{body.code}:{body.version_label}",
        action="REGISTER_MODEL",
        actor=user,
        after_value=body.model_dump(),
    )
    await session.commit()
    return _response(model)


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: uuid.UUID,
    body: ModelUpdateRequest,
    session: Session,
    user: User = require_permission(Permissions.MODEL_MANAGE),
) -> ModelResponse:
    model = await session.scalar(
        select(RegisteredModel)
        .where(RegisteredModel.id == model_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if model is None:
        raise NotFoundError(f"Model '{model_id}' not found")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _response(model)
    before = {key: getattr(model, "metadata_json" if key == "metadata" else key) for key in changes}
    for key, value in changes.items():
        setattr(model, "metadata_json" if key == "metadata" else key, value)
    record_audit_event(
        session,
        event_type="MODEL_UPDATED",
        entity_type="REGISTERED_MODEL",
        entity_id=f"{model.code}:{model.version_label}",
        action="UPDATE_MODEL",
        actor=user,
        before_value=before,
        after_value=changes,
    )
    await session.commit()
    return _response(model)

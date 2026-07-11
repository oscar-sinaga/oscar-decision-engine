"""Decision-table and scorecard management routes.

Both share the rule.* permissions: they are policy configuration managed by
the same roles (docs/14 §7).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.dependencies import require_permission
from app.modules.auth.models import User
from app.modules.auth.permissions import Permissions
from app.modules.scorecards import service
from app.modules.scorecards.service import DECISION_TABLE_KIND, SCORECARD_KIND, ConfigKind
from app.shared.database import get_session
from app.shared.domain.enums import ConfigStatus

Session = Annotated[AsyncSession, Depends(get_session)]


class ConfigCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    config: dict[str, Any]
    version_note: str = ""


class ConfigVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: dict[str, Any]
    version_note: str = ""


class LifecycleRequest(BaseModel):
    reason: str = ""


class ConfigVersionResponse(BaseModel):
    id: str
    version: int
    status: ConfigStatus
    config: dict[str, Any]
    version_note: str
    created_at: datetime | None
    warnings: list[dict[str, Any]] = []


class ConfigResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str
    active_version: int | None
    latest_version: int
    latest_status: ConfigStatus
    versions: list[ConfigVersionResponse]


def _version_response(
    version: Any, warnings: list[dict[str, Any]] | None = None
) -> ConfigVersionResponse:
    return ConfigVersionResponse(
        id=str(version.id),
        version=version.version,
        status=version.status,
        config=version.config_json,
        version_note=version.version_note,
        created_at=version.created_at,
        warnings=warnings or [],
    )


def _config_response(kind: ConfigKind, entity: Any) -> ConfigResponse:
    active = next((v for v in entity.versions if v.status == ConfigStatus.ACTIVE), None)
    latest = max(entity.versions, key=lambda v: v.version)
    return ConfigResponse(
        id=str(entity.id),
        code=entity.code,
        name=entity.name,
        description=entity.description,
        active_version=active.version if active else None,
        latest_version=latest.version,
        latest_status=latest.status,
        versions=[
            _version_response(v, service.validate_config(kind, v.config_json))
            for v in sorted(entity.versions, key=lambda v: v.version)
        ],
    )


def build_config_router(kind: ConfigKind, prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.post("", response_model=ConfigResponse, status_code=201)
    async def create(
        body: ConfigCreateRequest,
        session: Session,
        user: User = require_permission(Permissions.RULE_CREATE),
    ) -> ConfigResponse:
        entity, _warnings = await service.create_config(
            kind,
            session,
            code=body.code,
            name=body.name,
            description=body.description,
            config=body.config,
            version_note=body.version_note,
            actor=user,
        )
        return _config_response(kind, entity)

    @router.get("", response_model=list[ConfigResponse])
    async def list_all(
        session: Session,
        user: User = require_permission(Permissions.RULE_VIEW),
    ) -> list[ConfigResponse]:
        entities = (
            await session.scalars(
                select(kind.identity_model)
                .options(selectinload(kind.identity_model.versions))
                .order_by(kind.identity_model.code)
            )
        ).all()
        return [_config_response(kind, e) for e in entities if e.versions]

    @router.get("/{entity_id}", response_model=ConfigResponse)
    async def get_one(
        entity_id: uuid.UUID,
        session: Session,
        user: User = require_permission(Permissions.RULE_VIEW),
    ) -> ConfigResponse:
        entity = await service.get_identity(kind, session, entity_id)
        return _config_response(kind, entity)

    @router.post("/{entity_id}/versions", response_model=ConfigVersionResponse, status_code=201)
    async def create_version(
        entity_id: uuid.UUID,
        body: ConfigVersionRequest,
        session: Session,
        user: User = require_permission(Permissions.RULE_CREATE),
    ) -> ConfigVersionResponse:
        entity = await service.get_identity(kind, session, entity_id)
        version, warnings = await service.create_config_version(
            kind, session, entity, config=body.config, version_note=body.version_note, actor=user
        )
        return _version_response(version, warnings)

    @router.put("/{entity_id}/versions/{version_id}", response_model=ConfigVersionResponse)
    async def update_version(
        entity_id: uuid.UUID,
        version_id: uuid.UUID,
        body: ConfigVersionRequest,
        session: Session,
        user: User = require_permission(Permissions.RULE_CREATE),
    ) -> ConfigVersionResponse:
        entity = await service.get_identity(kind, session, entity_id)
        version = service.get_version(kind, entity, version_id)
        updated, warnings = await service.update_config_version(
            kind,
            session,
            entity,
            version,
            config=body.config,
            version_note=body.version_note,
            actor=user,
        )
        return _version_response(updated, warnings)

    @router.post(
        "/{entity_id}/versions/{version_id}/submit-approval",
        response_model=ConfigVersionResponse,
    )
    async def submit_version(
        entity_id: uuid.UUID,
        version_id: uuid.UUID,
        session: Session,
        user: User = require_permission(Permissions.RULE_CREATE),
    ) -> ConfigVersionResponse:
        entity = await service.get_identity(kind, session, entity_id)
        version = service.get_version(kind, entity, version_id)
        return _version_response(
            await service.submit_config_version(kind, session, entity, version, user)
        )

    @router.post(
        "/{entity_id}/versions/{version_id}/activate", response_model=ConfigVersionResponse
    )
    async def activate_version(
        entity_id: uuid.UUID,
        version_id: uuid.UUID,
        body: LifecycleRequest,
        session: Session,
        user: User = require_permission(Permissions.RULE_APPROVE),
    ) -> ConfigVersionResponse:
        entity = await service.get_identity(kind, session, entity_id)
        version = service.get_version(kind, entity, version_id)
        return _version_response(
            await service.activate_config_version(kind, session, entity, version, user, body.reason)
        )

    return router


decision_tables_router = build_config_router(
    DECISION_TABLE_KIND, "/decision-tables", "decision-tables"
)
scorecards_router = build_config_router(SCORECARD_KIND, "/scorecards", "scorecards")

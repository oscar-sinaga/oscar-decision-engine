"""Decision-table and scorecard management: validation, versioning, lifecycle, audit.

Both entities share the identity+versions pattern; this service implements the
lifecycle generically and validates configs with the engine parsers, so a
config that persists is guaranteed executable.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.decision_table import find_overlapping_rows, parse_decision_table_config
from app.engine.scorecard import parse_scorecard_config
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.shared.domain.enums import ConfigStatus
from app.shared.domain.errors import ConflictError, NotFoundError, ValidationFailedError
from app.shared.domain.version_lifecycle import (
    activate_version,
    ensure_editable,
    submit_for_approval,
)


@dataclass(frozen=True)
class ConfigKind:
    entity_type: str
    identity_model: type[Any]
    version_model: type[Any]
    identity_fk: str


DECISION_TABLE_KIND = ConfigKind(
    entity_type="DECISION_TABLE",
    identity_model=DecisionTable,
    version_model=DecisionTableVersion,
    identity_fk="decision_table_id",
)
SCORECARD_KIND = ConfigKind(
    entity_type="SCORECARD",
    identity_model=Scorecard,
    version_model=ScorecardVersion,
    identity_fk="scorecard_id",
)


def validate_config(kind: ConfigKind, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate a config with the engine parser. Returns non-blocking warnings."""
    try:
        if kind is DECISION_TABLE_KIND:
            parsed = parse_decision_table_config(config)
            return [
                {
                    "warning": "OVERLAPPING_ROWS",
                    "rows": list(pair),
                    "detail": "Rows can match the same input; hit policy decides the winner",
                }
                for pair in find_overlapping_rows(parsed)
            ]
        parse_scorecard_config(config)
        return []
    except ValidationError as exc:
        raise ValidationFailedError(
            f"{kind.entity_type} configuration is invalid",
            details=[
                {"field": ".".join(str(part) for part in err["loc"]), "issue": err["msg"]}
                for err in exc.errors()
            ],
        ) from exc


async def get_identity(kind: ConfigKind, session: AsyncSession, entity_id: uuid.UUID) -> Any:
    entity = await session.scalar(
        select(kind.identity_model)
        .where(kind.identity_model.id == entity_id)
        .options(selectinload(kind.identity_model.versions))
    )
    if entity is None:
        raise NotFoundError(f"{kind.entity_type} '{entity_id}' not found")
    return entity


def get_version(kind: ConfigKind, entity: Any, version_id: uuid.UUID) -> Any:
    for version in entity.versions:
        if version.id == version_id:
            return version
    raise NotFoundError(f"{kind.entity_type} version '{version_id}' not found")


async def create_config(
    kind: ConfigKind,
    session: AsyncSession,
    *,
    code: str,
    name: str,
    description: str,
    config: dict[str, Any],
    version_note: str,
    actor: User,
) -> tuple[Any, list[dict[str, Any]]]:
    warnings = validate_config(kind, config)
    duplicate = await session.scalar(
        select(kind.identity_model).where(kind.identity_model.code == code)
    )
    if duplicate is not None:
        raise ConflictError(f"{kind.entity_type} code '{code}' already exists")

    entity = kind.identity_model(code=code, name=name, description=description)
    session.add(entity)
    await session.flush()
    version = kind.version_model(
        **{kind.identity_fk: entity.id},
        version=1,
        status=ConfigStatus.DRAFT,
        config_json=config,
        version_note=version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()
    record_audit_event(
        session,
        event_type=f"{kind.entity_type}_CREATED",
        entity_type=kind.entity_type,
        entity_id=code,
        entity_version="1",
        action=f"CREATE_{kind.entity_type}",
        actor=actor,
        after_value={"name": name, "config": config, "status": ConfigStatus.DRAFT},
        metadata={"warnings": warnings},
    )
    await session.commit()
    return await get_identity(kind, session, entity.id), warnings


async def create_config_version(
    kind: ConfigKind,
    session: AsyncSession,
    entity: Any,
    *,
    config: dict[str, Any],
    version_note: str,
    actor: User,
) -> tuple[Any, list[dict[str, Any]]]:
    warnings = validate_config(kind, config)
    open_versions = [
        v
        for v in entity.versions
        if v.status in (ConfigStatus.DRAFT, ConfigStatus.PENDING_APPROVAL)
    ]
    if open_versions:
        raise ConflictError(
            f"{kind.entity_type} '{entity.code}' already has an open draft/pending version"
        )
    next_version = max((v.version for v in entity.versions), default=0) + 1
    version = kind.version_model(
        **{kind.identity_fk: entity.id},
        version=next_version,
        status=ConfigStatus.DRAFT,
        config_json=config,
        version_note=version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()
    record_audit_event(
        session,
        event_type=f"{kind.entity_type}_VERSION_CREATED",
        entity_type=f"{kind.entity_type}_VERSION",
        entity_id=entity.code,
        entity_version=str(next_version),
        action=f"CREATE_{kind.entity_type}_VERSION",
        actor=actor,
        after_value={"config": config},
        metadata={"warnings": warnings},
    )
    await session.commit()
    return version, warnings


async def update_config_version(
    kind: ConfigKind,
    session: AsyncSession,
    entity: Any,
    version: Any,
    *,
    config: dict[str, Any],
    version_note: str,
    actor: User,
) -> tuple[Any, list[dict[str, Any]]]:
    ensure_editable(version)
    warnings = validate_config(kind, config)
    before = {"config": version.config_json}
    version.config_json = config
    version.version_note = version_note or version.version_note
    record_audit_event(
        session,
        event_type=f"{kind.entity_type}_VERSION_UPDATED",
        entity_type=f"{kind.entity_type}_VERSION",
        entity_id=entity.code,
        entity_version=str(version.version),
        action=f"UPDATE_{kind.entity_type}_VERSION",
        actor=actor,
        before_value=before,
        after_value={"config": config},
        metadata={"warnings": warnings},
    )
    await session.commit()
    return version, warnings


async def submit_config_version(
    kind: ConfigKind, session: AsyncSession, entity: Any, version: Any, actor: User
) -> Any:
    before = version.status
    submit_for_approval(version)
    record_audit_event(
        session,
        event_type=f"{kind.entity_type}_VERSION_SUBMITTED",
        entity_type=f"{kind.entity_type}_VERSION",
        entity_id=entity.code,
        entity_version=str(version.version),
        action="SUBMIT_FOR_APPROVAL",
        actor=actor,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version


async def activate_config_version(
    kind: ConfigKind,
    session: AsyncSession,
    entity: Any,
    version: Any,
    actor: User,
    reason: str | None,
) -> Any:
    previous_active = next((v for v in entity.versions if v.status == ConfigStatus.ACTIVE), None)
    before = version.status
    activate_version(version, previous_active)
    version.approved_by = actor.id
    record_audit_event(
        session,
        event_type=f"{kind.entity_type}_VERSION_ACTIVATED",
        entity_type=f"{kind.entity_type}_VERSION",
        entity_id=entity.code,
        entity_version=str(version.version),
        action=f"ACTIVATE_{kind.entity_type}_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={
            "status": version.status,
            "retired_version": previous_active.version if previous_active else None,
        },
    )
    await session.commit()
    return version

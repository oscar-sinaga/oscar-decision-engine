"""Business audit event recording.

Audit events are written inside the caller's transaction: if the state change
fails, the event rolls back with it; if the audit insert fails, the state
change fails too (no silent unaudited change — docs/18 §12).
All before/after/metadata values pass through the PII redactor.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.shared.domain.enums import ActorType
from app.shared.logging import get_correlation_id, get_logger, get_request_id
from app.shared.utils.masking import redact

logger = get_logger("oscar.audit")


def record_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: User | None = None,
    actor_type: ActorType | None = None,
    entity_version: str | None = None,
    reason: str | None = None,
    before_value: dict[str, Any] | None = None,
    after_value: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit event in the current transaction (caller commits)."""
    resolved_actor_type = actor_type or (actor.actor_type if actor else ActorType.SYSTEM)
    event = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_type=resolved_actor_type,
        actor_label=actor.username if actor else "SYSTEM",
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_version=entity_version,
        action=action,
        reason=reason,
        before_value=redact(before_value) if before_value is not None else None,
        after_value=redact(after_value) if after_value is not None else None,
        metadata_json=redact(metadata or {}),
        correlation_id=get_correlation_id(),
        request_id=get_request_id(),
    )
    session.add(event)
    logger.info(
        "audit.event_staged",
        extra={"event_type": event_type, "entity_type": entity_type, "entity_id": entity_id},
    )
    return event

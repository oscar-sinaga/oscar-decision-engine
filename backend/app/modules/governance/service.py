"""Governance helpers: maker-checker enforcement and approval requests (docs/14 §5–6)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.governance.models import ApprovalRequest
from app.shared.domain.enums import ApprovalStatus
from app.shared.domain.errors import AuthorizationError
from app.shared.utils.ids import display_id


def ensure_maker_checker(created_by: uuid.UUID | None, approver: User) -> None:
    """The approver must differ from the maker (docs/14 §6)."""
    if created_by is not None and created_by == approver.id:
        raise AuthorizationError(
            "Maker-checker violation: the creator of a change cannot approve it"
        )


def open_approval_request(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    entity_version: str,
    requested_by: User,
    change_summary: str = "",
    request_reason: str = "",
    simulation_ref: str | None = None,
) -> ApprovalRequest:
    request = ApprovalRequest(
        request_id=display_id("APR"),
        entity_type=entity_type,
        entity_id=entity_id,
        entity_version=entity_version,
        status=ApprovalStatus.PENDING,
        change_summary=change_summary,
        request_reason=request_reason,
        simulation_ref=simulation_ref,
        requested_by=requested_by.id,
    )
    session.add(request)
    return request


async def pending_approval_request(
    session: AsyncSession, *, entity_type: str, entity_id: str, entity_version: str
) -> ApprovalRequest | None:
    request: ApprovalRequest | None = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == entity_id,
            ApprovalRequest.entity_version == entity_version,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    return request


async def resolve_approval_request(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: str,
    entity_version: str,
    status: ApprovalStatus,
    decided_by: User,
    decision_reason: str | None = None,
) -> ApprovalRequest | None:
    request = await session.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.entity_type == entity_type,
            ApprovalRequest.entity_id == entity_id,
            ApprovalRequest.entity_version == entity_version,
            ApprovalRequest.status == ApprovalStatus.PENDING,
        )
    )
    if request is None:
        return None
    request.status = status
    request.decided_by = decided_by.id
    request.decided_at = datetime.now(UTC)
    request.decision_reason = decision_reason
    return request


async def ensure_independent_approver(
    session: AsyncSession,
    created_by: uuid.UUID | None,
    approver: User,
    *,
    entity_type: str,
    entity_id: str,
    entity_version: str,
) -> None:
    """Reject approval by the creator, any recorded editor, or the submitter."""
    ensure_maker_checker(created_by, approver)
    contributed = await session.scalar(
        select(AuditLog.id)
        .where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            AuditLog.entity_version == entity_version,
            AuditLog.actor_user_id == approver.id,
            AuditLog.event_type.in_([f"{entity_type}_UPDATED", f"{entity_type}_SUBMITTED"]),
        )
        .limit(1)
    )
    pending = await pending_approval_request(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_version=entity_version,
    )
    if contributed is not None or (pending is not None and pending.requested_by == approver.id):
        raise AuthorizationError(
            "Maker-checker violation: editors and submitters cannot approve their change"
        )

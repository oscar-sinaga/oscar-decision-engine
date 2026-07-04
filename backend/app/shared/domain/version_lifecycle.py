"""Shared lifecycle transitions for versioned configuration (docs/14 §4).

Rules, decision tables, scorecards, and strategies share the same version
lifecycle::

    DRAFT → PENDING_APPROVAL → ACTIVE → RETIRED
                  ↘ REJECTED (back to draft via new version)

Invariants enforced here:
- only DRAFT versions are editable;
- only DRAFT versions can be submitted;
- only PENDING_APPROVAL versions can be activated (approve+activate is a
  single controlled action in MVP);
- activating a version retires the previously active one (kept readable);
- ACTIVE/RETIRED versions are immutable.
"""

from datetime import UTC, datetime
from typing import Any, Protocol

from app.shared.domain.enums import ConfigStatus
from app.shared.domain.errors import ConflictError, ImmutableConfigurationError


class VersionedConfig(Protocol):
    status: ConfigStatus
    version: int


def ensure_editable(version: Any) -> None:
    if version.status != ConfigStatus.DRAFT:
        raise ImmutableConfigurationError(
            f"Version {version.version} is {version.status} and cannot be edited; "
            "create a new draft version instead"
        )


def submit_for_approval(version: Any) -> None:
    if version.status != ConfigStatus.DRAFT:
        raise ConflictError(f"Only DRAFT versions can be submitted (current: {version.status})")
    version.status = ConfigStatus.PENDING_APPROVAL


def reject_version(version: Any) -> None:
    if version.status != ConfigStatus.PENDING_APPROVAL:
        raise ConflictError(
            f"Only PENDING_APPROVAL versions can be rejected (current: {version.status})"
        )
    version.status = ConfigStatus.REJECTED


def activate_version(version: Any, previous_active: Any | None) -> None:
    if version.status not in (ConfigStatus.PENDING_APPROVAL, ConfigStatus.DRAFT):
        raise ConflictError(
            f"Version {version.version} is {version.status} and cannot be activated"
        )
    if version.status == ConfigStatus.DRAFT:
        # MVP allows permission-controlled direct activation of drafts, but the
        # submitted flow is the documented path; governance hardening tightens
        # this in the maker-checker phase.
        raise ConflictError("Version must be submitted for approval before activation")
    if previous_active is not None and previous_active is not version:
        previous_active.status = ConfigStatus.RETIRED
        if hasattr(previous_active, "effective_to"):
            previous_active.effective_to = datetime.now(UTC)
    version.status = ConfigStatus.ACTIVE
    if hasattr(version, "effective_from"):
        version.effective_from = datetime.now(UTC)


def retire_version(version: Any) -> None:
    if version.status != ConfigStatus.ACTIVE:
        raise ConflictError(f"Only ACTIVE versions can be retired (current: {version.status})")
    version.status = ConfigStatus.RETIRED
    if hasattr(version, "effective_to"):
        version.effective_to = datetime.now(UTC)

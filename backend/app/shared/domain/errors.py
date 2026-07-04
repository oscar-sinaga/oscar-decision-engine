"""Domain error hierarchy mapped to the structured API error contract.

Errors carry a stable safe ``code`` and never embed stack traces, SQL, or
third-party payloads. API handlers translate them into the envelope defined in
``docs/07_api_contract.md``.
"""

from typing import Any


class DomainError(Exception):
    code = "DOMAIN_ERROR"
    status_code = 400

    def __init__(self, message: str, *, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationFailedError(DomainError):
    code = "VALIDATION_ERROR"
    status_code = 422


class NotFoundError(DomainError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(DomainError):
    code = "CONFLICT"
    status_code = 409


class ImmutableConfigurationError(DomainError):
    code = "IMMUTABLE_CONFIGURATION"
    status_code = 409


class AuthenticationError(DomainError):
    code = "AUTHENTICATION_REQUIRED"
    status_code = 401


class AuthorizationError(DomainError):
    code = "FORBIDDEN"
    status_code = 403


class ConfigurationError(DomainError):
    """Raised when active policy configuration is missing or inconsistent."""

    code = "CONFIGURATION_ERROR"
    status_code = 422


class AuditPersistenceError(DomainError):
    """Raised when a mandatory business audit event cannot be persisted.

    Critical state changes must fail explicitly rather than proceed unaudited.
    """

    code = "AUDIT_PERSISTENCE_FAILED"
    status_code = 500

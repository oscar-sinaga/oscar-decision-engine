"""PII and secret masking utilities.

Two use cases share this module:

1. **Log sanitization** — every structured value attached to a technical log
   record is passed through :func:`redact` so prohibited content (NIK, phone,
   address, tokens, credentials, documents) never reaches the log sink.
2. **Snapshot sanitization** — decision traces persist an input snapshot;
   :func:`sanitize_snapshot` masks direct identifiers while keeping the
   decision-relevant values needed for reproducibility.

Masking is deny-list based on key names and intentionally over-redacts:
a false positive hides one value, a false negative leaks PII.
"""

from typing import Any

REDACTED = "***REDACTED***"

# Key-name tokens whose values must never appear in logs or snapshots.
SENSITIVE_KEY_TOKENS: tuple[str, ...] = (
    "nik",
    "ktp",
    "npwp",
    "passport",
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "credential",
    "cookie",
    "session_id",
    "phone",
    "mobile",
    "msisdn",
    "email",
    "address",
    "bank_account",
    "account_number",
    "card_number",
    "document",
    "birth_date",
    "date_of_birth",
    "mother_maiden",
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_KEY_TOKENS)


def redact(value: Any) -> Any:
    """Recursively mask values held under sensitive keys in dicts/lists."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if is_sensitive_key(str(key)) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


def sanitize_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Mask direct identifiers in an application payload before persistence."""
    result = redact(payload)
    if not isinstance(result, dict):  # pragma: no cover - dict in, dict out
        raise TypeError("snapshot payload must be a mapping")
    return result

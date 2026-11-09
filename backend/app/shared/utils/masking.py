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
    "customer_id",
    "applicant_id",
    "full_name",
    "birth_place",
    "iban",
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(token in normalized for token in SENSITIVE_KEY_TOKENS)


_FIELD_REFERENCE_KEYS = ("field", "target", "feature", "feature_path", "output_target")
_FIELD_VALUE_KEYS = {
    "value",
    "actual",
    "expected",
    "observed",
    "left",
    "right",
    "resolved_value",
    "calculated_value",
    "input",
    "result",
}


def redact(value: Any) -> Any:
    """Mask sensitive keys and values associated with sensitive dotted feature paths.

    Rule evaluation evidence often represents a feature as {"field": "<path>",
    "actual": <raw value>}; masking by dictionary key alone misses these values.
    """
    if isinstance(value, dict):
        sensitive_reference = any(
            isinstance(value.get(ref), str) and is_sensitive_key(value[ref])
            for ref in _FIELD_REFERENCE_KEYS
        )
        return {
            key: (
                REDACTED
                if is_sensitive_key(str(key))
                or (sensitive_reference and str(key) in _FIELD_VALUE_KEYS)
                else redact(item)
            )
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

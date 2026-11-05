"""Strict JSON and governed feature validation, independent of API/database code."""

import math
from datetime import date
from typing import Any, TypeGuard


def finite_number(value: Any) -> TypeGuard[int | float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def iso_date(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 10:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _validate_storage_string(value: str) -> None:
    if "\x00" in value:
        raise ValueError("JSON strings must not contain NUL characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("JSON strings must contain valid Unicode scalar values") from exc


def validate_payload_json(value: Any, depth: int = 0, *, undotted_keys: bool = True) -> None:
    """Reject invalid JSON numbers and ambiguous paths before flattening/persistence.

    Error messages intentionally omit input values, including unknown nested fields.
    """
    if depth > 32:
        raise ValueError("Application payload nesting exceeds the supported limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or (undotted_keys and "." in key):
                raise ValueError("Application payload keys must be undotted strings")
            _validate_storage_string(key)
            validate_payload_json(item, depth + 1, undotted_keys=undotted_keys)
    elif isinstance(value, list):
        for item in value:
            validate_payload_json(item, depth + 1, undotted_keys=undotted_keys)
    elif isinstance(value, str):
        _validate_storage_string(value)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not finite_number(value):
            raise ValueError("Application payload numbers must be finite and representable")
    elif value is not None and not isinstance(value, (str, bool)):
        raise ValueError("Application payload must contain JSON-compatible values")


def feature_type_errors(features: dict[str, Any], types: dict[str, str]) -> list[dict[str, str]]:
    """Validate supplied catalog inputs without coercing strings/numbers/booleans.

    Missing and null values remain controlled by the strategy VALIDATION node.
    """
    errors = []
    for path, kind in types.items():
        value = features.get(path)
        if value is None:
            continue
        valid = {
            "NUMBER": finite_number(value),
            "BOOLEAN": isinstance(value, bool),
            "STRING": isinstance(value, str),
            "DATE": iso_date(value),
        }.get(kind, False)
        if not valid:
            errors.append({"field": path, "issue": f"must match catalog type {kind}"})
    return errors

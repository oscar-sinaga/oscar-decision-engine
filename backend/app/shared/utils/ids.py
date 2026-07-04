"""Identifier generation and validation helpers.

Business identifiers are human-scannable (``DEC-20260704-3F9A2C71E0``) while
technical identifiers (request/correlation) are opaque. Correlation IDs coming
from callers are only accepted when they match a safe charset so they can be
logged and returned in headers without sanitization concerns.
"""

import re
from datetime import UTC, datetime
from uuid import uuid4

_SAFE_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:\-]{8,128}$")


def new_request_id() -> str:
    return f"req-{uuid4().hex}"


def new_correlation_id() -> str:
    return f"corr-{uuid4().hex}"


def sanitize_correlation_id(raw: str | None) -> str | None:
    """Return the inbound correlation ID if safe to propagate, else ``None``."""
    if raw is None:
        return None
    candidate = raw.strip()
    if _SAFE_CORRELATION_ID.fullmatch(candidate):
        return candidate
    return None


def display_id(prefix: str, at: datetime | None = None) -> str:
    """Generate a business-facing identifier such as ``DEC-20260704-3F9A2C71E0``."""
    stamp = (at or datetime.now(UTC)).strftime("%Y%m%d")
    return f"{prefix}-{stamp}-{uuid4().hex[:10].upper()}"

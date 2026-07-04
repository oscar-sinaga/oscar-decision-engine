"""Structured JSON logging on top of the standard library.

Every record is emitted as one JSON object containing timestamp, level,
logger, event, request/correlation IDs, and sanitized structured fields.
Values attached via ``extra={"data": {...}}`` are passed through the PII
redactor before serialization so prohibited content cannot reach the sink.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.shared.logging.context import get_correlation_id, get_request_id
from app.shared.utils.masking import redact

_STANDARD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()) | {
    "message",
    "asctime",
    "taskName",
}


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": get_request_id(),
            "correlation_id": get_correlation_id(),
        }
        for key, value in record.__dict__.items():
            if key in _STANDARD_ATTRS or key.startswith("_"):
                continue
            payload[key] = redact(value) if isinstance(value, (dict, list, tuple)) else value
        if record.exc_info and record.exc_info[0] is not None:
            # Exception *type* only; stack traces stay out of structured logs
            # and are never returned to clients.
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload, default=str, ensure_ascii=False)


class TextLogFormatter(logging.Formatter):
    """Readable single-line formatter for local debugging (OSCAR_LOG_JSON=false)."""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        corr = get_correlation_id()
        return f"{base} correlation_id={corr}" if corr else base


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    # Uvicorn's access log duplicates the middleware request log; silence it.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

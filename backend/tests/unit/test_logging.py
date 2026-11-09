import json
import logging

from app.shared.logging.context import set_correlation_context
from app.shared.logging.logger import JsonLogFormatter
from app.shared.utils.masking import REDACTED

PROHIBITED_VALUES = [
    "3174091202900001",  # NIK-like
    "+628123456789",  # full phone
    "Jl. Melati No. 5",  # address
    "super-secret-token",
]


def _format(record: logging.LogRecord) -> str:
    return JsonLogFormatter().format(record)


def _record(event: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="oscar.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=event,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_log_output_is_json_with_context() -> None:
    with set_correlation_context("req-abc", "corr-xyz"):
        output = _format(_record("decision.executed", duration_ms=12))
    payload = json.loads(output)
    assert payload["event"] == "decision.executed"
    assert payload["request_id"] == "req-abc"
    assert payload["correlation_id"] == "corr-xyz"
    assert payload["duration_ms"] == 12
    assert payload["level"] == "INFO"


def test_log_output_masks_prohibited_pii() -> None:
    output = _format(
        _record(
            "application.received",
            data={
                "nik": PROHIBITED_VALUES[0],
                "phone": PROHIBITED_VALUES[1],
                "address": PROHIBITED_VALUES[2],
                "api_token": PROHIBITED_VALUES[3],
                "application_id": "APP-1",
            },
        )
    )
    for prohibited in PROHIBITED_VALUES:
        assert prohibited not in output
    payload = json.loads(output)
    assert payload["data"]["nik"] == REDACTED
    assert payload["data"]["application_id"] == "APP-1"


def test_exception_logs_type_only_no_stack_trace() -> None:
    try:
        raise RuntimeError("boom with secret detail")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            name="oscar.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="http.request.unhandled_error",
            args=(),
            exc_info=sys.exc_info(),
        )
    output = _format(record)
    payload = json.loads(output)
    assert payload["exception_type"] == "RuntimeError"
    assert "Traceback" not in output
    assert "boom with secret detail" not in output


def test_log_output_masks_scalar_extra_fields() -> None:
    output = _format(_record("auth.failure", api_token="sensitive-scalar", nik="3170000000000001"))
    parsed = json.loads(output)
    assert parsed["api_token"] == REDACTED
    assert parsed["nik"] == REDACTED
    assert "sensitive-scalar" not in output

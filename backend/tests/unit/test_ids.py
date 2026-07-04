import re

from app.shared.utils.ids import (
    display_id,
    new_correlation_id,
    new_request_id,
    sanitize_correlation_id,
)


def test_generated_ids_have_prefixes() -> None:
    assert new_request_id().startswith("req-")
    assert new_correlation_id().startswith("corr-")


def test_display_id_format() -> None:
    value = display_id("DEC")
    assert re.fullmatch(r"DEC-\d{8}-[0-9A-F]{10}", value)


def test_sanitize_correlation_id_accepts_safe_values() -> None:
    assert sanitize_correlation_id("corr-1234abcd") == "corr-1234abcd"
    assert sanitize_correlation_id("  corr-1234abcd  ") == "corr-1234abcd"


def test_sanitize_correlation_id_rejects_unsafe_values() -> None:
    assert sanitize_correlation_id(None) is None
    assert sanitize_correlation_id("short") is None
    assert sanitize_correlation_id("bad value with spaces") is None
    assert sanitize_correlation_id("x" * 200) is None
    assert sanitize_correlation_id('inject"header\r\n') is None

"""Regressions for malformed workflow configuration and PostgreSQL-safe JSON."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.modules.decisions.schemas import DecisionRequest
from app.modules.strategies.schemas import (
    GraphRequest,
    NodeRequest,
    Position,
    StepRequest,
    StrategyCreateRequest,
    StrategyVersionCreateRequest,
)


@pytest.mark.parametrize(
    "node_type,key", [("VALIDATION", "required_fields"), ("CALCULATION", "calculations")]
)
@pytest.mark.parametrize("value", [None, {}, "applicant.age", [None], [{}], [1], [""]])
def test_node_config_requires_a_list_of_nonempty_paths(
    node_type: str, key: str, value: Any
) -> None:
    with pytest.raises(ValidationError):
        NodeRequest.model_validate({"node_type": node_type, "config": {key: value}})


@pytest.mark.parametrize(
    "step_type,key", [("VALIDATION", "required_fields"), ("CALCULATION", "calculations")]
)
@pytest.mark.parametrize("value", [None, {}, "applicant.age", [None], [{}], [1], [""]])
def test_legacy_config_has_the_same_contract(step_type: str, key: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        StepRequest.model_validate({"order": 1, "type": step_type, "config": {key: value}})


@pytest.mark.parametrize("axis,value", [("x", 2**31), ("y", -(2**31) - 1)])
def test_canvas_positions_fit_postgresql_integer(axis: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Position.model_validate({axis: value})


@pytest.mark.parametrize("field,value", [("name", "n" * 201), ("reference_code", "R" * 101)])
def test_legacy_steps_respect_node_storage_limits(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        StepRequest.model_validate({"order": 1, "type": "RULE_SET", field: value})


def test_strategy_owner_fits_storage() -> None:
    with pytest.raises(ValidationError):
        StrategyCreateRequest.model_validate(
            {
                "strategy_code": "BOUNDARY",
                "name": "Boundary",
                "product_type": "MOTOR_LEASEBACK",
                "owner_team": "T" * 101,
            }
        )


def test_graph_collections_are_bounded_before_service_validation() -> None:
    with pytest.raises(ValidationError):
        GraphRequest.model_validate({"nodes": [{"node_type": "END"}] * 101})
    with pytest.raises(ValidationError):
        GraphRequest.model_validate(
            {
                "nodes": [{"node_key": "s", "node_type": "START"}],
                "edges": [{"from": "s", "to": "s"}] * 201,
            }
        )
    with pytest.raises(ValidationError):
        StrategyVersionCreateRequest.model_validate(
            {"steps": [{"order": i + 1, "type": "VALIDATION"} for i in range(99)]}
        )


@pytest.mark.parametrize("bad", ["\x00", "\ud800", "\udfff"])
@pytest.mark.parametrize("location", ["application_id", "nested_value", "nested_key"])
def test_request_rejects_strings_postgresql_cannot_store(bad: str, location: str) -> None:
    payload: dict[str, Any] = {"application_id": "APP-BOUNDARY", "product_type": "MOTOR_LEASEBACK"}
    if location == "application_id":
        payload["application_id"] = "A" + bad
    elif location == "nested_value":
        payload["applicant"] = {"custom_note": "A" + bad}
    else:
        payload["applicant"] = {"custom" + bad: 1}
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate(payload)


def test_valid_unicode_and_optional_empty_config_still_work() -> None:
    result = DecisionRequest.model_validate(
        {
            "application_id": "APP-✓",
            "product_type": "MOTOR_LEASEBACK",
            "applicant": {"custom_note": "Café 日本語 😀"},
        }
    )
    assert result.applicant["custom_note"] == "Café 日本語 😀"
    assert NodeRequest(node_type="VALIDATION").config == {}
    assert NodeRequest(node_type="CALCULATION", config={"calculations": []}).config == {
        "calculations": []
    }


def test_patch_omission_clear_and_false_are_distinct() -> None:
    from typing import ClassVar

    from app.shared.domain.request_models import PatchRequest

    class SamplePatch(PatchRequest):
        nullable_fields: ClassVar[frozenset[str]] = frozenset({"note"})
        label: str | None = None
        active: bool | None = None
        note: str | None = None

    assert SamplePatch().model_dump(exclude_unset=True) == {}
    assert SamplePatch(active=False).model_dump(exclude_unset=True) == {"active": False}
    assert SamplePatch(note=None).model_dump(exclude_unset=True) == {"note": None}
    for field in ("label", "active"):
        with pytest.raises(ValidationError):
            SamplePatch.model_validate({field: None})


def test_catalog_metadata_keeps_dotted_keys_but_rejects_unsafe_values() -> None:
    from app.shared.domain.request_models import StorageRequest

    class MetadataRequest(StorageRequest):
        metadata: dict[str, Any]

    value = MetadataRequest(metadata={"model.version": "✓"})
    assert value.metadata == {"model.version": "✓"}
    for bad in ("\x00", "\ud800", float("inf"), float("nan")):
        with pytest.raises(ValidationError):
            MetadataRequest(metadata={"model.version": bad})


def test_duplicate_translation_does_not_hide_other_database_errors() -> None:
    import asyncio
    from unittest.mock import AsyncMock

    from sqlalchemy.exc import IntegrityError

    from app.shared.database.constraints import flush_unique
    from app.shared.domain.errors import ConflictError

    class DatabaseFault(Exception):
        def __init__(self, sqlstate: str) -> None:
            self.sqlstate = sqlstate

    for state in ("23505", "23502"):
        original = IntegrityError("synthetic SQL", {}, DatabaseFault(state))
        session = AsyncMock()
        session.flush.side_effect = original
        expected = ConflictError if state == "23505" else IntegrityError
        with pytest.raises(expected):
            asyncio.run(flush_unique(session, "duplicate"))
        session.rollback.assert_awaited_once()

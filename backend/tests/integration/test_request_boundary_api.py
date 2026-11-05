"""API/database regressions: rejected writes are atomic; valid identifiers remain intact."""

import asyncio
import importlib.util
import json
import uuid
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from httpx import AsyncClient
from sqlalchemy import Connection, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.service import record_audit_event
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit
from tests.integration.test_strategy_management import _create_active_strategy


def body_for(endpoint: str) -> dict[str, Any]:
    code = f"BOUNDARY_{uuid.uuid4().hex[:12].upper()}"
    if endpoint == "features":
        return {
            "path": f"applicant.{code.lower()}",
            "label": "Boundary",
            "data_type": "STRING",
            "source": "PAYLOAD",
        }
    if endpoint == "models":
        return {
            "code": code,
            "version_label": "V1",
            "name": "Boundary",
            "metadata": {"valid": True},
        }
    if endpoint == "rule-categories":
        return {"code": code, "label": "Boundary"}
    return {
        "code": code,
        "category": "ELIGIBILITY",
        "severity": "DECLINE",
        "internal_message": "Boundary",
        "customer_message": "Clear this later",
    }


NULL_CASES = [
    (endpoint, field)
    for endpoint, fields in {
        "features": ("label", "description", "data_type", "category", "active", "writable"),
        "models": ("name", "provider", "description", "active", "metadata"),
        "rule-categories": ("label", "active"),
        "reason-codes": ("category", "severity", "internal_message", "active"),
    }.items()
    for field in fields
]


@pytest.mark.parametrize("endpoint,field", NULL_CASES)
async def test_null_patch_is_rejected_without_corrupting_catalog(
    db_client: AsyncClient, endpoint: str, field: str
) -> None:
    headers = await login(db_client, "admin")
    made = await db_client.post(f"/v1/{endpoint}", json=body_for(endpoint), headers=headers)
    assert made.status_code == 201, made.text
    original = made.json()
    rejected = await db_client.patch(
        f"/v1/{endpoint}/{original['id']}", json={field: None}, headers=headers
    )
    assert rejected.status_code == 422, rejected.text
    listed = await db_client.get(f"/v1/{endpoint}", headers=headers)
    assert listed.status_code == 200, listed.text
    current = next(row for row in listed.json() if row["id"] == original["id"])
    assert current == original
    empty = await db_client.patch(f"/v1/{endpoint}/{original['id']}", json={}, headers=headers)
    assert empty.status_code == 200 and empty.json() == original


@pytest.mark.parametrize(
    "endpoint,field,size",
    [
        ("features", "label", 201),
        ("features", "category", 51),
        ("models", "name", 201),
        ("models", "provider", 101),
        ("rule-categories", "label", 101),
    ],
)
async def test_oversized_patch_returns_422(
    db_client: AsyncClient, endpoint: str, field: str, size: int
) -> None:
    headers = await login(db_client, "admin")
    made = await db_client.post(f"/v1/{endpoint}", json=body_for(endpoint), headers=headers)
    assert made.status_code == 201, made.text
    rejected = await db_client.patch(
        f"/v1/{endpoint}/{made.json()['id']}", json={field: "x" * size}, headers=headers
    )
    assert rejected.status_code == 422, rejected.text


async def test_nullable_customer_message_can_be_cleared_and_audited(db_client: AsyncClient) -> None:
    headers = await login(db_client, "admin")
    payload = body_for("reason-codes")
    made = await db_client.post("/v1/reason-codes", json=payload, headers=headers)
    assert made.status_code == 201, made.text
    changed = await db_client.patch(
        f"/v1/reason-codes/{made.json()['id']}",
        json={"customer_message": None, "active": False},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["customer_message"] is None
    assert changed.json()["active"] is False
    assert changed.json()["internal_message"] == payload["internal_message"]
    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == payload["code"], AuditLog.event_type == "REASON_CODE_UPDATED"
            )
        )
        assert event is not None and event.after_value is not None
        assert event.before_value is not None
        assert event.before_value["customer_message"] == payload["customer_message"]
        assert event.after_value["customer_message"] is None


async def test_feature_allowed_values_can_still_be_cleared(db_client: AsyncClient) -> None:
    headers = await login(db_client, "admin")
    payload = {**body_for("features"), "allowed_values": ["YES", "NO"]}
    made = await db_client.post("/v1/features", json=payload, headers=headers)
    assert made.status_code == 201, made.text
    changed = await db_client.patch(
        f"/v1/features/{made.json()['id']}",
        json={"allowed_values": None, "active": False},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["allowed_values"] is None and changed.json()["active"] is False


@pytest.mark.parametrize("bad", ["\x00", "\ud800"])
async def test_invalid_json_strings_return_422_without_values_in_error(
    db_client: AsyncClient, bad: str
) -> None:
    headers = await login(db_client, "admin")
    payload = lease_back_motor_payload(applicant={"custom_note": "secret-marker" + bad})
    rejected = await db_client.post(
        "/v1/decisions",
        content=json.dumps(payload, ensure_ascii=True),
        headers={**headers, "Content-Type": "application/json"},
    )
    assert rejected.status_code == 422, rejected.text
    assert "secret-marker" not in rejected.text
    model = {**body_for("models"), "metadata": {"note": "secret-marker" + bad}}
    rejected_model = await db_client.post(
        "/v1/models",
        content=json.dumps(model, ensure_ascii=True),
        headers={**headers, "Content-Type": "application/json"},
    )
    assert rejected_model.status_code == 422, rejected_model.text
    assert "secret-marker" not in rejected_model.text


@pytest.mark.parametrize(
    "node_type,key,value",
    [
        ("VALIDATION", "required_fields", None),
        ("VALIDATION", "required_fields", [{}]),
        ("CALCULATION", "calculations", None),
    ],
)
async def test_malformed_graph_returns_422_not_500(
    db_client: AsyncClient, node_type: str, key: str, value: Any
) -> None:
    headers = await login(db_client, "admin")
    made = await db_client.post(
        "/v1/strategies",
        json={
            "strategy_code": f"BOUND_{uuid.uuid4().hex[:12].upper()}",
            "name": "Boundary",
            "product_type": "MOTOR_LEASEBACK",
        },
        headers=headers,
    )
    assert made.status_code == 201, made.text
    graph = {
        "nodes": [
            {"node_key": "s", "node_type": "START"},
            {"node_key": "n", "node_type": node_type, "config": {key: value}},
            {"node_key": "e", "node_type": "END"},
        ],
        "edges": [{"from": "s", "to": "n"}, {"from": "n", "to": "e"}],
    }
    rejected = await db_client.post(
        f"/v1/strategies/{made.json()['id']}/versions", json={"graph": graph}, headers=headers
    )
    assert rejected.status_code == 422, rejected.text
    detail = await db_client.get(f"/v1/strategies/{made.json()['id']}", headers=headers)
    assert detail.json()["versions"] == []


async def test_full_length_catalog_identifiers_are_not_truncated_in_audit(
    db_client: AsyncClient,
) -> None:
    headers = await login(db_client, "admin")
    code = "M" + uuid.uuid4().hex.upper() + "X" * 67
    version = "V" * 100
    path = "applicant.f" + uuid.uuid4().hex + "x" * 157
    assert len(code) == 100 and len(path) == 200
    model = await db_client.post(
        "/v1/models",
        json={"code": code, "version_label": version, "name": "Long identifier"},
        headers=headers,
    )
    feature = await db_client.post(
        "/v1/features",
        json={"path": path, "label": "Long path", "source": "PAYLOAD", "data_type": "STRING"},
        headers=headers,
    )
    assert model.status_code == 201, model.text
    assert feature.status_code == 201, feature.text
    async with get_sessionmaker()() as session:
        labels = (
            await session.scalars(
                select(AuditLog.entity_id).where(
                    AuditLog.entity_id.in_([f"{code}:{version}", path])
                )
            )
        ).all()
        assert set(labels) == {f"{code}:{version}", path}


async def test_full_length_strategy_executes_and_keeps_audit_version(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    code = "S" + uuid.uuid4().hex.upper() + "X" * 67
    segment = f"BOUND_{uuid.uuid4().hex[:12]}"
    await _create_active_strategy(
        db_client,
        analyst,
        manager,
        strategy_code=code,
        product_type="MOTOR_LEASEBACK",
        segment=segment,
    )
    response = await submit(db_client, lease_back_motor_payload(segment=segment))
    assert response.status_code == 201, response.text
    assert response.json()["strategy_version"] == f"{code}_V1"
    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.entity_id == response.json()["decision_id"],
                AuditLog.event_type == "DECISION_EXECUTED",
            )
        )
        assert event is not None and event.entity_version == f"{code}_V1"


@pytest.mark.parametrize("endpoint", ["models", "rule-categories", "reason-codes"])
async def test_concurrent_catalog_creates_return_one_201_and_one_409(
    db_client: AsyncClient, endpoint: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = await login(db_client, "admin")
    payload = body_for(endpoint)
    barrier = asyncio.Barrier(2)
    original_flush = AsyncSession.flush

    async def synchronized_flush(self: AsyncSession, objects: Sequence[Any] | None = None) -> None:
        if any(getattr(obj, "code", None) == payload["code"] for obj in self.new):
            await asyncio.wait_for(barrier.wait(), timeout=10)
        await original_flush(self, objects)

    monkeypatch.setattr(AsyncSession, "flush", synchronized_flush)
    results = await asyncio.gather(
        *[db_client.post(f"/v1/{endpoint}", json=payload, headers=headers) for _ in range(2)]
    )
    assert sorted(result.status_code for result in results) == [201, 409], [r.text for r in results]
    rows = await db_client.get(f"/v1/{endpoint}", headers=headers)
    assert rows.status_code == 200
    assert sum(row["code"] == payload["code"] for row in rows.json()) == 1


async def test_audit_downgrade_refuses_to_truncate_evidence(database: None) -> None:
    path = Path("alembic/versions/d7a4c192e605_audit_identifier_capacity.py")
    spec = importlib.util.spec_from_file_location("audit_identifier_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    async with get_sessionmaker()() as session:
        event = record_audit_event(
            session,
            event_type="TEST_CAPACITY",
            entity_type="TEST",
            entity_id="X" * 200,
            entity_version="V" * 100,
            action="VERIFY",
        )
        await session.flush()
        connection = await session.connection()

        def attempt_downgrade(sync_connection: Connection) -> None:
            with Operations.context(MigrationContext.configure(sync_connection)):
                with pytest.raises(RuntimeError, match="Cannot narrow audit identifiers"):
                    module.downgrade()

        await connection.run_sync(attempt_downgrade)
        assert event.entity_id == "X" * 200
        await session.rollback()

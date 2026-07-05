"""Model registry + dashboard trend tests (P2.5)."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


async def test_registry_seeded_and_listable(db_client: AsyncClient) -> None:
    scientist = await login(db_client, "datascientist")
    models = (await db_client.get("/v1/models", headers=scientist)).json()
    seeded = next(m for m in models if m["code"] == "MOTOR_SCORE" and m["version_label"] == "V1")
    assert seeded["provider"] == "INTERNAL"
    assert seeded["active"] is True
    assert seeded["metadata"]["payload_version_token"] == "MOTOR_SCORE_V1"


async def test_register_and_update_model_with_audit(db_client: AsyncClient) -> None:
    scientist = await login(db_client, "datascientist")
    code = f"TEST_MODEL_{uuid.uuid4().hex[:6].upper()}"
    created = await db_client.post(
        "/v1/models",
        json={
            "code": code,
            "version_label": "V2",
            "name": "Challenger score",
            "provider": "VENDOR_X",
            "description": "Challenger candidate",
            "metadata": {"auc": 0.78},
        },
        headers=scientist,
    )
    assert created.status_code == 201, created.text

    duplicate = await db_client.post(
        "/v1/models",
        json={"code": code, "version_label": "V2", "name": "dup"},
        headers=scientist,
    )
    assert duplicate.status_code == 409

    retired = await db_client.patch(
        f"/v1/models/{created.json()['id']}", json={"active": False}, headers=scientist
    )
    assert retired.status_code == 200
    assert retired.json()["active"] is False

    async with get_sessionmaker()() as session:
        events = (
            await session.scalars(select(AuditLog).where(AuditLog.entity_id == f"{code}:V2"))
        ).all()
    assert {e.event_type for e in events} == {"MODEL_REGISTERED", "MODEL_UPDATED"}


async def test_registry_permissions(db_client: AsyncClient) -> None:
    underwriter = await login(db_client, "underwriter")
    assert (await db_client.get("/v1/models", headers=underwriter)).status_code == 403

    # Data scientist can view but let's confirm an analyst (view only) cannot manage.
    analyst = await login(db_client, "riskanalyst")
    assert (await db_client.get("/v1/models", headers=analyst)).status_code == 200
    denied = await db_client.post(
        "/v1/models",
        json={"code": "X_DENY", "version_label": "V1", "name": "x"},
        headers=analyst,
    )
    assert denied.status_code == 403


async def test_decision_trend_buckets(db_client: AsyncClient) -> None:
    channel = "TREND_TEST"
    await submit(db_client, lease_back_motor_payload(channel=channel))
    await submit(
        db_client, lease_back_motor_payload(channel=channel, fraud={"blacklist_hit": True})
    )

    manager = await login(db_client, "riskmanager")
    response = await db_client.get(
        "/v1/monitoring/decision-trend", params={"channel": channel}, headers=manager
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interval"] == "day"
    assert len(body["buckets"]) >= 1
    total = sum(b["total"] for b in body["buckets"])
    assert total == 2
    all_counts: dict[str, int] = {}
    for b in body["buckets"]:
        for decision, count in b["decision_counts"].items():
            all_counts[decision] = all_counts.get(decision, 0) + count
    assert all_counts.get("REJECT") == 1
    assert all_counts.get("APPROVE_WITH_CONDITION") == 1


async def test_trend_requires_permission(db_client: AsyncClient) -> None:
    los = await login(db_client, "los-client")
    assert (await db_client.get("/v1/monitoring/decision-trend", headers=los)).status_code == 403

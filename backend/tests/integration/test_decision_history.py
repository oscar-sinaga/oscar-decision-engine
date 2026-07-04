"""Decision history search tests (docs/02 §6.6, screen spec §2)."""

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


async def test_history_filters_and_pagination(db_client: AsyncClient) -> None:
    approved = (await submit(db_client, lease_back_motor_payload(channel="HISTORY_TEST"))).json()
    rejected = (
        await submit(
            db_client,
            lease_back_motor_payload(channel="HISTORY_TEST", fraud={"blacklist_hit": True}),
        )
    ).json()

    analyst = await login(db_client, "riskanalyst")

    by_channel = await db_client.get(
        "/v1/decisions", params={"channel": "HISTORY_TEST"}, headers=analyst
    )
    assert by_channel.status_code == 200
    body = by_channel.json()
    assert body["total"] >= 2
    ids = {item["decision_id"] for item in body["items"]}
    assert {approved["decision_id"], rejected["decision_id"]} <= ids

    by_decision = await db_client.get(
        "/v1/decisions",
        params={"channel": "HISTORY_TEST", "decision": "REJECT"},
        headers=analyst,
    )
    reject_items = by_decision.json()["items"]
    assert all(item["decision"] == "REJECT" for item in reject_items)
    assert any(item["decision_id"] == rejected["decision_id"] for item in reject_items)
    assert reject_items[0]["reason_codes"] == ["BLACKLIST_HIT"]

    by_application = await db_client.get(
        "/v1/decisions",
        params={"application_id": approved["application_id"]},
        headers=analyst,
    )
    assert by_application.json()["total"] == 1

    paged = await db_client.get(
        "/v1/decisions",
        params={"channel": "HISTORY_TEST", "page_size": 1, "page": 1},
        headers=analyst,
    )
    assert len(paged.json()["items"]) == 1
    assert paged.json()["total"] >= 2

    ordering = [item["created_at"] for item in body["items"]]
    assert ordering == sorted(ordering, reverse=True)


async def test_history_requires_permission(db_client: AsyncClient) -> None:
    anonymous = await db_client.get("/v1/decisions")
    assert anonymous.status_code == 401


async def test_trace_view_is_audited(db_client: AsyncClient) -> None:
    created = (await submit(db_client, lease_back_motor_payload())).json()
    compliance = await login(db_client, "compliance")
    trace = await db_client.get(f"/v1/decisions/{created['decision_id']}/trace", headers=compliance)
    assert trace.status_code == 200

    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "DECISION_TRACE_VIEWED",
                AuditLog.entity_id == created["trace_id"],
            )
        )
    assert event is not None
    assert event.actor_label == "compliance"
    assert event.metadata_json["decision_id"] == created["decision_id"]

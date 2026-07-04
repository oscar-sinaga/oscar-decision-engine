"""Monitoring metrics tests (docs/07 §9, Epic 9)."""

from httpx import AsyncClient

from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


async def test_decision_summary_metrics(db_client: AsyncClient) -> None:
    channel = "MONITORING_TEST"
    await submit(db_client, lease_back_motor_payload(channel=channel))  # conditional approval
    await submit(
        db_client, lease_back_motor_payload(channel=channel, fraud={"blacklist_hit": True})
    )  # reject
    await submit(
        db_client,
        lease_back_motor_payload(channel=channel, applicant={"monthly_income": 7_440_000}),
    )  # manual review

    manager = await login(db_client, "riskmanager")
    response = await db_client.get(
        "/v1/monitoring/decision-summary", params={"channel": channel}, headers=manager
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["total_applications"] == 3
    assert body["decision_counts"] == {
        "APPROVE_WITH_CONDITION": 1,
        "REJECT": 1,
        "MANUAL_REVIEW": 1,
    }
    assert abs(body["approval_rate"] - 1 / 3) < 0.001
    assert abs(body["reject_rate"] - 1 / 3) < 0.001
    assert abs(body["manual_review_rate"] - 1 / 3) < 0.001
    assert body["error_rate"] == 0.0

    top_codes = {item["code"] for item in body["top_reason_codes"]}
    assert {"REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT", "BLACKLIST_HIT", "DTI_NEAR_THRESHOLD"} <= (
        top_codes
    )
    assert body["api_latency_p95_ms"] is not None
    assert body["manual_review_queue_size"] >= 1


async def test_summary_product_filter_and_empty_window(db_client: AsyncClient) -> None:
    manager = await login(db_client, "riskmanager")
    response = await db_client.get(
        "/v1/monitoring/decision-summary",
        params={"channel": "NO_SUCH_CHANNEL"},
        headers=manager,
    )
    body = response.json()
    assert body["total_applications"] == 0
    assert body["approval_rate"] == 0.0
    assert body["top_reason_codes"] == []


async def test_monitoring_requires_permission(db_client: AsyncClient) -> None:
    los = await login(db_client, "los-client")
    denied = await db_client.get("/v1/monitoring/decision-summary", headers=los)
    assert denied.status_code == 403

    underwriter = await login(db_client, "underwriter")
    also_denied = await db_client.get("/v1/monitoring/decision-summary", headers=underwriter)
    assert also_denied.status_code == 403

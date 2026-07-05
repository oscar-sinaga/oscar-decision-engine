"""Batch simulation / policy impact analysis tests (Phase 2, docs/12 §7)."""

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.modules.decisions.models import Application, Decision
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload


async def _active_leaseback_version_id(client: AsyncClient, analyst: dict[str, str]) -> str:
    strategies = (await client.get("/v1/strategies", headers=analyst)).json()
    leaseback = next(s for s in strategies if s["strategy_code"] == "LEASEBACK_MOTOR")
    detail = (await client.get(f"/v1/strategies/{leaseback['id']}", headers=analyst)).json()
    active = next(v for v in detail["versions"] if v["status"] == "ACTIVE")
    version_id: str = active["id"]
    return version_id


def _population() -> list[dict[str, object]]:
    return [
        lease_back_motor_payload(),  # conditional approval
        lease_back_motor_payload(fraud={"blacklist_hit": True}),  # reject
        lease_back_motor_payload(applicant={"monthly_income": 7_440_000}),  # manual review
        lease_back_motor_payload(fraud={"identity_match": False}),  # fraud investigation
    ]


async def test_batch_aggregates_population(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    version_id = await _active_leaseback_version_id(db_client, analyst)

    before_apps, before_decisions = await _counts()
    response = await db_client.post(
        "/v1/simulations/batch",
        json={
            "simulation_name": "Population impact",
            "strategy_version_id": version_id,
            "application_payloads": _population(),
            "compare_with_active": False,
        },
        headers=analyst,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["mode"] == "SIMULATION"
    assert body["total_records"] == 4
    counts = body["target"]["decision_counts"]
    assert counts.get("APPROVE_WITH_CONDITION") == 1
    assert counts.get("REJECT") == 1
    assert counts.get("MANUAL_REVIEW") == 1
    assert counts.get("FRAUD_INVESTIGATION") == 1
    assert abs(body["target"]["approval_rate"] - 0.25) < 0.001
    assert "BLACKLIST_HIT" in body["target"]["reason_code_distribution"]
    assert body["target"]["risk_grade_distribution"].get("B", 0) >= 1

    # No production rows created.
    after_apps, after_decisions = await _counts()
    assert (after_apps, after_decisions) == (before_apps, before_decisions)


async def _counts() -> tuple[int, int]:
    async with get_sessionmaker()() as session:
        apps = await session.scalar(select(func.count()).select_from(Application))
        decisions = await session.scalar(select(func.count()).select_from(Decision))
    return apps or 0, decisions or 0


async def test_batch_compares_against_active_and_reports_shifts(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")

    # Candidate draft v2: no final decision table → conservative MANUAL_REVIEW
    # for everything that isn't hard-stopped, so we get visible decision shifts.
    strategies = (await db_client.get("/v1/strategies", headers=analyst)).json()
    leaseback = next(s for s in strategies if s["strategy_code"] == "LEASEBACK_MOTOR")
    draft = await db_client.post(
        f"/v1/strategies/{leaseback['id']}/versions",
        json={
            "version_note": "candidate without approval path",
            "steps": [
                {
                    "order": 1,
                    "type": "CALCULATION",
                    "config": {"calculations": ["loan.ltv", "affordability.dti"]},
                },
                {"order": 2, "type": "RULE_SET", "reference_code": "AFFORDABILITY_STANDARD"},
            ],
        },
        headers=analyst,
    )
    assert draft.status_code == 201, draft.text
    candidate_id = draft.json()["id"]

    try:
        response = await db_client.post(
            "/v1/simulations/batch",
            json={
                "strategy_version_id": candidate_id,
                "application_payloads": _population(),
                "compare_with_active": True,
            },
            headers=analyst,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["active"] is not None
        assert body["active"]["strategy_version"] == "ACTIVE"
        # The candidate turns approvals/rejects into manual reviews → shifts recorded.
        assert len(body["decision_shifts"]) > 0
        assert all(s["from_decision"] != s["to_decision"] for s in body["decision_shifts"])
        assert body["segment_impact"][0]["active_decision_counts"] is not None
    finally:
        await db_client.post(
            f"/v1/strategies/{leaseback['id']}/versions/{candidate_id}/submit-approval",
            headers=analyst,
        )
        await db_client.post(
            f"/v1/strategies/{leaseback['id']}/versions/{candidate_id}/reject",
            json={"reason": "test cleanup"},
            headers=manager,
        )


async def test_batch_requires_permission_and_valid_version(db_client: AsyncClient) -> None:
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.post(
        "/v1/simulations/batch",
        json={"strategy_version_id": str(uuid.uuid4()), "application_payloads": _population()},
        headers=underwriter,
    )
    assert denied.status_code == 403

    analyst = await login(db_client, "riskanalyst")
    missing = await db_client.post(
        "/v1/simulations/batch",
        json={"strategy_version_id": str(uuid.uuid4()), "application_payloads": _population()},
        headers=analyst,
    )
    assert missing.status_code == 404

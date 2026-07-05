"""Simulation tests: side-effect freedom, comparison, permissions (docs/12)."""

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.modules.audit.models import AuditLog
from app.modules.decisions.models import Application, Decision, DecisionTrace
from app.modules.manual_review.models import ManualReviewCase
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload


async def _production_row_counts() -> tuple[int, int, int, int]:
    async with get_sessionmaker()() as session:
        applications = await session.scalar(select(func.count()).select_from(Application))
        decisions = await session.scalar(select(func.count()).select_from(Decision))
        traces = await session.scalar(select(func.count()).select_from(DecisionTrace))
        cases = await session.scalar(select(func.count()).select_from(ManualReviewCase))
    return applications or 0, decisions or 0, traces or 0, cases or 0


async def test_simulation_creates_no_production_side_effects(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    before = await _production_row_counts()

    response = await db_client.post(
        "/v1/simulations/single",
        json={
            "simulation_name": "Baseline motor payload",
            "application_payload": lease_back_motor_payload(),
        },
        headers=analyst,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["mode"] == "SIMULATION"
    assert body["simulation_id"].startswith("SIM-")
    assert body["draft_result"]["decision"] == "APPROVE_WITH_CONDITION"
    assert body["draft_result"]["strategy_version"] == "LEASEBACK_MOTOR_V1"
    assert body["active_result"] is None

    after = await _production_row_counts()
    assert after == before  # no application/decision/trace/case rows created

    # Simulation record persisted, marked as simulation, and audited.
    detail = (
        await db_client.get(f"/v1/simulations/{body['simulation_id']}", headers=analyst)
    ).json()
    assert detail["status"] == "COMPLETED"
    assert detail["trace"]["draft_trace"]["execution_mode"] == "SIMULATION"
    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "SIMULATION_EXECUTED",
                AuditLog.entity_id == body["simulation_id"],
            )
        )
    assert event is not None


async def test_simulation_compares_draft_against_active(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")

    # Draft strategy v2 for MOTOR_LEASEBACK without the final decision table:
    # the engine's conservative fallback produces MANUAL_REVIEW.
    strategies = (await db_client.get("/v1/strategies", headers=analyst)).json()
    leaseback = next(s for s in strategies if s["strategy_code"] == "LEASEBACK_MOTOR")
    draft = await db_client.post(
        f"/v1/strategies/{leaseback['id']}/versions",
        json={
            "version_note": "draft without approval path",
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
    draft_id = draft.json()["id"]
    draft_version = draft.json()["version"]

    try:
        response = await db_client.post(
            "/v1/simulations/single",
            json={
                "simulation_name": "Active vs draft",
                "application_payload": lease_back_motor_payload(),
                "strategy_version_id": draft_id,
                "compare_with_active": True,
            },
            headers=analyst,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["draft_result"]["strategy_version"] == f"LEASEBACK_MOTOR_V{draft_version}"
        assert body["draft_result"]["decision"] == "MANUAL_REVIEW"
        assert body["active_result"]["strategy_version"] == "LEASEBACK_MOTOR_V1"
        assert body["active_result"]["decision"] == "APPROVE_WITH_CONDITION"
        decision_diff = next(d for d in body["differences"] if d["field"] == "decision")
        assert decision_diff == {
            "field": "decision",
            "active": "APPROVE_WITH_CONDITION",
            "draft": "MANUAL_REVIEW",
        }
    finally:
        # Remove the draft so other tests see the seeded strategy untouched.
        manager = await login(db_client, "riskmanager")
        await db_client.post(
            f"/v1/strategies/{leaseback['id']}/versions/{draft_id}/submit-approval",
            headers=analyst,
        )
        await db_client.post(
            f"/v1/strategies/{leaseback['id']}/versions/{draft_id}/reject",
            json={"reason": "test cleanup"},
            headers=manager,
        )


async def test_simulation_with_validation_failure_reports_error_result(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    payload = lease_back_motor_payload()
    del payload["vehicle"]["appraisal_value"]
    response = await db_client.post(
        "/v1/simulations/single",
        json={"application_payload": payload},
        headers=analyst,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["draft_result"]["decision"] == "ERROR"
    assert body["draft_result"]["validation_failures"][0]["field"] == "vehicle.appraisal_value"


async def test_simulation_requires_permission(db_client: AsyncClient) -> None:
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.post(
        "/v1/simulations/single",
        json={"application_payload": lease_back_motor_payload()},
        headers=underwriter,
    )
    assert denied.status_code == 403


async def test_simulation_unknown_strategy_version(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    response = await db_client.post(
        "/v1/simulations/single",
        json={
            "application_payload": lease_back_motor_payload(),
            "strategy_version_id": str(uuid.uuid4()),
        },
        headers=analyst,
    )
    assert response.status_code == 404

"""Strategy management tests (Epic 4, docs/14 §8)."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit

VALID_STEPS: list[dict[str, Any]] = [
    {
        "order": 1,
        "type": "VALIDATION",
        "name": "Required Fields",
        "config": {"required_fields": ["loan.requested_amount", "vehicle.appraisal_value"]},
    },
    {
        "order": 2,
        "type": "CALCULATION",
        "name": "Derived",
        "config": {"calculations": ["loan.ltv", "affordability.dti"]},
    },
    {
        "order": 3,
        "type": "RULE_SET",
        "name": "Affordability",
        "reference_code": "AFFORDABILITY_STANDARD",
    },
    {"order": 4, "type": "SCORECARD", "name": "Score", "reference_code": "MOTOR_SCORECARD"},
    {
        "order": 5,
        "type": "DECISION_TABLE",
        "name": "Final",
        "reference_code": "FINAL_DECISION_MOTOR",
    },
]


def _strategy_body(**overrides: Any) -> dict[str, Any]:
    body = {
        "strategy_code": f"TEST_STRAT_{uuid.uuid4().hex[:6].upper()}",
        "name": "Test strategy",
        "product_type": "AUTO_LOAN_MOTOR",
        "segment": f"SEG_{uuid.uuid4().hex[:6].upper()}",
    }
    body.update(overrides)
    return body


async def _create_active_strategy(
    client: AsyncClient,
    analyst: dict[str, str],
    manager: dict[str, str],
    **overrides: Any,
) -> tuple[str, str]:
    """Create a strategy with VALID_STEPS and activate v1. Returns (strategy_id, version_id)."""
    strategy = (
        await client.post("/v1/strategies", json=_strategy_body(**overrides), headers=analyst)
    ).json()
    version = (
        await client.post(
            f"/v1/strategies/{strategy['id']}/versions",
            json={"version_note": "v1", "steps": VALID_STEPS},
            headers=analyst,
        )
    ).json()
    await client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/submit-approval",
        headers=analyst,
    )
    activated = await client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        json={"reason": "initial activation"},
        headers=manager,
    )
    assert activated.status_code == 200, activated.text
    return strategy["id"], version["id"]


async def test_strategy_lifecycle(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")

    strategy_id, version_id = await _create_active_strategy(db_client, analyst, manager)

    detail = (await db_client.get(f"/v1/strategies/{strategy_id}", headers=analyst)).json()
    assert detail["active_version"] == 1
    assert [s["order"] for s in detail["versions"][0]["steps"]] == [1, 2, 3, 4, 5]

    # Active version is immutable.
    frozen = await db_client.put(
        f"/v1/strategies/{strategy_id}/versions/{version_id}",
        json={"version_note": "x", "steps": VALID_STEPS},
        headers=analyst,
    )
    assert frozen.status_code == 409


async def test_step_validation_rejects_unknown_references(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    strategy = (
        await db_client.post("/v1/strategies", json=_strategy_body(), headers=analyst)
    ).json()

    bad_ruleset = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={"steps": [{"order": 1, "type": "RULE_SET", "reference_code": "NOT_A_RULE_SET"}]},
        headers=analyst,
    )
    assert bad_ruleset.status_code == 422

    bad_calc = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={
            "steps": [
                {"order": 1, "type": "CALCULATION", "config": {"calculations": ["loan.magic"]}}
            ]
        },
        headers=analyst,
    )
    assert bad_calc.status_code == 422

    duplicate_order = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={
            "steps": [
                {"order": 1, "type": "RULE_SET", "reference_code": "FRAUD_BASIC"},
                {"order": 1, "type": "RULE_SET", "reference_code": "ELIGIBILITY_MOTOR"},
            ]
        },
        headers=analyst,
    )
    assert duplicate_order.status_code == 422


async def test_underwriter_cannot_activate_strategy(db_client: AsyncClient) -> None:
    """PRD §6.11 acceptance criterion."""
    analyst = await login(db_client, "riskanalyst")
    underwriter = await login(db_client, "underwriter")
    strategy = (
        await db_client.post("/v1/strategies", json=_strategy_body(), headers=analyst)
    ).json()
    version = (
        await db_client.post(
            f"/v1/strategies/{strategy['id']}/versions",
            json={"steps": VALID_STEPS},
            headers=analyst,
        )
    ).json()
    await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/submit-approval",
        headers=analyst,
    )
    denied = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        json={"reason": "x"},
        headers=underwriter,
    )
    assert denied.status_code == 403


async def test_single_active_strategy_per_product_segment(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    segment = f"SEG_{uuid.uuid4().hex[:6].upper()}"

    first_id, _ = await _create_active_strategy(db_client, analyst, manager, segment=segment)
    second_id, _ = await _create_active_strategy(db_client, analyst, manager, segment=segment)

    first = (await db_client.get(f"/v1/strategies/{first_id}", headers=analyst)).json()
    second = (await db_client.get(f"/v1/strategies/{second_id}", headers=analyst)).json()
    assert first["active_version"] is None  # retired by the competing activation
    assert first["versions"][0]["status"] == "RETIRED"
    assert second["active_version"] == 1


async def test_new_version_and_rollback(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    strategy_id, v1_id = await _create_active_strategy(db_client, analyst, manager)

    # v2 with a reduced step list.
    v2 = (
        await db_client.post(
            f"/v1/strategies/{strategy_id}/versions",
            json={"version_note": "v2 tighter", "steps": VALID_STEPS[:4] + [VALID_STEPS[4]]},
            headers=analyst,
        )
    ).json()
    await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{v2['id']}/submit-approval", headers=analyst
    )
    await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{v2['id']}/activate",
        json={"reason": "v2 live"},
        headers=manager,
    )
    detail = (await db_client.get(f"/v1/strategies/{strategy_id}", headers=analyst)).json()
    statuses = {v["version"]: v["status"] for v in detail["versions"]}
    assert statuses == {1: "RETIRED", 2: "ACTIVE"}

    # Rollback requires a reason.
    missing_reason = await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{v1_id}/rollback",
        json={"reason": "  "},
        headers=manager,
    )
    assert missing_reason.status_code == 422

    rolled_back = await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{v1_id}/rollback",
        json={"reason": "v2 caused approval-rate drop"},
        headers=manager,
    )
    assert rolled_back.status_code == 200
    detail = (await db_client.get(f"/v1/strategies/{strategy_id}", headers=analyst)).json()
    statuses = {v["version"]: v["status"] for v in detail["versions"]}
    assert statuses == {1: "ACTIVE", 2: "RETIRED"}

    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "STRATEGY_ROLLED_BACK",
                AuditLog.entity_id == detail["strategy_code"],
            )
        )
    assert event is not None
    assert event.reason == "v2 caused approval-rate drop"
    assert event.actor_label == "riskmanager"


async def test_runtime_uses_api_created_strategy(db_client: AsyncClient) -> None:
    """A CAR_LEASEBACK strategy created via the API serves decisions end-to-end."""
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    await _create_active_strategy(
        db_client,
        analyst,
        manager,
        strategy_code=f"LEASEBACK_CAR_{uuid.uuid4().hex[:4].upper()}",
        product_type="CAR_LEASEBACK",
        segment="DEFAULT",
    )

    payload = lease_back_motor_payload(product_type="CAR_LEASEBACK")
    response = await submit(db_client, payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "APPROVE_WITH_CONDITION"
    assert body["strategy_version"].endswith("_V1")


async def test_activation_requires_active_referenced_configs(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")

    # A scorecard whose only version stays DRAFT.
    scorecard = (
        await db_client.post(
            "/v1/scorecards",
            json={
                "code": f"DRAFT_SC_{uuid.uuid4().hex[:6].upper()}",
                "name": "Draft only",
                "config": {"bands": [{"min_score": 0, "risk_grade": "A"}]},
            },
            headers=analyst,
        )
    ).json()

    strategy = (
        await db_client.post("/v1/strategies", json=_strategy_body(), headers=analyst)
    ).json()
    version = (
        await db_client.post(
            f"/v1/strategies/{strategy['id']}/versions",
            json={
                "steps": [
                    {"order": 1, "type": "SCORECARD", "reference_code": scorecard["code"]},
                    {
                        "order": 2,
                        "type": "DECISION_TABLE",
                        "reference_code": "FINAL_DECISION_MOTOR",
                    },
                ]
            },
            headers=analyst,
        )
    ).json()
    await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/submit-approval",
        headers=analyst,
    )
    blocked = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        json={"reason": "should fail"},
        headers=manager,
    )
    assert blocked.status_code == 422
    assert "no active version" in blocked.text


async def test_rule_set_management(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    code = f"TEST_RS_{uuid.uuid4().hex[:6].upper()}"

    created = await db_client.post(
        "/v1/rule-sets",
        json={"code": code, "name": "Test set", "rule_codes": ["DTI_MAX_STANDARD"]},
        headers=analyst,
    )
    assert created.status_code == 201, created.text
    assert created.json()["rule_codes"] == ["DTI_MAX_STANDARD"]

    unknown = await db_client.post(
        "/v1/rule-sets",
        json={"code": f"X_{code}", "name": "Bad", "rule_codes": ["NOT_A_RULE"]},
        headers=analyst,
    )
    assert unknown.status_code == 422

    updated = await db_client.put(
        f"/v1/rule-sets/{created.json()['id']}/members",
        json={"rule_codes": ["DTI_MAX_STANDARD", "BUREAU_DPD_MAX"]},
        headers=analyst,
    )
    assert updated.status_code == 200
    assert updated.json()["rule_codes"] == ["DTI_MAX_STANDARD", "BUREAU_DPD_MAX"]

    async with get_sessionmaker()() as session:
        events = (await session.scalars(select(AuditLog).where(AuditLog.entity_id == code))).all()
    assert {e.event_type for e in events} == {"RULE_SET_CREATED", "RULE_SET_MEMBERS_UPDATED"}

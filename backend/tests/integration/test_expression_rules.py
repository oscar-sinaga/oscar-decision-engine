"""Phase 3 safe-expression API, permissions, and decision integration tests."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit
from tests.integration.test_strategy_management import VALID_STEPS, submit_with_simulation


def _expression_rule_payload(code: str) -> dict[str, Any]:
    return {
        "rule_code": code,
        "name": "Computed eligible limit",
        "category": "LIMIT",
        "rule_kind": "EXPRESSION",
        "expression": "loan.requested_amount * 0.5",
        "output_target": "outputs.eligible_limit",
        "version_note": "Safe expression integration test",
    }


async def test_expression_validation_is_admin_only(db_client: AsyncClient) -> None:
    admin = await login(db_client, "admin")
    analyst = await login(db_client, "riskanalyst")
    body = {
        "expression": "COALESCE(bureau.max_dpd_12m, 999) <= 30",
        "expects": "boolean",
    }

    denied = await db_client.post("/v1/expressions/validate", json=body, headers=analyst)
    allowed = await db_client.post("/v1/expressions/validate", json=body, headers=admin)

    assert denied.status_code == 403
    assert allowed.status_code == 200, allowed.text
    result = allowed.json()
    assert result["valid"] is True
    assert result["inferred_type"] == "BOOLEAN"
    assert result["referenced_features"] == ["bureau.max_dpd_12m"]
    assert result["ast_node_count"] > 0


async def test_expression_rule_authoring_preview_and_dry_run(db_client: AsyncClient) -> None:
    admin = await login(db_client, "admin")
    analyst = await login(db_client, "riskanalyst")
    code = f"EXPR_{uuid.uuid4().hex[:8].upper()}"
    payload = _expression_rule_payload(code)

    denied = await db_client.post("/v1/rules", json=payload, headers=analyst)
    created = await db_client.post("/v1/rules", json=payload, headers=admin)

    assert denied.status_code == 403
    assert created.status_code == 201, created.text
    rule = created.json()
    version = rule["versions"][0]
    assert version["rule_kind"] == "EXPRESSION"
    assert version["expression"] == payload["expression"]
    assert version["output_target"] == payload["output_target"]
    assert "OSCAR" not in version["sql_preview"]
    assert "-- writes outputs.eligible_limit" in version["sql_preview"]
    assert version["branches"] == []

    tested = await db_client.post(
        f"/v1/rules/{rule['id']}/versions/{version['id']}/test",
        json={"features": {"loan.requested_amount": 20_000_000}},
        headers=analyst,
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["outputs_after"] == {"outputs.eligible_limit": 10_000_000}


async def test_set_output_expression_is_admin_gated_and_executes_in_order(
    db_client: AsyncClient,
) -> None:
    admin = await login(db_client, "admin")
    analyst = await login(db_client, "riskanalyst")
    payload = {
        "rule_code": f"ACTION_EXPR_{uuid.uuid4().hex[:8].upper()}",
        "name": "Action expression",
        "category": "LIMIT",
        "rule_kind": "STATEMENT",
        "branches": [
            {
                "when": {"all": [{"field": "loan.requested_amount", "operator": ">", "value": 0}]},
                "then": [
                    {
                        "type": "SET_OUTPUT",
                        "target": "outputs.eligible_limit",
                        "expression": "loan.requested_amount * 0.4",
                    },
                    {
                        "type": "SET_OUTPUT",
                        "target": "outputs.vehicle_price_band",
                        "expression": "outputs.eligible_limit / 1000",
                    },
                ],
            }
        ],
    }

    denied = await db_client.post("/v1/rules", json=payload, headers=analyst)
    created = await db_client.post("/v1/rules", json=payload, headers=admin)

    assert denied.status_code == 403
    assert created.status_code == 201, created.text
    rule = created.json()
    version = rule["versions"][0]
    tested = await db_client.post(
        f"/v1/rules/{rule['id']}/versions/{version['id']}/test",
        json={"features": {"loan.requested_amount": 20_000_000}},
        headers=analyst,
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["outputs_after"] == {
        "outputs.eligible_limit": 8_000_000,
        "outputs.vehicle_price_band": 8_000,
    }


async def test_active_expression_rule_executes_inside_decision_strategy(
    db_client: AsyncClient,
) -> None:
    admin = await login(db_client, "admin")
    manager = await login(db_client, "riskmanager")
    analyst = await login(db_client, "riskanalyst")
    code = f"DECISION_EXPR_{uuid.uuid4().hex[:8].upper()}"

    created = await db_client.post("/v1/rules", json=_expression_rule_payload(code), headers=admin)
    assert created.status_code == 201, created.text
    rule = created.json()
    version = rule["versions"][0]
    await db_client.post(
        f"/v1/rules/{rule['id']}/versions/{version['id']}/submit-approval",
        headers=admin,
    )
    activated = await db_client.post(
        f"/v1/rules/{rule['id']}/versions/{version['id']}/activate",
        json={"reason": "integration test"},
        headers=manager,
    )
    assert activated.status_code == 200, activated.text

    # Published sets are immutable: build an isolated governed policy instead of mutating seed.
    set_code = f"EXPR_SET_{uuid.uuid4().hex[:8].upper()}"
    created_set = await db_client.post(
        "/v1/rule-sets",
        headers=admin,
        json={
            "code": set_code,
            "name": "Expression test",
            "rule_codes": ["DTI_MAX_STANDARD", code],
        },
    )
    assert created_set.status_code == 201, created_set.text
    segment = f"EXPR_SEG_{uuid.uuid4().hex[:8].upper()}"
    strategy = await db_client.post(
        "/v1/strategies",
        headers=admin,
        json={
            "strategy_code": segment,
            "name": "Expression policy",
            "product_type": "MOTOR_LEASEBACK",
            "segment": segment,
        },
    )
    assert strategy.status_code == 201, strategy.text
    steps = [
        {**step, "reference_code": set_code}
        if step.get("reference_code") == "AFFORDABILITY_STANDARD"
        else step
        for step in VALID_STEPS
    ]
    draft = await db_client.post(
        f"/v1/strategies/{strategy.json()['id']}/versions", headers=admin, json={"steps": steps}
    )
    assert draft.status_code == 201, draft.text
    await submit_with_simulation(db_client, admin, strategy.json()["id"], draft.json()["id"])
    active = await db_client.post(
        f"/v1/strategies/{strategy.json()['id']}/versions/{draft.json()['id']}/activate",
        headers=manager,
        json={"reason": "Independent test approval"},
    )
    assert active.status_code == 200, active.text
    decision = await submit(db_client, lease_back_motor_payload(segment=segment))
    assert decision.status_code == 201, decision.text
    trace = await db_client.get(
        f"/v1/decisions/{decision.json()['decision_id']}/trace", headers=analyst
    )
    assert trace.status_code == 200, trace.text
    body = trace.json()
    assert body["feature_values"]["outputs.eligible_limit"] == 7_500_000
    matching = [
        result
        for step in body["steps"]
        for result in step.get("rule_results", [])
        if result.get("rule_code") == code
    ]
    assert matching and matching[0]["matched_branch"] == "expression"

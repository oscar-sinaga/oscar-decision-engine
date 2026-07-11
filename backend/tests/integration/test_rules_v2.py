"""Phase 3 rule-v2 API contract tests."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login


def _branch_payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "rule_code": f"V2_RULE_{uuid.uuid4().hex[:8].upper()}",
        "name": "Vehicle type classification",
        "category": "COLLATERAL",
        "rule_kind": "CLASSIFICATION",
        "branches": [
            {
                "when": {"all": [{"field": "vehicle.age_years", "operator": ">", "value": 10}]},
                "then": [{"type": "SET_OUTPUT", "target": "loan.ltv", "value": 0.95}],
            }
        ],
        "default": [{"type": "SET_OUTPUT", "target": "loan.ltv", "value": 0.8}],
    }
    body.update(overrides)
    return body


async def test_create_v2_rule_persists_normalized_body(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")

    response = await db_client.post("/v1/rules", json=_branch_payload(), headers=analyst)

    assert response.status_code == 201, response.text
    version = response.json()["versions"][0]
    assert version["rule_kind"] == "CLASSIFICATION"
    assert version["condition"] is None
    assert version["action"] is None
    assert version["branches"][0]["then"][0]["type"] == "SET_OUTPUT"
    assert version["default"][0]["value"] == 0.8


async def test_create_legacy_rule_still_returns_normalized_branch(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    payload = {
        "rule_code": f"LEGACY_V2_{uuid.uuid4().hex[:8].upper()}",
        "name": "Legacy-compatible",
        "category": "AFFORDABILITY",
        "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.45}]},
        "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
    }

    response = await db_client.post("/v1/rules", json=payload, headers=analyst)

    assert response.status_code == 201, response.text
    version = response.json()["versions"][0]
    assert version["condition"] == payload["condition"]
    assert version["action"] == payload["action"]
    assert version["branches"][0]["then"][0]["decision"] == "REJECT"


async def test_rule_request_requires_exactly_one_authoring_form(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    both = _branch_payload(
        condition={"all": [{"field": "loan.ltv", "operator": ">", "value": 0.9}]},
        action={"decision": "REJECT", "reason_code": "HIGH_LTV"},
    )
    neither = {
        "rule_code": f"EMPTY_{uuid.uuid4().hex[:8].upper()}",
        "name": "No body",
        "category": "LIMIT",
    }

    assert (await db_client.post("/v1/rules", json=both, headers=analyst)).status_code == 422
    assert (await db_client.post("/v1/rules", json=neither, headers=analyst)).status_code == 422


async def test_typed_operator_matrix_rejects_invalid_pairs(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    invalid = _branch_payload()
    invalid["branches"][0]["when"] = {
        "all": [{"field": "vehicle.type", "operator": ">", "value": "MOTOR"}]
    }

    response = await db_client.post("/v1/rules", json=invalid, headers=analyst)

    assert response.status_code == 422, response.text
    detail = response.json()["error"]["details"][0]
    assert detail["field"] == "vehicle.type"
    assert detail["issue"] == "operator '>' not allowed for STRING feature"


async def test_typed_condition_value_must_match_catalog_type(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    invalid = _branch_payload()
    invalid["branches"][0]["when"] = {
        "all": [{"field": "vehicle.age_years", "operator": "=", "value": "old"}]
    }

    response = await db_client.post("/v1/rules", json=invalid, headers=analyst)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["details"][0]["issue"] == (
        "value does not match NUMBER feature type"
    )


async def test_v2_dry_run_returns_branch_actions_and_outputs(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    created = (await db_client.post("/v1/rules", json=_branch_payload(), headers=analyst)).json()
    rule_id = created["id"]
    version_id = created["versions"][0]["id"]

    response = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/test",
        json={"features": {"vehicle.age_years": 12}},
        headers=analyst,
    )

    assert response.status_code == 200, response.text
    result = response.json()
    assert result["matched"] is True
    assert result["matched_branch"] == 0
    assert result["actions_applied"][0]["type"] == "SET_OUTPUT"
    assert result["outputs_after"] == {"loan.ltv": 0.95}

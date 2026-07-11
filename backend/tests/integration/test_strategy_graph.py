"""Phase 3 strategy graph API and execution integration tests."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit
from tests.integration.test_strategy_management import VALID_STEPS, submit_with_simulation


def _strategy_body() -> dict[str, Any]:
    token = uuid.uuid4().hex[:8].upper()
    return {
        "strategy_code": f"GRAPH_{token}",
        "name": "Graph strategy",
        "product_type": "CAR_LEASEBACK",
        "segment": f"GRAPH_{token}",
    }


def _branching_graph() -> dict[str, Any]:
    nodes = [
        {"node_key": "start", "node_type": "START", "position": {"x": 0, "y": 80}},
        {
            "node_key": "validation",
            "node_type": "VALIDATION",
            "name": "Required",
            "config": {"required_fields": ["loan.requested_amount", "vehicle.appraisal_value"]},
            "position": {"x": 240, "y": 80},
        },
        {
            "node_key": "calc",
            "node_type": "CALCULATION",
            "name": "Derived",
            "config": {
                "calculations": [
                    "loan.ltv",
                    "affordability.dti",
                    "vehicle.age_years",
                ]
            },
            "position": {"x": 480, "y": 80},
        },
        {
            "node_key": "blacklisted",
            "node_type": "CONDITION",
            "name": "Blacklisted?",
            "config": {
                "condition": {
                    "all": [{"field": "fraud.blacklist_hit", "operator": "=", "value": True}]
                }
            },
            "position": {"x": 720, "y": 80},
        },
        {
            "node_key": "fraud",
            "node_type": "RULE_SET",
            "name": "Fraud",
            "reference_code": "FRAUD_BASIC",
            "position": {"x": 960, "y": 0},
        },
        {
            "node_key": "eligibility",
            "node_type": "RULE_SET",
            "name": "Eligibility",
            "reference_code": "ELIGIBILITY_MOTOR",
            "position": {"x": 960, "y": 160},
        },
        {
            "node_key": "score",
            "node_type": "SCORECARD",
            "name": "Score",
            "reference_code": "MOTOR_SCORECARD",
            "position": {"x": 1200, "y": 80},
        },
        {
            "node_key": "final",
            "node_type": "DECISION_TABLE",
            "name": "Final",
            "reference_code": "FINAL_DECISION_MOTOR",
            "position": {"x": 1440, "y": 80},
        },
        {"node_key": "end", "node_type": "END", "position": {"x": 1680, "y": 80}},
    ]
    edges = [
        {"from": "start", "to": "validation"},
        {"from": "validation", "to": "calc"},
        {"from": "calc", "to": "blacklisted"},
        {"from": "blacklisted", "to": "fraud", "label": "TRUE"},
        {"from": "blacklisted", "to": "eligibility", "label": "FALSE"},
        {"from": "fraud", "to": "score"},
        {"from": "eligibility", "to": "score"},
        {"from": "score", "to": "final"},
        {"from": "final", "to": "end"},
    ]
    return {"nodes": nodes, "edges": edges}


async def test_legacy_steps_are_returned_as_linear_graph(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    strategy = (
        await db_client.post("/v1/strategies", json=_strategy_body(), headers=analyst)
    ).json()
    response = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={"steps": VALID_STEPS},
        headers=analyst,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert [item["order"] for item in body["steps"]] == [1, 2, 3, 4, 5]
    assert body["graph"]["nodes"][0]["node_key"] in {"end", "n1", "start"}
    assert any(node["node_type"] == "START" for node in body["graph"]["nodes"])
    assert any(node["node_type"] == "END" for node in body["graph"]["nodes"])


async def test_graph_xor_steps_and_validation_errors(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    strategy = (
        await db_client.post("/v1/strategies", json=_strategy_body(), headers=analyst)
    ).json()
    both = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={"steps": VALID_STEPS, "graph": _branching_graph()},
        headers=analyst,
    )
    assert both.status_code == 422

    cyclic = _branching_graph()
    cyclic["edges"].append({"from": "final", "to": "calc"})
    invalid = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={"graph": cyclic},
        headers=analyst,
    )
    assert invalid.status_code == 422
    assert "cycle detected" in invalid.text


async def test_condition_graph_executes_both_paths_and_traces_node_keys(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    strategy_body = _strategy_body()
    strategy = (await db_client.post("/v1/strategies", json=strategy_body, headers=analyst)).json()
    version_response = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        json={"version_note": "branching", "graph": _branching_graph()},
        headers=analyst,
    )
    assert version_response.status_code == 201, version_response.text
    version = version_response.json()
    assert version["steps"] is None

    await submit_with_simulation(db_client, analyst, strategy["id"], version["id"])
    activated = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        json={"reason": "graph test"},
        headers=manager,
    )
    assert activated.status_code == 200, activated.text

    false_payload = lease_back_motor_payload(
        product_type="CAR_LEASEBACK", segment=strategy_body["segment"]
    )
    false_payload["application_id"] = f"GRAPH-FALSE-{uuid.uuid4().hex[:8]}"
    false_result = await submit(db_client, false_payload)
    assert false_result.status_code == 201, false_result.text

    true_payload = lease_back_motor_payload(
        product_type="CAR_LEASEBACK",
        segment=strategy_body["segment"],
        fraud={"blacklist_hit": True},
    )
    true_payload["application_id"] = f"GRAPH-TRUE-{uuid.uuid4().hex[:8]}"
    true_result = await submit(db_client, true_payload)
    assert true_result.status_code == 201, true_result.text
    assert true_result.json()["decision"] == "REJECT"

    false_trace_response = await db_client.get(
        f"/v1/decisions/{false_result.json()['decision_id']}/trace", headers=analyst
    )
    true_trace_response = await db_client.get(
        f"/v1/decisions/{true_result.json()['decision_id']}/trace", headers=analyst
    )
    assert false_trace_response.status_code == 200, false_trace_response.text
    assert true_trace_response.status_code == 200, true_trace_response.text
    false_trace = false_trace_response.json()
    true_trace = true_trace_response.json()
    assert false_trace["strategy"]["execution"] == "GRAPH"
    assert false_trace["steps"][2]["node_key"] == "blacklisted"
    assert false_trace["steps"][2]["taken_edge"] == "FALSE"
    assert false_trace["steps"][3]["node_key"] == "eligibility"
    assert true_trace["steps"][2]["taken_edge"] == "TRUE"
    assert true_trace["steps"][3]["node_key"] == "fraud"

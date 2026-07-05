"""Full maker-checker: mandatory simulation attachment before activation (P2.4)."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload
from tests.integration.test_strategy_management import (
    VALID_STEPS,
    submit_with_simulation,
)


def _strategy_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "strategy_code": f"MC_STRAT_{uuid.uuid4().hex[:6].upper()}",
        "name": "Maker-checker strategy",
        "product_type": "AUTO_LOAN_CAR",
        "segment": f"SEG_{uuid.uuid4().hex[:6].upper()}",
    }
    body.update(overrides)
    return body


async def _draft_version(client: AsyncClient, analyst: dict[str, str]) -> tuple[str, str]:
    strategy = (await client.post("/v1/strategies", json=_strategy_body(), headers=analyst)).json()
    version = (
        await client.post(
            f"/v1/strategies/{strategy['id']}/versions",
            json={"steps": VALID_STEPS},
            headers=analyst,
        )
    ).json()
    return strategy["id"], version["id"]


async def test_activation_blocked_without_attached_simulation(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    strategy_id, version_id = await _draft_version(db_client, analyst)

    # Submit for approval WITHOUT attaching a simulation.
    await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{version_id}/submit-approval", headers=analyst
    )
    blocked = await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{version_id}/activate",
        json={"reason": "no sim attached"},
        headers=manager,
    )
    assert blocked.status_code == 409
    assert "simulation" in blocked.json()["error"]["message"].lower()


async def test_activation_succeeds_with_attached_simulation(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    strategy_id, version_id = await _draft_version(db_client, analyst)

    await submit_with_simulation(db_client, analyst, strategy_id, version_id)
    activated = await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{version_id}/activate",
        json={"reason": "impact assessed via attached simulation"},
        headers=manager,
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "ACTIVE"

    # The approval request carries the simulation reference.
    approvals = (await db_client.get("/v1/approvals", headers=manager)).json()
    entry = next(
        a
        for a in approvals
        if a["entity_type"] == "STRATEGY_VERSION"
        and a["status"] == "APPROVED"
        and a["simulation_ref"] is not None
    )
    assert entry["simulation_ref"].startswith("SIM-")


async def test_submit_rejects_mismatched_simulation(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    strategy_id, version_id = await _draft_version(db_client, analyst)

    # A simulation of a *different* (active leaseback) version, not this one.
    strategies = (await db_client.get("/v1/strategies", headers=analyst)).json()
    leaseback = next(s for s in strategies if s["strategy_code"] == "LEASEBACK_MOTOR")
    detail = (await db_client.get(f"/v1/strategies/{leaseback['id']}", headers=analyst)).json()
    other_version = next(v for v in detail["versions"] if v["status"] == "ACTIVE")["id"]
    sim = (
        await db_client.post(
            "/v1/simulations/single",
            json={
                "application_payload": lease_back_motor_payload(),
                "strategy_version_id": other_version,
            },
            headers=analyst,
        )
    ).json()

    mismatched = await db_client.post(
        f"/v1/strategies/{strategy_id}/versions/{version_id}/submit-approval",
        json={"simulation_id": sim["simulation_id"]},
        headers=analyst,
    )
    assert mismatched.status_code == 422
    assert mismatched.json()["error"]["details"][0]["field"] == "simulation_id"

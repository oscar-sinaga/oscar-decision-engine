"""Feature catalog tests (Phase 2 — data dictionary governs rule vocabulary)."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login


def _rule_payload(field: str, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "rule_code": f"FC_RULE_{uuid.uuid4().hex[:6].upper()}",
        "name": "Feature catalog test rule",
        "category": "AFFORDABILITY",
        "condition": {"all": [{"field": field, "operator": ">", "value": 1}]},
        "action": {"decision": "MANUAL_REVIEW", "reason_code": "DTI_NEAR_THRESHOLD"},
    }
    body.update(overrides)
    return body


async def test_catalog_seeded_and_listable(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    features = (await db_client.get("/v1/features", headers=analyst)).json()
    paths = {f["path"] for f in features}
    # Payload, derived, and score features are all present.
    assert "affordability.dti" in paths
    assert "loan.ltv" in paths
    assert "score.risk_grade" in paths
    dti = next(f for f in features if f["path"] == "affordability.dti")
    assert dti["source"] == "DERIVED"
    assert dti["data_type"] == "NUMBER"
    assert dti["category"] == "AFFORDABILITY"

    derived_only = (
        await db_client.get("/v1/features", params={"source": "DERIVED"}, headers=analyst)
    ).json()
    assert all(f["source"] == "DERIVED" for f in derived_only)


async def test_meta_reflects_catalog(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    meta = (await db_client.get("/v1/meta", headers=analyst)).json()
    meta_paths = {f["path"] for f in meta["features"]}
    catalog_paths = {
        f["path"]
        for f in (
            await db_client.get("/v1/features", params={"active": True}, headers=analyst)
        ).json()
    }
    assert meta_paths == catalog_paths


async def test_new_catalog_feature_enables_rule(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    novel = f"applicant.custom_score_{uuid.uuid4().hex[:6]}"

    # A rule referencing an uncatalogued feature is rejected.
    rejected = await db_client.post("/v1/rules", json=_rule_payload(novel), headers=analyst)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["details"][0]["field"] == novel

    # Add the feature to the catalog, then the same rule validates.
    created = await db_client.post(
        "/v1/features",
        json={
            "path": novel,
            "label": "Custom score",
            "description": "Partner-provided custom score",
            "data_type": "NUMBER",
            "source": "PAYLOAD",
            "category": "APPLICANT",
        },
        headers=analyst,
    )
    assert created.status_code == 201, created.text
    accepted = await db_client.post("/v1/rules", json=_rule_payload(novel), headers=analyst)
    assert accepted.status_code == 201


async def test_deactivated_feature_blocks_new_rules(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    path = f"vehicle.custom_flag_{uuid.uuid4().hex[:6]}"
    created = (
        await db_client.post(
            "/v1/features",
            json={
                "path": path,
                "label": "Custom flag",
                "data_type": "BOOLEAN",
                "source": "PAYLOAD",
                "category": "VEHICLE",
            },
            headers=analyst,
        )
    ).json()

    ok = await db_client.post(
        "/v1/rules",
        json=_rule_payload(
            path, condition={"all": [{"field": path, "operator": "=", "value": True}]}
        ),
        headers=analyst,
    )
    assert ok.status_code == 201

    deactivated = await db_client.patch(
        f"/v1/features/{created['id']}", json={"active": False}, headers=analyst
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    blocked = await db_client.post(
        "/v1/rules",
        json=_rule_payload(
            path, condition={"all": [{"field": path, "operator": "=", "value": True}]}
        ),
        headers=analyst,
    )
    assert blocked.status_code == 422


async def test_feature_management_requires_permission(db_client: AsyncClient) -> None:
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.post(
        "/v1/features",
        json={
            "path": "applicant.blocked",
            "label": "x",
            "data_type": "NUMBER",
            "source": "PAYLOAD",
        },
        headers=underwriter,
    )
    assert denied.status_code == 403

    auditor = await login(db_client, "auditor")
    # Auditor can view the catalog (rule.view) but not create.
    assert (await db_client.get("/v1/features", headers=auditor)).status_code == 200

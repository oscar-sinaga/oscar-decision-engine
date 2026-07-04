"""Governance tests: maker-checker, approval queue, audit API, admin RBAC (docs/14)."""

import uuid
from typing import Any

from httpx import AsyncClient

from tests.conftest import login


def _rule_payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "rule_code": f"GOV_RULE_{uuid.uuid4().hex[:6].upper()}",
        "name": "Governance test rule",
        "category": "AFFORDABILITY",
        "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.45}]},
        "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
    }
    body.update(overrides)
    return body


async def test_maker_cannot_approve_own_change(db_client: AsyncClient) -> None:
    manager = await login(db_client, "riskmanager")  # has both create and approve

    created = (await db_client.post("/v1/rules", json=_rule_payload(), headers=manager)).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/submit-approval", headers=manager
    )
    denied = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate",
        json={"reason": "self-approval attempt"},
        headers=manager,
    )
    assert denied.status_code == 403
    assert "Maker-checker" in denied.json()["error"]["message"]

    # A different approver (admin) can activate it.
    admin = await login(db_client, "admin")
    approved = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate",
        json={"reason": "independent approval"},
        headers=admin,
    )
    assert approved.status_code == 200


async def test_maker_checker_applies_to_strategies(db_client: AsyncClient) -> None:
    manager = await login(db_client, "riskmanager")
    strategy = (
        await db_client.post(
            "/v1/strategies",
            json={
                "strategy_code": f"GOV_STRAT_{uuid.uuid4().hex[:6].upper()}",
                "name": "Gov strategy",
                "product_type": "AUTO_LOAN_CAR",
                "segment": f"SEG_{uuid.uuid4().hex[:6].upper()}",
            },
            headers=manager,
        )
    ).json()
    version = (
        await db_client.post(
            f"/v1/strategies/{strategy['id']}/versions",
            json={
                "steps": [
                    {"order": 1, "type": "RULE_SET", "reference_code": "AFFORDABILITY_STANDARD"},
                    {
                        "order": 2,
                        "type": "DECISION_TABLE",
                        "reference_code": "FINAL_DECISION_MOTOR",
                    },
                    {"order": 3, "type": "SCORECARD", "reference_code": "MOTOR_SCORECARD"},
                ]
            },
            headers=manager,
        )
    ).json()
    await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/submit-approval",
        headers=manager,
    )
    denied = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        json={"reason": "self"},
        headers=manager,
    )
    assert denied.status_code == 403


async def test_approval_queue_tracks_lifecycle(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    code = f"GOV_QUEUE_{uuid.uuid4().hex[:6].upper()}"

    created = (
        await db_client.post(
            "/v1/rules",
            json=_rule_payload(rule_code=code, version_note="tighten policy"),
            headers=analyst,
        )
    ).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/submit-approval", headers=analyst
    )

    pending = await db_client.get("/v1/approvals", params={"status": "PENDING"}, headers=manager)
    assert pending.status_code == 200
    entry = next(r for r in pending.json() if r["entity_id"] == code)
    assert entry["entity_type"] == "RULE_VERSION"
    assert entry["requested_by"] == "riskanalyst"

    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate",
        json={"reason": "looks good"},
        headers=manager,
    )
    approved = await db_client.get("/v1/approvals", headers=manager)
    entry = next(r for r in approved.json() if r["entity_id"] == code)
    assert entry["status"] == "APPROVED"
    assert entry["decided_by"] == "riskmanager"
    assert entry["decision_reason"] == "looks good"

    # Underwriter is not an approver.
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.get("/v1/approvals", headers=underwriter)
    assert denied.status_code == 403


async def test_audit_log_api_filters(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    code = f"GOV_AUDITED_{uuid.uuid4().hex[:6].upper()}"
    await db_client.post("/v1/rules", json=_rule_payload(rule_code=code), headers=analyst)

    auditor = await login(db_client, "auditor")
    by_entity = await db_client.get("/v1/audit-logs", params={"entity_id": code}, headers=auditor)
    assert by_entity.status_code == 200
    body = by_entity.json()
    assert body["total"] == 1
    event = body["items"][0]
    assert event["event_type"] == "RULE_CREATED"
    assert event["actor_label"] == "riskanalyst"
    assert event["correlation_id"] is not None

    by_type = await db_client.get(
        "/v1/audit-logs",
        params={"event_type": "RULE_CREATED", "actor": "riskanalyst", "page_size": 5},
        headers=auditor,
    )
    assert by_type.status_code == 200
    assert all(i["event_type"] == "RULE_CREATED" for i in by_type.json()["items"])

    # Underwriter has no audit.view.
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.get("/v1/audit-logs", headers=underwriter)
    assert denied.status_code == 403


async def test_admin_role_assignment_with_audit(db_client: AsyncClient) -> None:
    admin = await login(db_client, "admin")

    users = await db_client.get("/v1/admin/users", headers=admin)
    assert users.status_code == 200
    engineer = next(u for u in users.json() if u["username"] == "engineer")
    assert engineer["roles"] == ["ENGINEER"]

    matrix = await db_client.get("/v1/admin/roles", headers=admin)
    assert matrix.status_code == 200
    auditor_role = next(r for r in matrix.json() if r["code"] == "AUDITOR")
    assert "audit.view" in auditor_role["permissions"]

    updated = await db_client.put(
        "/v1/admin/users/engineer/roles",
        json={"roles": ["ENGINEER", "AUDITOR"]},
        headers=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["roles"] == ["AUDITOR", "ENGINEER"]

    # Newly granted permission works immediately.
    engineer_headers = await login(db_client, "engineer")
    audit_ok = await db_client.get("/v1/audit-logs", headers=engineer_headers)
    assert audit_ok.status_code == 200

    # Restore original roles.
    restored = await db_client.put(
        "/v1/admin/users/engineer/roles", json={"roles": ["ENGINEER"]}, headers=admin
    )
    assert restored.json()["roles"] == ["ENGINEER"]

    unknown = await db_client.put(
        "/v1/admin/users/engineer/roles", json={"roles": ["NOT_A_ROLE"]}, headers=admin
    )
    assert unknown.status_code == 422

    # Non-admin cannot manage roles.
    manager = await login(db_client, "riskmanager")
    denied = await db_client.put(
        "/v1/admin/users/engineer/roles", json={"roles": ["ADMIN"]}, headers=manager
    )
    assert denied.status_code == 403

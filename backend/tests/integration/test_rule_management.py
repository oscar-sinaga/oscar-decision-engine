"""Rule / decision-table / scorecard / reason-code management tests (Epics 3, 6)."""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


def _rule_payload(code: str | None = None, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "rule_code": code or f"TEST_RULE_{uuid.uuid4().hex[:6].upper()}",
        "name": "Test rule",
        "category": "AFFORDABILITY",
        "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.45}]},
        "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
    }
    body.update(overrides)
    return body


async def test_create_rule_and_lifecycle(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")

    created = await db_client.post("/v1/rules", json=_rule_payload(), headers=analyst)
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["latest_status"] == "DRAFT"
    assert rule["active_version"] is None
    rule_id = rule["id"]
    version_id = rule["versions"][0]["id"]

    # Draft is editable.
    updated = await db_client.put(
        f"/v1/rules/{rule_id}/versions/{version_id}",
        json={
            "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.5}]},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
        },
        headers=analyst,
    )
    assert updated.status_code == 200
    assert updated.json()["condition"]["all"][0]["value"] == 0.5

    # Submit, then activate with the manager role.
    submitted = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/submit-approval", headers=analyst
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "PENDING_APPROVAL"

    activated = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate",
        json={"reason": "Approved for production"},
        headers=manager,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"

    # Active version is immutable.
    frozen = await db_client.put(
        f"/v1/rules/{rule_id}/versions/{version_id}",
        json={
            "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.6}]},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
        },
        headers=analyst,
    )
    assert frozen.status_code == 409
    assert frozen.json()["error"]["code"] == "IMMUTABLE_CONFIGURATION"

    # New draft version can be created and activated; previous is retired.
    v2 = await db_client.post(
        f"/v1/rules/{rule_id}/versions",
        json={
            "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.55}]},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
            "version_note": "Loosen threshold",
        },
        headers=analyst,
    )
    assert v2.status_code == 201
    v2_id = v2.json()["id"]
    await db_client.post(f"/v1/rules/{rule_id}/versions/{v2_id}/submit-approval", headers=analyst)
    activated_v2 = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{v2_id}/activate", json={"reason": "ok"}, headers=manager
    )
    assert activated_v2.status_code == 200

    detail = (await db_client.get(f"/v1/rules/{rule_id}", headers=analyst)).json()
    statuses = {v["version"]: v["status"] for v in detail["versions"]}
    assert statuses == {1: "RETIRED", 2: "ACTIVE"}
    assert detail["active_version"] == 2


async def test_rule_validation_rejects_unknown_features_and_reason_codes(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")

    unknown_field = await db_client.post(
        "/v1/rules",
        json=_rule_payload(
            condition={"all": [{"field": "loan.shark_index", "operator": ">", "value": 1}]}
        ),
        headers=analyst,
    )
    assert unknown_field.status_code == 422
    assert unknown_field.json()["error"]["details"][0]["field"] == "loan.shark_index"

    unknown_reason = await db_client.post(
        "/v1/rules",
        json=_rule_payload(action={"decision": "REJECT", "reason_code": "NOT_A_REAL_CODE"}),
        headers=analyst,
    )
    assert unknown_reason.status_code == 422

    bad_operator = await db_client.post(
        "/v1/rules",
        json=_rule_payload(
            condition={"all": [{"field": "affordability.dti", "operator": "like", "value": 1}]}
        ),
        headers=analyst,
    )
    assert bad_operator.status_code == 422


async def test_rule_activation_requires_approve_permission(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    created = (await db_client.post("/v1/rules", json=_rule_payload(), headers=analyst)).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/submit-approval", headers=analyst
    )

    denied = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate", json={"reason": "x"}, headers=analyst
    )
    assert denied.status_code == 403

    auditor = await login(db_client, "auditor")
    read_only = await db_client.post("/v1/rules", json=_rule_payload(), headers=auditor)
    assert read_only.status_code == 403
    listing = await db_client.get("/v1/rules", headers=auditor)
    assert listing.status_code == 200  # auditor can read


async def test_unsubmitted_draft_cannot_activate(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    created = (await db_client.post("/v1/rules", json=_rule_payload(), headers=analyst)).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    response = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate", json={"reason": "x"}, headers=manager
    )
    assert response.status_code == 409


async def test_rule_test_endpoint_dry_runs(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    created = (await db_client.post("/v1/rules", json=_rule_payload(), headers=analyst)).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    result = await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/test",
        json={"features": {"affordability.dti": 0.5}},
        headers=analyst,
    )
    assert result.status_code == 200
    body = result.json()
    assert body["matched"] is True
    assert body["action"]["reason_code"] == "HIGH_DTI"
    assert body["evaluated_conditions"][0]["actual"] == 0.5


async def test_activated_rule_version_changes_runtime_behavior(db_client: AsyncClient) -> None:
    """A new DTI threshold takes effect for new decisions and traces pin v2."""
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")

    # Baseline: dti ≈ 0.469 rejects under v1 threshold (> 0.45).
    payload = lease_back_motor_payload(applicant={"monthly_income": 6_660_000})
    baseline = (await submit(db_client, payload)).json()
    assert baseline["decision"] == "REJECT"

    # Find the DTI_MAX_STANDARD rule and raise the threshold to 0.48 as v2.
    rules = (await db_client.get("/v1/rules", headers=analyst)).json()
    dti_rule = next(r for r in rules if r["rule_code"] == "DTI_MAX_STANDARD")
    v2 = await db_client.post(
        f"/v1/rules/{dti_rule['id']}/versions",
        json={
            "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.48}]},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
            "version_note": "Raise DTI ceiling",
        },
        headers=analyst,
    )
    v2_id = v2.json()["id"]
    await db_client.post(
        f"/v1/rules/{dti_rule['id']}/versions/{v2_id}/submit-approval", headers=analyst
    )
    activated = await db_client.post(
        f"/v1/rules/{dti_rule['id']}/versions/{v2_id}/activate",
        json={"reason": "Policy change CR-42"},
        headers=manager,
    )
    assert activated.status_code == 200

    try:
        # Same applicant now passes both DTI rules (0.469 < 0.48 ceiling; the
        # near-threshold band tops out at 0.45) → approval path under grade B.
        after = (
            await submit(
                db_client, lease_back_motor_payload(applicant={"monthly_income": 6_660_000})
            )
        ).json()
        assert after["decision"] == "APPROVE_WITH_CONDITION"

        # The trace pins the exact rule version used.
        trace = (
            await db_client.get(f"/v1/decisions/{after['decision_id']}/trace", headers=analyst)
        ).json()
        rule_versions = {
            r["rule_code"]: r["version"]
            for s in trace["steps"]
            if s["type"] == "RULE_SET"
            for r in s["rule_results"]
        }
        assert rule_versions["DTI_MAX_STANDARD"] == 2
        assert rule_versions["DTI_NEAR_THRESHOLD"] == 1
    finally:
        # Restore v1 so other tests keep the seeded policy: create v3 = v1 config.
        v3 = await db_client.post(
            f"/v1/rules/{dti_rule['id']}/versions",
            json={
                "condition": {
                    "all": [{"field": "affordability.dti", "operator": ">", "value": 0.45}]
                },
                "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
                "version_note": "Restore threshold",
            },
            headers=analyst,
        )
        v3_id = v3.json()["id"]
        await db_client.post(
            f"/v1/rules/{dti_rule['id']}/versions/{v3_id}/submit-approval", headers=analyst
        )
        await db_client.post(
            f"/v1/rules/{dti_rule['id']}/versions/{v3_id}/activate",
            json={"reason": "restore"},
            headers=manager,
        )


async def test_rule_lifecycle_audit_trail(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    code = f"AUDITED_RULE_{uuid.uuid4().hex[:6].upper()}"
    created = (
        await db_client.post("/v1/rules", json=_rule_payload(code=code), headers=analyst)
    ).json()
    rule_id, version_id = created["id"], created["versions"][0]["id"]
    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/submit-approval", headers=analyst
    )
    await db_client.post(
        f"/v1/rules/{rule_id}/versions/{version_id}/activate",
        json={"reason": "audit trail test"},
        headers=manager,
    )

    async with get_sessionmaker()() as session:
        events = (
            await session.scalars(
                select(AuditLog).where(AuditLog.entity_id == code).order_by(AuditLog.created_at)
            )
        ).all()
    event_types = [e.event_type for e in events]
    assert event_types == ["RULE_CREATED", "RULE_VERSION_SUBMITTED", "RULE_VERSION_ACTIVATED"]
    activation = events[-1]
    assert activation.actor_label == "riskmanager"
    assert activation.reason == "audit trail test"
    assert activation.before_value == {"status": "PENDING_APPROVAL"}
    assert activation.after_value is not None
    assert activation.after_value["status"] == "ACTIVE"


async def test_decision_table_management_with_overlap_warnings(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    code = f"TEST_TABLE_{uuid.uuid4().hex[:6].upper()}"
    created = await db_client.post(
        "/v1/decision-tables",
        json={
            "code": code,
            "name": "Test matrix",
            "config": {
                "hit_policy": "FIRST_MATCH",
                "rows": [
                    {
                        "conditions": [
                            {"field": "score.risk_grade", "operator": "=", "value": "A"}
                        ],
                        "output": {"decision": "APPROVE"},
                    },
                    {
                        "conditions": [
                            {"field": "score.risk_grade", "operator": "in", "value": ["A", "B"]}
                        ],
                        "output": {
                            "decision": "MANUAL_REVIEW",
                            "reason_code": "RISK_GRADE_BORDERLINE",
                        },
                    },
                ],
            },
        },
        headers=analyst,
    )
    assert created.status_code == 201, created.text

    # Invalid config rejected.
    invalid = await db_client.post(
        "/v1/decision-tables",
        json={
            "code": f"BAD_TABLE_{uuid.uuid4().hex[:6].upper()}",
            "name": "Bad",
            "config": {"rows": [{"conditions": [], "output": {"decision": "NOT_A_DECISION"}}]},
        },
        headers=analyst,
    )
    assert invalid.status_code == 422

    # Overlap warnings surface when editing the open draft version.
    entity_id = created.json()["id"]
    draft_version_id = created.json()["versions"][0]["id"]
    version = await db_client.put(
        f"/v1/decision-tables/{entity_id}/versions/{draft_version_id}",
        json={
            "config": {
                "hit_policy": "FIRST_MATCH",
                "rows": [
                    {
                        "conditions": [
                            {"field": "score.risk_grade", "operator": "=", "value": "A"}
                        ],
                        "output": {"decision": "APPROVE"},
                    },
                    {
                        "conditions": [
                            {"field": "score.risk_grade", "operator": "in", "value": ["A", "B"]}
                        ],
                        "output": {"decision": "REJECT", "reason_code": "LOW_CREDIT_SCORE"},
                    },
                ],
            },
        },
        headers=analyst,
    )
    assert version.status_code == 200
    assert any(w["warning"] == "OVERLAPPING_ROWS" for w in version.json()["warnings"])

    reopened = await db_client.get(f"/v1/decision-tables/{entity_id}", headers=analyst)
    assert reopened.status_code == 200
    assert any(
        warning["warning"] == "OVERLAPPING_ROWS"
        for warning in reopened.json()["versions"][0]["warnings"]
    )


async def test_scorecard_management(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    code = f"TEST_SC_{uuid.uuid4().hex[:6].upper()}"
    created = await db_client.post(
        "/v1/scorecards",
        json={
            "code": code,
            "name": "Test scorecard",
            "config": {
                "bands": [{"min_score": 700, "risk_grade": "A"}],
                "missing_score_decision": "MANUAL_REVIEW",
                "missing_score_reason_code": "SCORE_UNAVAILABLE",
            },
        },
        headers=analyst,
    )
    assert created.status_code == 201, created.text
    entity_id = created.json()["id"]
    version_id = created.json()["versions"][0]["id"]
    await db_client.post(
        f"/v1/scorecards/{entity_id}/versions/{version_id}/submit-approval", headers=analyst
    )
    activated = await db_client.post(
        f"/v1/scorecards/{entity_id}/versions/{version_id}/activate",
        json={"reason": "ok"},
        headers=manager,
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "ACTIVE"

    invalid = await db_client.post(
        "/v1/scorecards",
        json={
            "code": f"BAD_SC_{uuid.uuid4().hex[:4].upper()}",
            "name": "Bad",
            "config": {"bands": []},
        },
        headers=analyst,
    )
    assert invalid.status_code == 422


async def test_reason_code_crud_with_audit(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    code = f"TEST_REASON_{uuid.uuid4().hex[:6].upper()}"
    created = await db_client.post(
        "/v1/reason-codes",
        json={
            "code": code,
            "category": "OPERATIONAL",
            "severity": "REVIEW",
            "internal_message": "Test reason",
        },
        headers=analyst,
    )
    assert created.status_code == 201

    duplicate = await db_client.post(
        "/v1/reason-codes",
        json={
            "code": code,
            "category": "OPERATIONAL",
            "severity": "REVIEW",
            "internal_message": "Duplicate",
        },
        headers=analyst,
    )
    assert duplicate.status_code == 409

    updated = await db_client.patch(
        f"/v1/reason-codes/{created.json()['id']}",
        json={"active": False},
        headers=analyst,
    )
    assert updated.status_code == 200
    assert updated.json()["active"] is False

    async with get_sessionmaker()() as session:
        events = (await session.scalars(select(AuditLog).where(AuditLog.entity_id == code))).all()
    assert {e.event_type for e in events} == {"REASON_CODE_CREATED", "REASON_CODE_UPDATED"}

    # Underwriter cannot manage reason codes.
    underwriter = await login(db_client, "underwriter")
    denied = await db_client.post(
        "/v1/reason-codes",
        json={
            "code": "X_DENIED",
            "category": "OPERATIONAL",
            "severity": "REVIEW",
            "internal_message": "nope",
        },
        headers=underwriter,
    )
    assert denied.status_code == 403

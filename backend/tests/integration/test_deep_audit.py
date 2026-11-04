"""End-to-end regressions for governance, runtime inputs, and concurrent review."""

import asyncio
import copy
import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.decisions.models import Application, Decision
from app.modules.manual_review import service as review_service
from app.modules.manual_review.schemas import AnalystDecisionRequest
from app.shared.config import get_settings
from app.shared.database.session import get_sessionmaker
from app.shared.domain.enums import DecisionType
from app.shared.domain.errors import ConflictError
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit
from tests.integration.test_maker_checker_simulation import _draft_version
from tests.integration.test_manual_review import _create_review_case
from tests.integration.test_strategy_management import VALID_STEPS, submit_with_simulation


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"


async def make_rule(
    client: AsyncClient, headers: dict[str, str], field: str = "applicant.age"
) -> dict[str, Any]:
    response = await client.post(
        "/v1/rules",
        headers=headers,
        json={
            "rule_code": unique("AUDIT_RULE"),
            "name": "Synthetic audit rule",
            "category": "ELIGIBILITY",
            "condition": {"field": field, "operator": ">=", "value": 10},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
        },
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


async def activate_rule(
    client: AsyncClient, rule: dict[str, Any], maker: dict[str, str], checker: dict[str, str]
) -> None:
    path = f"/v1/rules/{rule['id']}/versions/{rule['versions'][0]['id']}"
    submitted = await client.post(path + "/submit-approval", headers=maker)
    assert submitted.status_code == 200, submitted.text
    activated = await client.post(
        path + "/activate", headers=checker, json={"reason": "Synthetic audit fixture"}
    )
    assert activated.status_code == 200, activated.text


async def draft_for_set(
    client: AsyncClient, maker: dict[str, str], set_code: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    code = unique("AUDIT_STRATEGY")
    created = await client.post(
        "/v1/strategies",
        headers=maker,
        json={
            "strategy_code": code,
            "name": "Synthetic audit policy",
            "product_type": "MOTOR_LEASEBACK",
            "segment": code,
        },
    )
    assert created.status_code == 201, created.text
    strategy = created.json()
    version = await client.post(
        f"/v1/strategies/{strategy['id']}/versions",
        headers=maker,
        json={
            "steps": [
                {"order": 1, "type": "RULE_SET", "name": "Audit input", "reference_code": set_code}
            ],
        },
    )
    assert version.status_code == 201, version.text
    return strategy, version.json()


async def test_custom_catalog_feature_reaches_production_and_simulation(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    manager = await login(db_client, "riskmanager")
    field = "applicant." + unique("audit_score").lower()
    feature = await db_client.post(
        "/v1/features",
        headers=analyst,
        json={
            "path": field,
            "label": "Synthetic custom score",
            "data_type": "NUMBER",
            "source": "PAYLOAD",
        },
    )
    assert feature.status_code == 201, feature.text
    rule = await make_rule(db_client, analyst, field)
    await activate_rule(db_client, rule, analyst, manager)
    rule_set = await db_client.post(
        "/v1/rule-sets",
        headers=analyst,
        json={
            "code": unique("AUDIT_SET"),
            "name": "Audit set",
            "rule_codes": [rule["rule_code"]],
        },
    )
    assert rule_set.status_code == 201, rule_set.text
    strategy, version = await draft_for_set(db_client, analyst, rule_set.json()["code"])
    await submit_with_simulation(db_client, analyst, strategy["id"], version["id"])
    activated = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/activate",
        headers=manager,
        json={"reason": "Synthetic fixture"},
    )
    assert activated.status_code == 200, activated.text
    payload = lease_back_motor_payload(segment=strategy["segment"])
    payload["applicant"][field.split(".", 1)[1]] = 20
    decision = await submit(db_client, payload)
    assert decision.status_code == 201, decision.text
    assert decision.json()["decision"] == "REJECT"
    trace = await db_client.get(
        f"/v1/decisions/{decision.json()['decision_id']}/trace", headers=analyst
    )
    assert trace.json()["feature_values"][field] == 20
    simulation = await db_client.post(
        "/v1/simulations/single",
        headers=analyst,
        json={"application_payload": payload, "strategy_version_id": version["id"]},
    )
    assert simulation.status_code == 201, simulation.text
    assert simulation.json()["draft_result"]["decision"] == "REJECT"
    # Retirement affects new authoring, not execution of existing approved rules.
    retired = await db_client.patch(
        f"/v1/features/{feature.json()['id']}", headers=analyst, json={"active": False}
    )
    assert retired.status_code == 200
    payload["application_id"] = unique("APP")
    assert (await submit(db_client, payload)).json()["decision"] == "REJECT"


@pytest.mark.parametrize(
    "section,key,value",
    [
        ("fraud", "blacklist_hit", "false"),
        ("fraud", "identity_match", 1),
        ("applicant", "monthly_income", "8500000"),
        ("vehicle", "year", True),
    ],
)
async def test_runtime_rejects_catalog_type_mismatch(
    db_client: AsyncClient, section: str, key: str, value: Any
) -> None:
    payload = lease_back_motor_payload()
    payload[section][key] = value
    response = await submit(db_client, payload)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
async def test_nonstandard_json_numbers_return_safe_422(
    db_client: AsyncClient, literal: str
) -> None:
    payload = lease_back_motor_payload()
    payload["loan"]["requested_amount"] = "BADNUM"
    raw = json.dumps(payload).replace('"BADNUM"', literal)
    headers = {**await login(db_client, "los-client"), "Content-Type": "application/json"}
    response = await db_client.post("/v1/decisions", content=raw, headers=headers)
    assert response.status_code == 422, response.text


async def test_batch_allows_absent_active_comparison_without_hiding_candidate(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    _, version_id = await _draft_version(db_client, analyst)
    payload = lease_back_motor_payload(product_type="TOP_UP", segment=unique("NO_ACTIVE"))
    response = await db_client.post(
        "/v1/simulations/batch",
        headers=analyst,
        json={
            "strategy_version_id": version_id,
            "application_payloads": [payload],
            "compare_with_active": True,
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["total_records"] == 1
    assert response.json()["active"] is None


async def test_editor_cannot_approve_another_makers_rule(db_client: AsyncClient) -> None:
    analyst, manager, admin = [
        await login(db_client, u) for u in ("riskanalyst", "riskmanager", "admin")
    ]
    rule = await make_rule(db_client, analyst)
    path = f"/v1/rules/{rule['id']}/versions/{rule['versions'][0]['id']}"
    changed = await db_client.put(
        path,
        headers=manager,
        json={
            "condition": {"field": "applicant.age", "operator": ">=", "value": 18},
            "action": {"decision": "REJECT", "reason_code": "HIGH_DTI"},
        },
    )
    assert changed.status_code == 200, changed.text
    assert (await db_client.post(path + "/submit-approval", headers=analyst)).status_code == 200
    blocked = await db_client.post(
        path + "/activate", headers=manager, json={"reason": "Self-reviewed edit"}
    )
    assert blocked.status_code == 403, blocked.text
    approved = await db_client.post(
        path + "/activate", headers=admin, json={"reason": "Independent check"}
    )
    assert approved.status_code == 200, approved.text


@pytest.mark.parametrize(
    "endpoint,config",
    [
        ("scorecards", {"bands": [{"min_score": 0, "risk_grade": "A"}]}),
        (
            "decision-tables",
            {"rows": [{"conditions": [], "output": {"decision": "MANUAL_REVIEW"}}]},
        ),
    ],
)
async def test_config_editor_cannot_self_approve(
    db_client: AsyncClient, endpoint: str, config: dict[str, Any]
) -> None:
    analyst, manager = [await login(db_client, u) for u in ("riskanalyst", "riskmanager")]
    response = await db_client.post(
        f"/v1/{endpoint}",
        headers=analyst,
        json={"code": unique("AUDIT_CONFIG"), "name": "Audit", "config": config},
    )
    assert response.status_code == 201, response.text
    entity = response.json()
    path = f"/v1/{endpoint}/{entity['id']}/versions/{entity['versions'][0]['id']}"
    assert (
        await db_client.put(
            path, headers=manager, json={"config": config, "version_note": "Reviewed edit"}
        )
    ).status_code == 200
    assert (await db_client.post(path + "/submit-approval", headers=analyst)).status_code == 200
    blocked = await db_client.post(
        path + "/activate", headers=manager, json={"reason": "Self approval"}
    )
    assert blocked.status_code == 403, blocked.text


async def test_strategy_editor_cannot_self_approve(db_client: AsyncClient) -> None:
    analyst, manager = [await login(db_client, u) for u in ("riskanalyst", "riskmanager")]
    strategy_id, version_id = await _draft_version(db_client, analyst)
    path = f"/v1/strategies/{strategy_id}/versions/{version_id}"
    changed = await db_client.put(path, headers=manager, json={"steps": VALID_STEPS})
    assert changed.status_code == 200, changed.text
    await submit_with_simulation(db_client, analyst, strategy_id, version_id)
    blocked = await db_client.post(
        path + "/activate", headers=manager, json={"reason": "Self approval"}
    )
    assert blocked.status_code == 403, blocked.text


async def test_old_simulation_cannot_approve_changed_graph(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    strategy_id, version_id = await _draft_version(db_client, analyst)
    sim = await db_client.post(
        "/v1/simulations/single",
        headers=analyst,
        json={"strategy_version_id": version_id, "application_payload": lease_back_motor_payload()},
    )
    assert sim.status_code == 201, sim.text
    steps = copy.deepcopy(VALID_STEPS)
    steps.append(
        {
            "order": 6,
            "type": "CALCULATION",
            "name": "Changed graph",
            "config": {"calculations": ["loan.ltv"]},
        }
    )
    path = f"/v1/strategies/{strategy_id}/versions/{version_id}"
    assert (await db_client.put(path, headers=analyst, json={"steps": steps})).status_code == 200
    rejected = await db_client.post(
        path + "/submit-approval",
        headers=analyst,
        json={"simulation_id": sim.json()["simulation_id"]},
    )
    assert rejected.status_code == 422, rejected.text
    await submit_with_simulation(db_client, analyst, strategy_id, version_id)


async def test_changed_rule_set_invalidates_simulation_then_freezes_on_submission(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    created = await db_client.post(
        "/v1/rule-sets",
        headers=analyst,
        json={"code": unique("AUDIT_RS"), "name": "Audit", "rule_codes": ["DTI_MAX_STANDARD"]},
    )
    assert created.status_code == 201, created.text
    rs = created.json()
    strategy, version = await draft_for_set(db_client, analyst, rs["code"])
    sim = await db_client.post(
        "/v1/simulations/single",
        headers=analyst,
        json={
            "strategy_version_id": version["id"],
            "application_payload": lease_back_motor_payload(),
        },
    )
    assert sim.status_code == 201
    edit = await db_client.put(
        f"/v1/rule-sets/{rs['id']}/members",
        headers=analyst,
        json={"rule_codes": ["BUREAU_DPD_MAX"]},
    )
    assert edit.status_code == 200
    rejected = await db_client.post(
        f"/v1/strategies/{strategy['id']}/versions/{version['id']}/submit-approval",
        headers=analyst,
        json={"simulation_id": sim.json()["simulation_id"]},
    )
    assert rejected.status_code == 422, rejected.text
    await submit_with_simulation(db_client, analyst, strategy["id"], version["id"])
    blocked = await db_client.put(
        f"/v1/rule-sets/{rs['id']}/members",
        headers=analyst,
        json={"rule_codes": ["DTI_MAX_STANDARD"]},
    )
    assert blocked.status_code == 409, blocked.text


async def test_published_rule_set_cannot_be_mutated_by_analyst(db_client: AsyncClient) -> None:
    analyst = await login(db_client, "riskanalyst")
    sets = (await db_client.get("/v1/rule-sets", headers=analyst)).json()
    live = next(row for row in sets if row["code"] == "AFFORDABILITY_STANDARD")
    blocked = await db_client.put(
        f"/v1/rule-sets/{live['id']}/members",
        headers=analyst,
        json={"rule_codes": live["rule_codes"]},
    )
    assert blocked.status_code == 409, blocked.text


async def test_fraud_routing_stays_open_and_cannot_be_self_approved(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    headers = await login(db_client, "underwriter")
    case_id = decision["manual_review_case_id"]
    path = f"/v1/manual-review/cases/{case_id}/decision"
    flagged = await db_client.post(
        path,
        headers=headers,
        json={
            "analyst_decision": "FRAUD_INVESTIGATION",
            "override_reason": "Synthetic identity discrepancy",
        },
    )
    assert flagged.status_code == 200, flagged.text
    assert flagged.json()["status"] == "ESCALATED"
    assert flagged.json()["closed_at"] is None
    assert flagged.json()["priority"] == "HIGH"
    async with get_sessionmaker()() as session:
        app = await session.scalar(
            select(Application).where(Application.application_id == decision["application_id"])
        )
        assert app is not None and app.status == "PENDING_REVIEW"
    blocked = await db_client.post(
        path,
        headers=headers,
        json={"analyst_decision": "APPROVE", "override_reason": "Self approval"},
    )
    assert blocked.status_code == 403, blocked.text


async def test_stale_concurrent_review_cannot_overwrite_closed_case(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    case_id = decision["manual_review_case_id"]
    request = AnalystDecisionRequest(
        analyst_decision=DecisionType.APPROVE, override_reason="Synthetic concurrent review"
    )
    async with get_sessionmaker()() as first, get_sessionmaker()() as second:
        a, b = (
            await review_service.get_case(first, case_id),
            await review_service.get_case(second, case_id),
        )
        u1 = await first.scalar(select(User).where(User.username == "underwriter"))
        u2 = await second.scalar(select(User).where(User.username == "underwriter"))
        assert u1 is not None and u2 is not None

        async def decide(session: Any, case: Any, user: User) -> str:
            try:
                await review_service.decide_case(session, case, request, user)
                return "decided"
            except ConflictError:
                await session.rollback()
                return "conflict"

        outcomes = await asyncio.wait_for(
            asyncio.gather(decide(first, a, u1), decide(second, b, u2)), 15
        )
        assert sorted(outcomes) == ["conflict", "decided"]
    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.entity_id == case_id, AuditLog.event_type == "MANUAL_REVIEW_DECIDED")
        )
        assert count == 1


async def test_unknown_assignee_filter_is_empty(db_client: AsyncClient) -> None:
    await _create_review_case(db_client)
    response = await db_client.get(
        "/v1/manual-review/cases",
        headers=await login(db_client, "underwriter"),
        params={"assigned_to": unique("NONEXISTENT")},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


async def test_cannot_assign_review_to_read_only_auditor(db_client: AsyncClient) -> None:
    case = await _create_review_case(db_client)
    response = await db_client.post(
        f"/v1/manual-review/cases/{case['manual_review_case_id']}/assign",
        headers=await login(db_client, "underwriter"),
        json={"assignee_username": "auditor"},
    )
    assert response.status_code == 422, response.text


async def test_document_resolution_checks_case_and_document_lifecycle(
    db_client: AsyncClient,
) -> None:
    decision = await _create_review_case(db_client)
    headers = await login(db_client, "underwriter")
    path = f"/v1/manual-review/cases/{decision['manual_review_case_id']}"
    requested = await db_client.post(
        path + "/request-documents",
        headers=headers,
        json={"message": "Synthetic request", "document_names": ["Synthetic slip"]},
    )
    assert requested.status_code == 200, requested.text
    doc = requested.json()["documents"][0]["id"]
    resolve = path + f"/documents/{doc}/resolve"
    assert (
        await db_client.post(resolve, headers=headers, json={"status": "REQUESTED"})
    ).status_code == 422
    assert (
        await db_client.post(resolve, headers=headers, json={"status": "RECEIVED"})
    ).status_code == 200
    assert (
        await db_client.post(resolve, headers=headers, json={"status": "WAIVED"})
    ).status_code == 409
    closed = await db_client.post(
        path + "/decision",
        headers=headers,
        json={"analyst_decision": "APPROVE", "override_reason": "Synthetic conclusion"},
    )
    assert closed.status_code == 200, closed.text
    assert (
        await db_client.post(resolve, headers=headers, json={"status": "RECEIVED"})
    ).status_code == 409


@pytest.mark.parametrize("different", [False, True])
async def test_concurrent_idempotency_retries_are_atomic(
    db_client: AsyncClient, different: bool
) -> None:
    headers = {**await login(db_client, "los-client"), "Idempotency-Key": unique("AUDIT_IDEM")}
    first = lease_back_motor_payload()
    second = copy.deepcopy(first)
    if different:
        second["loan"]["requested_amount"] += 100
    responses = await asyncio.wait_for(
        asyncio.gather(
            db_client.post("/v1/decisions", json=first, headers=headers),
            db_client.post("/v1/decisions", json=second, headers=headers),
        ),
        15,
    )
    assert sorted(r.status_code for r in responses) == ([201, 409] if different else [201, 201]), [
        r.text for r in responses
    ]
    if not different:
        assert responses[0].json()["decision_id"] == responses[1].json()["decision_id"]
    async with get_sessionmaker()() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Decision)
            .where(Decision.idempotency_key == headers["Idempotency-Key"])
        )
        assert count == 1


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "actor_type"])
async def test_signed_jwt_must_have_all_required_claims(
    db_client: AsyncClient, missing: str
) -> None:
    async with get_sessionmaker()() as session:
        user = await session.scalar(select(User).where(User.username == "admin"))
        assert user is not None
        claims: dict[str, Any] = {
            "sub": str(user.id),
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=2),
            "actor_type": "USER",
        }
    claims.pop(missing)
    settings = get_settings()
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    response = await db_client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401, response.text


def test_test_fixture_refuses_non_test_database() -> None:
    env = {
        **os.environ,
        "OSCAR_DATABASE_URL": "postgresql+asyncpg://user:not-a-real-secret@127.0.0.1:1/oscar",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import tests.conftest"],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "Refusing destructive test setup" in result.stderr

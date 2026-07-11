"""Managed rule-category catalog integration tests."""

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login


async def test_category_crud_is_audited_and_governs_rule_create(
    db_client: AsyncClient,
) -> None:
    analyst = await login(db_client, "riskanalyst")
    code = f"CUSTOM_{uuid.uuid4().hex[:8].upper()}"
    created = await db_client.post(
        "/v1/rule-categories",
        json={"code": code, "label": "Custom policy"},
        headers=analyst,
    )
    assert created.status_code == 201, created.text
    category = created.json()

    rule_body = {
        "rule_code": f"CATEGORY_RULE_{uuid.uuid4().hex[:8].upper()}",
        "name": "Custom category rule",
        "category": code,
        "condition": {"all": [{"field": "affordability.dti", "operator": ">", "value": 0.4}]},
        "action": {"decision": "MANUAL_REVIEW", "reason_code": "DTI_NEAR_THRESHOLD"},
    }
    accepted = await db_client.post("/v1/rules", json=rule_body, headers=analyst)
    assert accepted.status_code == 201, accepted.text

    deactivated = await db_client.patch(
        f"/v1/rule-categories/{category['id']}",
        json={"active": False},
        headers=analyst,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    rule_body["rule_code"] = f"CATEGORY_RULE_{uuid.uuid4().hex[:8].upper()}"
    blocked = await db_client.post("/v1/rules", json=rule_body, headers=analyst)
    assert blocked.status_code == 422
    assert blocked.json()["error"]["details"][0]["field"] == "category"

    async with get_sessionmaker()() as session:
        events = (
            await session.scalars(
                select(AuditLog).where(AuditLog.entity_id == code).order_by(AuditLog.created_at)
            )
        ).all()
    assert [event.event_type for event in events] == [
        "RULE_CATEGORY_CREATED",
        "RULE_CATEGORY_UPDATED",
    ]


async def test_seeded_categories_list_and_permissions(db_client: AsyncClient) -> None:
    auditor = await login(db_client, "auditor")
    categories = await db_client.get("/v1/rule-categories", headers=auditor)
    assert categories.status_code == 200
    assert "AFFORDABILITY" in {row["code"] for row in categories.json()}

    denied = await db_client.post(
        "/v1/rule-categories",
        json={"code": "AUDITOR_DENIED", "label": "Denied"},
        headers=auditor,
    )
    assert denied.status_code == 403


async def test_expression_authoring_permission_is_admin_only(db_client: AsyncClient) -> None:
    admin = await login(db_client, "admin")
    analyst = await login(db_client, "riskanalyst")

    admin_me = (await db_client.get("/v1/auth/me", headers=admin)).json()
    analyst_me = (await db_client.get("/v1/auth/me", headers=analyst)).json()

    assert "rule.author_expression" in admin_me["permissions"]
    assert "rule.author_expression" not in analyst_me["permissions"]

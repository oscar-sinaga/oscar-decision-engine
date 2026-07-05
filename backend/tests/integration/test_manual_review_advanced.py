"""Advanced manual review tests (Phase 2): SLA, comments, documents, escalation."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


async def _create_case(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = lease_back_motor_payload(applicant={"monthly_income": 7_440_000}, **overrides)
    decision: dict[str, Any] = (await submit(client, payload)).json()
    assert decision["manual_review_case_id"] is not None
    return decision


async def test_case_has_sla_target(db_client: AsyncClient) -> None:
    decision = await _create_case(db_client)
    underwriter = await login(db_client, "underwriter")
    detail = (
        await db_client.get(
            f"/v1/manual-review/cases/{decision['manual_review_case_id']}", headers=underwriter
        )
    ).json()
    # MEDIUM-priority case gets a 24h SLA target and is not yet breached.
    assert detail["sla_due_at"] is not None
    assert detail["sla_breached"] is False


async def test_fraud_case_is_high_priority_with_tighter_sla(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(fraud={"identity_match": False})
    decision = (await submit(db_client, payload)).json()
    underwriter = await login(db_client, "underwriter")
    detail = (
        await db_client.get(
            f"/v1/manual-review/cases/{decision['manual_review_case_id']}", headers=underwriter
        )
    ).json()
    assert detail["priority"] == "HIGH"
    assert detail["sla_due_at"] is not None


async def test_comment_thread(db_client: AsyncClient) -> None:
    decision = await _create_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    detail = (
        await db_client.post(
            f"/v1/manual-review/cases/{case_id}/comments",
            json={"body": "Called applicant to verify income; awaiting slip."},
            headers=underwriter,
        )
    ).json()
    assert len(detail["comments"]) == 1
    assert detail["comments"][0]["author_label"] == "underwriter"
    assert "verify income" in detail["comments"][0]["body"]

    # Compliance can read but comment permission is manual_review.view.
    await db_client.post(
        f"/v1/manual-review/cases/{case_id}/comments",
        json={"body": "Second note"},
        headers=underwriter,
    )
    latest = (await db_client.get(f"/v1/manual-review/cases/{case_id}", headers=underwriter)).json()
    assert len(latest["comments"]) == 2

    async with get_sessionmaker()() as session:
        events = (
            await session.scalars(
                select(AuditLog).where(
                    AuditLog.event_type == "MANUAL_REVIEW_COMMENT_ADDED",
                    AuditLog.entity_id == case_id,
                )
            )
        ).all()
    assert len(events) == 2


async def test_document_checklist_lifecycle(db_client: AsyncClient) -> None:
    decision = await _create_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    requested = (
        await db_client.post(
            f"/v1/manual-review/cases/{case_id}/request-documents",
            json={
                "message": "Need income evidence",
                "document_names": ["Latest salary slip", "Bank statement 3 months"],
            },
            headers=underwriter,
        )
    ).json()
    assert requested["status"] == "PENDING_DOCUMENTS"
    assert len(requested["documents"]) == 2
    assert all(d["status"] == "REQUESTED" for d in requested["documents"])

    doc_id = requested["documents"][0]["id"]
    resolved = (
        await db_client.post(
            f"/v1/manual-review/cases/{case_id}/documents/{doc_id}/resolve",
            json={"status": "RECEIVED"},
            headers=underwriter,
        )
    ).json()
    received = next(d for d in resolved["documents"] if d["id"] == doc_id)
    assert received["status"] == "RECEIVED"
    assert received["resolved_at"] is not None


async def test_escalation_records_target(db_client: AsyncClient) -> None:
    decision = await _create_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    detail = (
        await db_client.post(
            f"/v1/manual-review/cases/{case_id}/escalate",
            json={
                "reason": "Collateral value needs supervisor sign-off",
                "escalated_to": "SENIOR_UNDERWRITER",
            },
            headers=underwriter,
        )
    ).json()
    assert detail["status"] == "ESCALATED"
    assert detail["escalated_to"] == "SENIOR_UNDERWRITER"

    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "MANUAL_REVIEW_ESCALATED",
                AuditLog.entity_id == case_id,
            )
        )
    assert event is not None
    assert event.after_value is not None
    assert event.after_value["escalated_to"] == "SENIOR_UNDERWRITER"

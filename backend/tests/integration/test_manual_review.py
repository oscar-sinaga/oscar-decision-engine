"""Manual review workflow tests (docs/13, Epic 8)."""

from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.shared.database.session import get_sessionmaker
from tests.conftest import login
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


async def _create_review_case(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    """Submit a borderline-DTI application, returning the decision response."""
    payload = lease_back_motor_payload(applicant={"monthly_income": 7_440_000}, **overrides)
    decision: dict[str, Any] = (await submit(client, payload)).json()
    assert decision["manual_review_case_id"] is not None
    return decision


async def test_queue_lists_and_filters_cases(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client, channel="MR_QUEUE_TEST")
    underwriter = await login(db_client, "underwriter")

    queue = await db_client.get(
        "/v1/manual-review/cases", params={"status": "NEW"}, headers=underwriter
    )
    assert queue.status_code == 200
    items = queue.json()["items"]
    target = next(i for i in items if i["case_id"] == decision["manual_review_case_id"])
    assert target["system_decision"] == "MANUAL_REVIEW"
    assert "DTI_NEAR_THRESHOLD" in target["system_reason_codes"]
    assert target["priority"] == "MEDIUM"
    assert target["application_id"] == decision["application_id"]


async def test_case_detail_shows_masked_context(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    underwriter = await login(db_client, "underwriter")
    detail = await db_client.get(
        f"/v1/manual-review/cases/{decision['manual_review_case_id']}", headers=underwriter
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["decision_id"] == decision["decision_id"]
    assert body["trace_id"] == decision["trace_id"]
    assert body["loan_summary"]["requested_amount"] == 15_000_000
    assert body["vehicle_summary"]["brand"] == "Honda"
    assert body["analyst_decision"] is None


async def test_assign_and_decide_with_override(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    assigned = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/assign", json={}, headers=underwriter
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "ASSIGNED"
    assert assigned.json()["assigned_to"] == "underwriter"

    # Override without a reason is rejected.
    missing_reason = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={"analyst_decision": "APPROVE_WITH_CONDITION", "approved_limit": 10_000_000},
        headers=underwriter,
    )
    assert missing_reason.status_code == 422

    decided = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={
            "analyst_decision": "APPROVE_WITH_CONDITION",
            "approved_limit": 10_000_000,
            "approved_tenor_months": 12,
            "override_reason": "Verified income document; reduced limit to acceptable LTV",
            "notes": "Customer provided updated salary slip.",
        },
        headers=underwriter,
    )
    assert decided.status_code == 200, decided.text
    body = decided.json()
    assert body["status"] == "APPROVED_BY_ANALYST"
    assert body["analyst_decision"] == "APPROVE_WITH_CONDITION"
    assert body["analyst_decided_by"] == "underwriter"
    assert body["approved_limit"] == 10_000_000
    assert body["closed_at"] is not None
    # System decision remains separate and unchanged.
    assert body["system_decision"] == "MANUAL_REVIEW"
    system = await db_client.get(f"/v1/decisions/{decision['decision_id']}", headers=underwriter)
    assert system.json()["decision"] == "MANUAL_REVIEW"

    async with get_sessionmaker()() as session:
        events = (
            await session.scalars(
                select(AuditLog).where(AuditLog.entity_id == case_id).order_by(AuditLog.created_at)
            )
        ).all()
    event_types = [e.event_type for e in events]
    assert "MANUAL_REVIEW_CASE_CREATED" in event_types
    assert "MANUAL_REVIEW_CASE_ASSIGNED" in event_types
    assert "MANUAL_REVIEW_DECIDED" in event_types
    assert "MANUAL_REVIEW_OVERRIDDEN" in event_types
    override_event = next(e for e in events if e.event_type == "MANUAL_REVIEW_OVERRIDDEN")
    assert override_event.before_value == {"system_decision": "MANUAL_REVIEW"}
    assert override_event.after_value == {"analyst_decision": "APPROVE_WITH_CONDITION"}
    assert override_event.reason is not None

    # Closed case cannot be decided again.
    again = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={
            "analyst_decision": "REJECT",
            "override_reason_code": "HIGH_DTI",
            "override_reason": "x",
        },
        headers=underwriter,
    )
    assert again.status_code == 409


async def test_reject_requires_reason_code(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    missing_code = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={"analyst_decision": "REJECT", "override_reason": "insufficient income evidence"},
        headers=underwriter,
    )
    assert missing_code.status_code == 422

    rejected = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={
            "analyst_decision": "REJECT",
            "override_reason_code": "HIGH_DTI",
            "override_reason": "Income cannot be verified at required level",
        },
        headers=underwriter,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED_BY_ANALYST"


async def test_fraud_case_approval_requires_override_permission(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(fraud={"identity_match": False})
    decision = (await submit(db_client, payload)).json()
    assert decision["decision"] == "FRAUD_INVESTIGATION"
    case_id = decision["manual_review_case_id"]

    underwriter = await login(db_client, "underwriter")
    denied = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={
            "analyst_decision": "APPROVE",
            "override_reason": "identity verified in branch",
        },
        headers=underwriter,
    )
    assert denied.status_code == 403

    manager = await login(db_client, "riskmanager")
    approved = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/decision",
        json={
            "analyst_decision": "APPROVE",
            "override_reason": "Identity re-verified with original documents in branch",
        },
        headers=manager,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED_BY_ANALYST"


async def test_escalate_and_request_documents(db_client: AsyncClient) -> None:
    decision = await _create_review_case(db_client)
    case_id = decision["manual_review_case_id"]
    underwriter = await login(db_client, "underwriter")

    docs = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/request-documents",
        json={"message": "Please provide latest salary slip"},
        headers=underwriter,
    )
    assert docs.status_code == 200
    assert docs.json()["status"] == "PENDING_DOCUMENTS"
    assert "salary slip" in docs.json()["notes"]

    escalated = await db_client.post(
        f"/v1/manual-review/cases/{case_id}/escalate",
        json={"reason": "Needs supervisor judgement on collateral"},
        headers=underwriter,
    )
    assert escalated.status_code == 200
    assert escalated.json()["status"] == "ESCALATED"


async def test_queue_requires_view_permission(db_client: AsyncClient) -> None:
    los = await login(db_client, "los-client")
    denied = await db_client.get("/v1/manual-review/cases", headers=los)
    assert denied.status_code == 403

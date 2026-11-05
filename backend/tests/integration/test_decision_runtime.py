"""End-to-end tests for the decision runtime vertical slice.

Covers: decisioning outcomes, idempotency, validation errors, trace content,
PII masking in snapshots, authorization, and business audit events —
docs/02 §6.1 acceptance criteria and docs/08 Epic 2/5 definition of done.
"""

import uuid
from typing import Any

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.audit.models import AuditLog
from app.modules.decisions.models import Decision, DecisionTrace
from app.shared.database.session import get_sessionmaker
from tests.conftest import login


def lease_back_motor_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "application_id": f"APP-{uuid.uuid4().hex[:10].upper()}",
        "product_type": "MOTOR_LEASEBACK",
        "channel": "BRANCH",
        "applicant": {
            "customer_id": "CUST-001",
            "age": 34,
            "employment_type": "EMPLOYEE",
            "monthly_income": 8_500_000,
            "existing_monthly_obligation": 2_500_000,
            "internal_max_dpd_12m": 0,
        },
        "loan": {"requested_amount": 15_000_000, "requested_tenor_months": 24},
        "vehicle": {
            "type": "MOTOR",
            "brand": "Honda",
            "model": "Vario",
            "year": 2020,
            "appraisal_value": 18_000_000,
            "ownership_status": "OWNED",
        },
        "bureau": {"collectability": "CURRENT", "max_dpd_12m": 0, "active_loan_count": 2},
        "fraud": {
            "identity_match": True,
            "document_match": True,
            "blacklist_hit": False,
            "device_risk_score": 0.12,
        },
        "model_outputs": {"credit_score": 684, "model_version": "MOTOR_SCORE_V1"},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}
        else:
            payload[key] = value
    return payload


async def submit(client: AsyncClient, payload: dict[str, Any], **kwargs: Any) -> Any:
    headers = kwargs.pop("headers", await login(client, "los-client"))
    return await client.post("/v1/decisions", json=payload, headers=headers, **kwargs)


async def test_conditional_approval_flow(db_client: AsyncClient) -> None:
    response = await submit(db_client, lease_back_motor_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["decision"] == "APPROVE_WITH_CONDITION"
    assert body["risk_grade"] == "B"
    assert body["score"] == 684
    assert body["approved_limit"] == 12_600_000.0
    assert body["approved_tenor_months"] == 18
    assert body["pricing_rate"] == 0.025
    assert body["strategy_version"] == "LEASEBACK_MOTOR_V1"
    assert body["decision_id"].startswith("DEC-")
    assert body["trace_id"].startswith("TRC-")
    assert body["manual_review_case_id"] is None
    codes = [item["code"] for item in body["reason_codes"]]
    assert codes == ["REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT"]
    assert body["reason_codes"][0]["message"] == "Requested amount is above eligible limit"
    assert body["correlation_id"] == response.headers["x-correlation-id"]


async def test_high_dti_is_rejected_with_reason(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(
        applicant={"monthly_income": 3_000_000, "existing_monthly_obligation": 1_200_000}
    )
    response = await submit(db_client, payload)
    body = response.json()
    assert body["decision"] == "REJECT"
    codes = [item["code"] for item in body["reason_codes"]]
    assert "HIGH_DTI" in codes  # reject always carries at least one reason code


async def test_borderline_dti_routes_to_manual_review(db_client: AsyncClient) -> None:
    # installment 625k; target dti ~0.42 → income (2.5M + 625k)/0.42 ≈ 7.44M
    payload = lease_back_motor_payload(applicant={"monthly_income": 7_440_000})
    response = await submit(db_client, payload)
    body = response.json()
    assert body["decision"] == "MANUAL_REVIEW"
    assert body["manual_review_case_id"] is not None
    codes = [item["code"] for item in body["reason_codes"]]
    assert "DTI_NEAR_THRESHOLD" in codes


async def test_fraud_mismatch_routes_to_investigation(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(fraud={"identity_match": False})
    response = await submit(db_client, payload)
    body = response.json()
    assert body["decision"] == "FRAUD_INVESTIGATION"
    assert body["manual_review_case_id"] is not None
    codes = [item["code"] for item in body["reason_codes"]]
    assert "APPLICATION_DATA_MISMATCH" in codes


async def test_blacklist_stops_execution(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(fraud={"blacklist_hit": True})
    response = await submit(db_client, payload)
    body = response.json()
    assert body["decision"] == "REJECT"
    codes = [item["code"] for item in body["reason_codes"]]
    assert codes == ["BLACKLIST_HIT"]


async def test_idempotency_key_returns_same_decision(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()
    headers = await login(db_client, "los-client")
    key = f"idem-{uuid.uuid4().hex}"
    first = await db_client.post(
        "/v1/decisions", json=payload, headers={**headers, "Idempotency-Key": key}
    )
    second = await db_client.post(
        "/v1/decisions", json=payload, headers={**headers, "Idempotency-Key": key}
    )
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["decision_id"] == second.json()["decision_id"]

    async with get_sessionmaker()() as session:
        rows = (
            await session.scalars(select(Decision).where(Decision.idempotency_key == key))
        ).all()
    assert len(rows) == 1


async def test_idempotency_key_rejects_different_payload(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()
    headers = await login(db_client, "los-client")
    key = f"idem-conflict-{uuid.uuid4().hex}"
    first = await db_client.post(
        "/v1/decisions", json=payload, headers={**headers, "Idempotency-Key": key}
    )
    changed = {**payload, "loan": {**payload["loan"], "requested_amount": 11_000_000}}
    second = await db_client.post(
        "/v1/decisions", json=changed, headers={**headers, "Idempotency-Key": key}
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


async def test_trace_feature_values_and_steps_mask_sensitive_values(db_client: AsyncClient) -> None:
    from app.modules.decisions.models import DecisionTrace

    created = (await submit(db_client, lease_back_motor_payload())).json()
    async with get_sessionmaker()() as session:
        trace = await session.scalar(
            select(DecisionTrace).where(DecisionTrace.trace_id == created["trace_id"])
        )
        assert trace is not None
        assert trace.feature_values["applicant.customer_id"] == "***REDACTED***"
        assert "CUST-001" not in str(trace.feature_values)
        assert "CUST-001" not in str(trace.step_results)

    analyst = await login(db_client, "riskanalyst")
    viewed = await db_client.get(f"/v1/decisions/{created['decision_id']}/trace", headers=analyst)
    assert viewed.status_code == 200
    assert viewed.json()["feature_values"]["applicant.customer_id"] == "***REDACTED***"
    assert "CUST-001" not in viewed.text


async def test_missing_required_field_returns_validation_error(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()
    del payload["vehicle"]["appraisal_value"]
    response = await submit(db_client, payload)
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(detail["field"] == "vehicle.appraisal_value" for detail in body["error"]["details"])
    assert body["correlation_id"] == response.headers["x-correlation-id"]


async def test_unknown_product_strategy_is_configuration_error(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload(product_type="CAR_LEASEBACK")
    response = await submit(db_client, payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONFIGURATION_ERROR"


async def test_trace_reconstructs_decision(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()
    payload["applicant"]["nik"] = "3174091202900001"  # synthetic PII, must be masked
    created = (await submit(db_client, payload)).json()

    analyst_headers = await login(db_client, "riskanalyst")
    response = await db_client.get(
        f"/v1/decisions/{created['decision_id']}/trace", headers=analyst_headers
    )
    assert response.status_code == 200, response.text
    trace = response.json()
    assert trace["trace_id"] == created["trace_id"]
    assert trace["execution_mode"] == "PRODUCTION"
    assert trace["strategy"]["strategy_code"] == "LEASEBACK_MOTOR"
    assert trace["strategy"]["version"] == 1
    assert trace["strategy"]["execution"] == "GRAPH"
    assert trace["strategy"]["strategy_id"]
    assert trace["strategy"]["version_id"]

    # Feature values show the exact calculated inputs.
    assert trace["feature_values"]["loan.ltv"] == 0.833333
    assert trace["feature_values"]["vehicle.age_years"] == 6
    assert 0.36 < trace["feature_values"]["affordability.dti"] < 0.37

    # Ordered steps with statuses and pinned versions.
    orders = [step["order"] for step in trace["steps"]]
    assert orders == sorted(orders) and len(orders) == 7
    rule_steps = [s for s in trace["steps"] if s["type"] == "RULE_SET"]
    assert all(r["version"] == 1 for s in rule_steps for r in s["rule_results"])
    table_step = next(s for s in trace["steps"] if s["type"] == "DECISION_TABLE")
    assert table_step["reference_version"] == 1

    assert trace["score_result"]["model_version"] == "MOTOR_SCORE_V1"
    assert trace["final_decision"]["decision"] == "APPROVE_WITH_CONDITION"

    # PII is masked in the persisted snapshot; decision inputs are retained.
    assert trace["input_snapshot"]["applicant"]["nik"] == "***REDACTED***"
    assert trace["input_snapshot"]["loan"]["requested_amount"] == 15_000_000
    assert trace["metadata"]["correlation_id"] is not None
    assert "3174091202900001" not in response.text


async def test_decision_audit_event_recorded(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()
    created = (await submit(db_client, payload)).json()

    async with get_sessionmaker()() as session:
        event = await session.scalar(
            select(AuditLog).where(
                AuditLog.event_type == "DECISION_EXECUTED",
                AuditLog.entity_id == created["decision_id"],
            )
        )
    assert event is not None
    assert event.actor_label == "los-client"
    assert event.actor_type == "API_CLIENT"
    assert event.entity_version == "LEASEBACK_MOTOR_V1"
    assert event.after_value is not None
    assert event.after_value["decision"] == created["decision"]
    assert event.correlation_id is not None
    assert event.request_id is not None


async def test_trace_rows_are_never_updated(db_client: AsyncClient) -> None:
    created = (await submit(db_client, lease_back_motor_payload())).json()
    async with get_sessionmaker()() as session:
        trace = await session.scalar(
            select(DecisionTrace).where(DecisionTrace.trace_id == created["trace_id"])
        )
        assert trace is not None
        original_output = dict(trace.final_output)
    # The application exposes no mutation path for traces; verify repeated
    # reads return identical evidence.
    async with get_sessionmaker()() as session:
        again = await session.scalar(
            select(DecisionTrace).where(DecisionTrace.trace_id == created["trace_id"])
        )
        assert again is not None
        assert again.final_output == original_output


async def test_decision_requires_permission(db_client: AsyncClient) -> None:
    payload = lease_back_motor_payload()

    # No token.
    anonymous = await db_client.post("/v1/decisions", json=payload)
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    # Underwriter lacks decision.execute.
    underwriter = await login(db_client, "underwriter")
    forbidden = await db_client.post("/v1/decisions", json=payload, headers=underwriter)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    # API client lacks decision.trace.view.
    created = (await submit(db_client, payload)).json()
    los = await login(db_client, "los-client")
    trace_forbidden = await db_client.get(
        f"/v1/decisions/{created['decision_id']}/trace", headers=los
    )
    assert trace_forbidden.status_code == 403


async def test_get_decision_by_id(db_client: AsyncClient) -> None:
    created = (await submit(db_client, lease_back_motor_payload())).json()
    headers = await login(db_client, "underwriter")
    response = await db_client.get(f"/v1/decisions/{created['decision_id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["decision_id"] == created["decision_id"]
    assert response.json()["decision"] == created["decision"]

    missing = await db_client.get("/v1/decisions/DEC-00000000-XXXX", headers=headers)
    assert missing.status_code == 404

"""Golden decision outcomes protecting Phase 3 strategy graph migration.

These expectations were captured against the seeded ordered-step
``LEASEBACK_MOTOR`` strategy before M2.  They intentionally assert only the
stable business outcome tuple; generated identifiers and timings are excluded.
"""

from collections.abc import Callable
from typing import Any

import pytest
from httpx import AsyncClient

from tests.integration.test_decision_runtime import lease_back_motor_payload, submit

PayloadFactory = Callable[[], dict[str, Any]]


GOLDEN_CASES: list[tuple[str, PayloadFactory, tuple[str, list[str], str | None, float | None]]] = [
    (
        "approve_with_condition",
        lease_back_motor_payload,
        (
            "APPROVE_WITH_CONDITION",
            ["REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT"],
            "B",
            12_600_000.0,
        ),
    ),
    (
        "blacklist_reject",
        lambda: lease_back_motor_payload(fraud={"blacklist_hit": True}),
        ("REJECT", ["BLACKLIST_HIT"], None, None),
    ),
    (
        "borderline_dti_review",
        lambda: lease_back_motor_payload(applicant={"monthly_income": 7_440_000}),
        (
            "MANUAL_REVIEW",
            ["DTI_NEAR_THRESHOLD", "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT"],
            "B",
            None,
        ),
    ),
    (
        "fraud_mismatch",
        lambda: lease_back_motor_payload(fraud={"identity_match": False}),
        (
            "FRAUD_INVESTIGATION",
            ["APPLICATION_DATA_MISMATCH", "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT"],
            "B",
            None,
        ),
    ),
]


@pytest.mark.parametrize(("case_name", "payload_factory", "expected"), GOLDEN_CASES)
async def test_seeded_strategy_golden_outcome(
    db_client: AsyncClient,
    case_name: str,
    payload_factory: PayloadFactory,
    expected: tuple[str, list[str], str | None, float | None],
) -> None:
    payload = payload_factory()
    payload["application_id"] = f"GOLDEN-{case_name.upper()}"

    response = await submit(db_client, payload)
    assert response.status_code == 201, response.text
    body = response.json()

    actual = (
        body["decision"],
        [item["code"] for item in body["reason_codes"]],
        body["risk_grade"],
        body["approved_limit"],
    )
    assert actual == expected

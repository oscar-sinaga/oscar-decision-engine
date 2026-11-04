"""Regressions found by the November follow-up audit, not happy-path smoke tests."""

import math

import pytest
from pydantic import ValidationError

from app.engine.decision_table import find_overlapping_rows, parse_decision_table_config
from app.engine.dsl import Condition, Operator
from app.engine.evaluator import evaluate_condition
from app.engine.scorecard import parse_scorecard_config, resolve_score
from app.modules.decisions.schemas import DecisionRequest


@pytest.mark.parametrize("operator,expected", [("=", True), ("in", [True])])
def test_boolean_is_not_the_number_one(operator: str, expected: object) -> None:
    condition = Condition(field="fraud.blacklist_hit", operator=Operator(operator), value=expected)
    assert evaluate_condition(condition, {"fraud.blacklist_hit": 1})[0] is False


def test_integer_order_does_not_round_at_float_precision_boundary() -> None:
    condition = Condition(field="loan.amount", operator=Operator.GT, value=2**53)
    assert evaluate_condition(condition, {"loan.amount": 2**53 + 1})[0] is True


def test_iso_date_ordering_is_supported_by_the_runtime() -> None:
    condition = Condition(field="applicant.date", operator=Operator.GT, value="2026-01-01")
    assert evaluate_condition(condition, {"applicant.date": "2026-11-04"})[0] is True


@pytest.mark.parametrize("operator", [Operator.IN, Operator.NOT_IN])
def test_membership_operator_requires_value_even_when_omitted(operator: Operator) -> None:
    with pytest.raises(ValidationError):
        Condition(field="applicant.kind", operator=operator)


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_non_finite_score_never_gets_a_risk_grade(bad: float) -> None:
    config = parse_scorecard_config({"bands": [{"min_score": 0, "risk_grade": "A"}]})
    outcome = resolve_score(config, {"model_outputs.credit_score": bad})
    assert outcome.score_missing
    assert outcome.score is None
    assert outcome.risk_grade is None


@pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
def test_invalid_json_numbers_are_rejected_at_request_boundary(bad: float) -> None:
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate(
            {
                "application_id": "SYNTHETIC",
                "product_type": "MOTOR_LEASEBACK",
                "loan": {"amount": bad},
            }
        )


def test_ambiguous_dotted_payload_keys_are_not_accepted() -> None:
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate(
            {
                "application_id": "SYNTHETIC",
                "product_type": "MOTOR_LEASEBACK",
                "applicant": {"x.y": 1},
            }
        )


def test_date_overlap_analysis_does_not_crash_on_valid_date_conditions() -> None:
    config = parse_decision_table_config(
        {
            "rows": [
                {
                    "conditions": [
                        {"field": "applicant.date", "operator": ">", "value": "2026-01-01"}
                    ],
                    "output": {"decision": "MANUAL_REVIEW"},
                },
                {
                    "conditions": [
                        {"field": "applicant.date", "operator": "<", "value": "2026-12-01"}
                    ],
                    "output": {"decision": "REJECT"},
                },
            ]
        }
    )
    assert find_overlapping_rows(config) == [(0, 1)]

"""Financial persistence bounds and deterministic comparison properties."""

import math
import random
from typing import Any

import pytest
from pydantic import ValidationError

from app.engine.decision_table import (
    DecisionTableConfig,
    TableOutput,
    TableRow,
    find_overlapping_rows,
    parse_decision_table_config,
)
from app.engine.dsl import Condition, Operator
from app.engine.evaluator import evaluate_condition
from app.engine.executor import ExecutablePlan, StepPlan, run_strategy
from app.engine.scorecard import parse_scorecard_config, resolve_score
from app.modules.manual_review.schemas import AnalystDecisionRequest
from app.shared.domain.enums import DecisionType, StepType


@pytest.mark.parametrize(
    "field,value",
    [
        ("approved_limit", math.inf),
        ("approved_limit", math.nan),
        ("approved_limit", -1),
        ("approved_limit", 1e16),
        ("approved_limit", True),
        ("approved_limit", "1000"),
        ("approved_tenor_months", 0),
        ("approved_tenor_months", True),
        ("approved_tenor_months", 2**31),
        ("pricing_rate", math.inf),
        ("pricing_rate", -0.1),
        ("pricing_rate", 1000),
    ],
)
def test_table_financial_terms_must_fit_persistence(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        TableOutput.model_validate({"decision": "APPROVE", field: value})


@pytest.mark.parametrize("field,value", [("approved_limit", 1e16), ("approved_tenor_months", 2**31)])
def test_manual_terms_must_fit_persistence(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        AnalystDecisionRequest.model_validate({"analyst_decision": "APPROVE", field: value})


@pytest.mark.parametrize("score", [1e300, -1e300, 100_000_000])
def test_unrepresentable_scores_take_missing_score_fallback(score: float) -> None:
    config = parse_scorecard_config({"bands": [{"min_score": 0, "risk_grade": "A"}]})
    result = resolve_score(config, {"model_outputs.credit_score": score})
    assert result.score_missing
    assert result.score is None
    assert result.risk_grade is None


def test_fallback_grade_cannot_overflow_database_string() -> None:
    with pytest.raises(ValidationError):
        parse_scorecard_config(
            {
                "bands": [{"min_score": 0, "risk_grade": "A"}],
                "below_bands_risk_grade": "TOO_LONG",
            }
        )


def test_oversized_calculated_limit_takes_engine_error_path() -> None:
    table = parse_decision_table_config(
        {
            "rows": [
                {
                    "conditions": [],
                    "output": {
                        "decision": "APPROVE",
                        "approved_limit_pct_of": {"field": "vehicle.appraisal_value", "pct": 0.9},
                    },
                }
            ]
        }
    )
    plan = ExecutablePlan(
        strategy_code="SYNTHETIC_BOUNDS",
        strategy_version=1,
        strategy_version_id="synthetic-version",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        steps=[
            StepPlan(
                order=1,
                step_type=StepType.DECISION_TABLE,
                name="Oversized limit",
                decision_table=table,
            )
        ],
    )
    result = run_strategy(plan, {"vehicle": {"appraisal_value": 1e300}})
    assert result.final_decision is DecisionType.ERROR
    assert result.approved_limit is None
    assert result.errors


def test_typed_equality_deterministic_properties() -> None:
    rng = random.Random(7611)
    values = [False, True, -2, -1, 0, 1, 2, 2**53, 2**53 + 1, "a", "b", "2026-01-01", None]
    for _ in range(10_000):
        actual, expected = rng.choice(values), rng.choice(values)
        condition = Condition(field="x", operator=Operator.EQ, value=expected)
        matched = evaluate_condition(condition, {"x": actual})[0]
        reference = actual == expected
        if isinstance(actual, bool) or isinstance(expected, bool):
            reference = type(actual) is bool and type(expected) is bool and actual == expected
        assert matched is reference


def test_overlap_detector_has_no_false_negatives_on_sampled_numeric_domain() -> None:
    rng = random.Random(7611)
    for _ in range(2_000):
        conditions = [
            Condition(
                field="x",
                operator=Operator(rng.choice([">", ">=", "<", "<=", "="])),
                value=rng.randint(-5, 5),
            )
            for _ in range(4)
        ]
        rows = [
            TableRow(
                conditions=conditions[:2],
                output=TableOutput(decision=DecisionType.MANUAL_REVIEW),
            ),
            TableRow(conditions=conditions[2:], output=TableOutput(decision=DecisionType.REJECT)),
        ]
        detected = bool(find_overlapping_rows(DecisionTableConfig(rows=rows)))
        common_input = any(
            all(evaluate_condition(c, {"x": i / 2})[0] for c in conditions)
            for i in range(-12, 13)
        )
        assert not common_input or detected

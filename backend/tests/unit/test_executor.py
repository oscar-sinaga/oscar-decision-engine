"""Executor unit tests using an in-memory plan (no database)."""

from typing import Any

from app.engine.decision_table import parse_decision_table_config
from app.engine.dsl import parse_rule_definition
from app.engine.executor import (
    ExecutablePlan,
    ResolvedRule,
    StepPlan,
    most_severe,
    run_strategy,
)
from app.engine.scorecard import parse_scorecard_config
from app.shared.domain.enums import DecisionType, StepOnError, StepType


def _rule(code: str, condition: dict[str, Any], action: dict[str, Any]) -> ResolvedRule:
    return ResolvedRule(
        rule_code=code, version=1, definition=parse_rule_definition(condition, action)
    )


def _plan(steps: list[StepPlan]) -> ExecutablePlan:
    return ExecutablePlan(
        strategy_code="TEST_STRATEGY",
        strategy_version=1,
        strategy_version_id="00000000-0000-0000-0000-000000000000",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        steps=steps,
    )


BASE_PAYLOAD: dict[str, Any] = {
    "application_id": "APP-T-1",
    "product_type": "MOTOR_LEASEBACK",
    "applicant": {"age": 34, "monthly_income": 8_500_000, "existing_monthly_obligation": 2_500_000},
    "loan": {"requested_amount": 15_000_000, "requested_tenor_months": 24},
    "vehicle": {"type": "MOTOR", "year": 2020, "appraisal_value": 18_000_000},
    "fraud": {"blacklist_hit": False},
    "model_outputs": {"credit_score": 684, "model_version": "MOTOR_SCORE_V1"},
}


def test_severity_ordering() -> None:
    assert most_severe([DecisionType.APPROVE, DecisionType.REJECT]) is DecisionType.REJECT
    assert (
        most_severe([DecisionType.MANUAL_REVIEW, DecisionType.FRAUD_INVESTIGATION])
        is DecisionType.FRAUD_INVESTIGATION
    )
    assert most_severe([]) is None


def test_validation_step_blocks_execution() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.VALIDATION,
                name="Required",
                config={"required_fields": ["vehicle.appraisal_value"]},
            ),
            StepPlan(
                order=2,
                step_type=StepType.CALCULATION,
                name="Calc",
                config={"calculations": ["loan.ltv"]},
            ),
        ]
    )
    payload = {**BASE_PAYLOAD, "vehicle": {"type": "MOTOR", "year": 2020}}
    result = run_strategy(plan, payload)
    assert result.final_decision is DecisionType.ERROR
    assert result.validation_failures[0].field == "vehicle.appraisal_value"
    assert result.step_results[1]["status"] == "SKIPPED"


def test_calculation_and_rule_flow() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.CALCULATION,
                name="Calc",
                config={"calculations": ["loan.ltv", "affordability.dti", "vehicle.age_years"]},
            ),
            StepPlan(
                order=2,
                step_type=StepType.RULE_SET,
                name="Rules",
                rules=[
                    _rule(
                        "LTV_MAX",
                        {"all": [{"field": "loan.ltv", "operator": ">", "value": 0.85}]},
                        {"decision": "MANUAL_REVIEW", "reason_code": "LTV_ABOVE_THRESHOLD"},
                    )
                ],
            ),
        ]
    )
    result = run_strategy(plan, BASE_PAYLOAD)
    # LTV = 15M/18M = 0.8333 → rule does not match → no candidate → conservative fallback.
    assert result.feature_values["loan.ltv"] == 0.833333
    assert result.final_decision is DecisionType.MANUAL_REVIEW
    assert "NO_DECISION_PRODUCED" in result.reason_codes


def test_stop_execution_skips_remaining_steps() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.RULE_SET,
                name="Fraud",
                rules=[
                    _rule(
                        "BLACKLIST",
                        {"all": [{"field": "fraud.blacklist_hit", "operator": "=", "value": True}]},
                        {
                            "type": "STOP_EXECUTION",
                            "decision": "REJECT",
                            "reason_code": "BLACKLIST_HIT",
                        },
                    )
                ],
            ),
            StepPlan(
                order=2,
                step_type=StepType.CALCULATION,
                name="Calc",
                config={"calculations": ["loan.ltv"]},
            ),
        ]
    )
    payload = {**BASE_PAYLOAD, "fraud": {"blacklist_hit": True}}
    result = run_strategy(plan, payload)
    assert result.final_decision is DecisionType.REJECT
    assert result.reason_codes == ["BLACKLIST_HIT"]
    assert result.step_results[1]["status"] == "SKIPPED"


def test_most_severe_candidate_wins_over_table_output() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.RULE_SET,
                name="Fraud",
                rules=[
                    _rule(
                        "MISMATCH",
                        {
                            "any": [
                                {"field": "fraud.identity_match", "operator": "=", "value": False}
                            ]
                        },
                        {
                            "decision": "FRAUD_INVESTIGATION",
                            "reason_code": "APPLICATION_DATA_MISMATCH",
                        },
                    )
                ],
            ),
            StepPlan(
                order=2,
                step_type=StepType.SCORECARD,
                name="Score",
                reference_code="SC",
                reference_version=1,
                scorecard=parse_scorecard_config({"bands": [{"min_score": 0, "risk_grade": "A"}]}),
            ),
            StepPlan(
                order=3,
                step_type=StepType.DECISION_TABLE,
                name="Final",
                reference_code="DT",
                reference_version=1,
                decision_table=parse_decision_table_config(
                    {
                        "rows": [
                            {
                                "conditions": [
                                    {"field": "score.risk_grade", "operator": "=", "value": "A"}
                                ],
                                "output": {"decision": "APPROVE"},
                            }
                        ]
                    }
                ),
            ),
        ]
    )
    payload = {**BASE_PAYLOAD, "fraud": {"identity_match": False}}
    result = run_strategy(plan, payload)
    assert result.final_decision is DecisionType.FRAUD_INVESTIGATION
    # Approval outputs are not attached to a non-approval decision.
    assert result.approved_limit is None


def test_step_error_fallback_routes_to_manual_review() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.SCORECARD,
                name="Broken Scorecard",
                on_error=StepOnError.MANUAL_REVIEW,
                scorecard=None,  # triggers a step execution error
            ),
        ]
    )
    result = run_strategy(plan, BASE_PAYLOAD)
    assert result.final_decision is DecisionType.MANUAL_REVIEW
    assert "STEP_EXECUTION_ERROR" in result.reason_codes
    assert result.errors and result.errors[0]["on_error"] == "MANUAL_REVIEW"


def test_conditional_approval_when_limit_below_requested() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.CALCULATION,
                name="Calc",
                config={"calculations": ["loan.ltv"]},
            ),
            StepPlan(
                order=2,
                step_type=StepType.SCORECARD,
                name="Score",
                reference_code="SC",
                reference_version=1,
                scorecard=parse_scorecard_config(
                    {"bands": [{"min_score": 650, "risk_grade": "B"}]}
                ),
            ),
            StepPlan(
                order=3,
                step_type=StepType.DECISION_TABLE,
                name="Final",
                reference_code="DT",
                reference_version=1,
                decision_table=parse_decision_table_config(
                    {
                        "above_limit_reason_code": "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT",
                        "rows": [
                            {
                                "conditions": [
                                    {"field": "score.risk_grade", "operator": "=", "value": "B"}
                                ],
                                "output": {
                                    "decision": "APPROVE",
                                    "approved_limit_pct_of": {
                                        "field": "vehicle.appraisal_value",
                                        "pct": 0.7,
                                    },
                                    "approved_tenor_months": 18,
                                    "pricing_rate": 0.025,
                                },
                            }
                        ],
                    }
                ),
            ),
        ]
    )
    result = run_strategy(plan, BASE_PAYLOAD)
    assert result.final_decision is DecisionType.APPROVE_WITH_CONDITION
    assert result.approved_limit == 12_600_000.0  # 0.7 × 18M < requested 15M
    assert result.approved_tenor_months == 18
    assert result.pricing_rate == 0.025
    assert "REQUESTED_AMOUNT_ABOVE_ELIGIBLE_LIMIT" in result.reason_codes
    assert result.risk_grade == "B"


def test_deterministic_execution() -> None:
    plan = _plan(
        [
            StepPlan(
                order=1,
                step_type=StepType.CALCULATION,
                name="Calc",
                config={"calculations": ["loan.ltv", "affordability.dti"]},
            ),
        ]
    )
    first = run_strategy(plan, BASE_PAYLOAD)
    second = run_strategy(plan, BASE_PAYLOAD)
    assert first.final_decision == second.final_decision
    assert first.feature_values == second.feature_values
    assert first.reason_codes == second.reason_codes

"""Worked generic-rule patterns required by the Phase 3 rule-v2 specification."""

from typing import Any

from app.engine.decision_table import parse_decision_table_config
from app.engine.dsl import normalize_rule_definition
from app.engine.executor import ExecutablePlan, ResolvedRule, StepPlan, run_strategy
from app.shared.domain.enums import DecisionType, StepType


def _rule(code: str, body: dict[str, Any], kind: str = "STATEMENT") -> ResolvedRule:
    return ResolvedRule(
        rule_code=code,
        version=1,
        rule_kind=kind,
        definition=normalize_rule_definition(body, None),
    )


def _plan(steps: list[StepPlan]) -> ExecutablePlan:
    return ExecutablePlan(
        strategy_code="RULE_V2_PATTERNS",
        strategy_version=1,
        strategy_version_id="00000000-0000-0000-0000-000000000000",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        steps=steps,
    )


def _output_rule(
    code: str, field: str, operator: str, expected: Any, target: str, value: Any
) -> ResolvedRule:
    return _rule(
        code,
        {
            "branches": [
                {
                    "when": {"all": [{"field": field, "operator": operator, "value": expected}]},
                    "then": [{"type": "SET_OUTPUT", "target": target, "value": value}],
                }
            ],
        },
        "CLASSIFICATION",
    )


def test_statement_output_is_consumed_by_later_decision_table() -> None:
    statement = _rule(
        "VEHICLE_PRICE_BAND",
        {
            "branches": [
                {
                    "when": {
                        "all": [
                            {
                                "field": "applicant.monthly_income",
                                "operator": ">",
                                "value": 8_000_000,
                            }
                        ]
                    },
                    "then": [
                        {
                            "type": "SET_OUTPUT",
                            "target": "outputs.vehicle_price_band",
                            "value": 20_000,
                        }
                    ],
                }
            ],
            "default": [
                {
                    "type": "SET_OUTPUT",
                    "target": "outputs.vehicle_price_band",
                    "value": 0,
                }
            ],
        },
    )
    result = run_strategy(
        _plan(
            [
                StepPlan(order=1, step_type=StepType.RULE_SET, name="Band", rules=[statement]),
                StepPlan(
                    order=2,
                    step_type=StepType.DECISION_TABLE,
                    name="Final",
                    decision_table=parse_decision_table_config(
                        {
                            "rows": [
                                {
                                    "conditions": [
                                        {
                                            "field": "outputs.vehicle_price_band",
                                            "operator": ">=",
                                            "value": 15_000,
                                        }
                                    ],
                                    "output": {"decision": "APPROVE"},
                                }
                            ]
                        }
                    ),
                ),
            ]
        ),
        {"applicant": {"monthly_income": 8_500_000}},
    )

    assert result.final_decision is DecisionType.APPROVE
    assert result.feature_values["outputs.vehicle_price_band"] == 20_000


def test_classification_pair_combines_in_decision_table() -> None:
    collateral = _output_rule(
        "COLLATERAL_RISK",
        "vehicle.year",
        "<",
        2018,
        "outputs.collateral_risk",
        "HIGH",
    )
    affordability = _output_rule(
        "AFFORDABILITY_RISK",
        "applicant.monthly_income",
        "<",
        6_000_000,
        "outputs.affordability_risk",
        "HIGH",
    )
    result = run_strategy(
        _plan(
            [
                StepPlan(
                    order=1,
                    step_type=StepType.RULE_SET,
                    name="Classify",
                    rules=[collateral, affordability],
                ),
                StepPlan(
                    order=2,
                    step_type=StepType.DECISION_TABLE,
                    name="Combine",
                    decision_table=parse_decision_table_config(
                        {
                            "rows": [
                                {
                                    "conditions": [
                                        {
                                            "field": "outputs.collateral_risk",
                                            "operator": "=",
                                            "value": "HIGH",
                                        },
                                        {
                                            "field": "outputs.affordability_risk",
                                            "operator": "=",
                                            "value": "HIGH",
                                        },
                                    ],
                                    "output": {
                                        "decision": "MANUAL_REVIEW",
                                        "reason_code": "HIGH_DTI",
                                    },
                                }
                            ]
                        }
                    ),
                ),
            ]
        ),
        {"applicant": {"monthly_income": 5_500_000}, "vehicle": {"year": 2015}},
    )

    assert result.final_decision is DecisionType.MANUAL_REVIEW
    assert result.feature_values["outputs.collateral_risk"] == "HIGH"
    assert result.feature_values["outputs.affordability_risk"] == "HIGH"


def test_mixed_branch_sets_output_and_reason_code() -> None:
    mixed = _rule(
        "MIXED_AFFORDABILITY",
        {
            "branches": [
                {
                    "when": {
                        "all": [
                            {
                                "field": "applicant.monthly_income",
                                "operator": "<",
                                "value": 7_000_000,
                            }
                        ]
                    },
                    "then": [
                        {
                            "type": "SET_OUTPUT",
                            "target": "outputs.affordability_risk",
                            "value": "HIGH",
                        },
                        {"type": "ADD_REASON_CODE", "reason_code": "DTI_NEAR_THRESHOLD"},
                    ],
                }
            ],
            "default": [
                {
                    "type": "SET_OUTPUT",
                    "target": "outputs.affordability_risk",
                    "value": "LOW",
                }
            ],
        },
    )

    result = run_strategy(
        _plan([StepPlan(order=1, step_type=StepType.RULE_SET, name="Mixed", rules=[mixed])]),
        {"applicant": {"monthly_income": 6_500_000}},
    )

    assert result.feature_values["outputs.affordability_risk"] == "HIGH"
    assert "DTI_NEAR_THRESHOLD" in result.reason_codes
    actions = result.step_results[0]["rule_results"][0]["actions_applied"]
    assert [action["type"] for action in actions] == ["SET_OUTPUT", "ADD_REASON_CODE"]

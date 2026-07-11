from typing import Any

from app.engine.dsl import normalize_rule_definition
from app.engine.executor import ExecutablePlan, ResolvedRule, StepPlan, run_strategy
from app.shared.domain.enums import DecisionType, StepType


def _plan(definition: dict[str, Any]) -> ExecutablePlan:
    return ExecutablePlan(
        strategy_code="BRANCH_TEST",
        strategy_version=1,
        strategy_version_id="00000000-0000-0000-0000-000000000000",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        steps=[
            StepPlan(
                order=1,
                step_type=StepType.RULE_SET,
                name="Branch rule",
                rules=[
                    ResolvedRule(
                        rule_code="RISK_BAND",
                        version=1,
                        definition=normalize_rule_definition(definition, None),
                    )
                ],
            )
        ],
    )


def _definition() -> dict[str, Any]:
    return {
        "branches": [
            {
                "when": {"all": [{"field": "applicant.age", "operator": ">", "value": 60}]},
                "then": [
                    {
                        "type": "SET_OUTPUT",
                        "target": "outputs.age_risk",
                        "value": "HIGH",
                    },
                    {"type": "ADD_REASON_CODE", "reason_code": "SENIOR_APPLICANT"},
                ],
            },
            {
                "when": {"all": [{"field": "applicant.age", "operator": ">", "value": 30}]},
                "then": [
                    {
                        "type": "SET_OUTPUT",
                        "target": "outputs.age_risk",
                        "value": "MEDIUM",
                    }
                ],
            },
        ],
        "default": [{"type": "SET_OUTPUT", "target": "outputs.age_risk", "value": "LOW"}],
    }


def test_first_match_wins_and_actions_apply_in_order() -> None:
    result = run_strategy(_plan(_definition()), {"applicant": {"age": 65}})

    rule = result.step_results[0]["rule_results"][0]
    assert rule["matched_branch"] == 0
    assert [action["type"] for action in rule["actions_applied"]] == [
        "SET_OUTPUT",
        "ADD_REASON_CODE",
    ]
    assert result.feature_values["outputs.age_risk"] == "HIGH"
    assert result.reason_codes == ["SENIOR_APPLICANT", "NO_DECISION_PRODUCED"]


def test_second_branch_can_match() -> None:
    result = run_strategy(_plan(_definition()), {"applicant": {"age": 40}})

    rule = result.step_results[0]["rule_results"][0]
    assert rule["matched_branch"] == 1
    assert result.feature_values["outputs.age_risk"] == "MEDIUM"


def test_default_applies_when_no_branch_matches() -> None:
    result = run_strategy(_plan(_definition()), {"applicant": {"age": 20}})

    rule = result.step_results[0]["rule_results"][0]
    assert rule["matched_branch"] == "default"
    assert result.feature_values["outputs.age_risk"] == "LOW"


def test_no_match_without_default_is_a_non_event() -> None:
    definition = _definition()
    definition.pop("default")
    result = run_strategy(_plan(definition), {"applicant": {"age": 20}})

    rule = result.step_results[0]["rule_results"][0]
    assert rule["matched"] is False
    assert rule["status"] == "PASSED"
    assert "matched_branch" not in rule


def test_stop_execution_in_action_list_keeps_prior_output_and_skips_next_step() -> None:
    definition = {
        "branches": [
            {
                "when": {
                    "all": [
                        {
                            "field": "fraud.blacklist_hit",
                            "operator": "=",
                            "value": True,
                        }
                    ]
                },
                "then": [
                    {
                        "type": "SET_OUTPUT",
                        "target": "outputs.fraud_flag",
                        "value": True,
                    },
                    {
                        "type": "STOP_EXECUTION",
                        "decision": "REJECT",
                        "reason_code": "FRAUD_HIT",
                    },
                ],
            }
        ]
    }
    plan = _plan(definition)
    plan.steps.append(
        StepPlan(
            order=2,
            step_type=StepType.CALCULATION,
            name="Skipped",
            config={"calculations": ["loan.ltv"]},
        )
    )

    result = run_strategy(plan, {"fraud": {"blacklist_hit": True}})

    assert result.final_decision is DecisionType.REJECT
    assert result.feature_values["outputs.fraud_flag"] is True
    assert result.step_results[1]["status"] == "SKIPPED"

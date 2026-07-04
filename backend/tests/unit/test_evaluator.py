import pytest
from pydantic import ValidationError

from app.engine.dsl import Condition, Operator, parse_rule_definition
from app.engine.evaluator import evaluate_condition, evaluate_node


def _cond(field: str, operator: str, value: object = None) -> Condition:
    return Condition(field=field, operator=Operator(operator), value=value)


def test_comparison_operators() -> None:
    features = {"affordability.dti": 0.51}
    assert evaluate_condition(_cond("affordability.dti", ">", 0.45), features)[0]
    assert not evaluate_condition(_cond("affordability.dti", "<", 0.45), features)[0]
    assert evaluate_condition(_cond("affordability.dti", ">=", 0.51), features)[0]
    assert evaluate_condition(_cond("affordability.dti", "<=", 0.51), features)[0]


def test_equality_and_membership() -> None:
    features = {"vehicle.type": "MOTOR", "bureau.collectability": "CURRENT"}
    assert evaluate_condition(_cond("vehicle.type", "=", "MOTOR"), features)[0]
    assert evaluate_condition(_cond("bureau.collectability", "!=", "DOUBTFUL"), features)[0]
    assert evaluate_condition(_cond("vehicle.type", "in", ["MOTOR", "CAR"]), features)[0]
    assert evaluate_condition(_cond("vehicle.type", "not_in", ["CAR"]), features)[0]


def test_presence_operators() -> None:
    features = {"bureau.max_dpd_12m": 0, "applicant.income_verified": None}
    assert evaluate_condition(_cond("bureau.max_dpd_12m", "exists"), features)[0]
    assert evaluate_condition(_cond("applicant.income_verified", "is_null"), features)[0]
    assert evaluate_condition(_cond("missing.field", "is_null"), features)[0]
    assert not evaluate_condition(_cond("missing.field", "exists"), features)[0]


def test_missing_field_comparisons_are_false_with_detail() -> None:
    matched, detail = evaluate_condition(_cond("affordability.dti", ">", 0.45), {})
    assert matched is False
    assert detail["field_present"] is False
    assert detail["actual"] is None


def test_boolean_values_never_match_numeric_comparison() -> None:
    features = {"fraud.blacklist_hit": True}
    assert not evaluate_condition(_cond("fraud.blacklist_hit", ">", 0), features)[0]
    assert evaluate_condition(_cond("fraud.blacklist_hit", "=", True), features)[0]


def test_all_any_not_groups() -> None:
    definition = parse_rule_definition(
        {
            "all": [
                {"field": "vehicle.type", "operator": "=", "value": "MOTOR"},
                {
                    "any": [
                        {"field": "loan.ltv", "operator": ">", "value": 0.85},
                        {"field": "vehicle.age_years", "operator": ">", "value": 8},
                    ]
                },
                {"not": {"field": "fraud.blacklist_hit", "operator": "=", "value": True}},
            ]
        },
        {"decision": "MANUAL_REVIEW", "reason_code": "X"},
    )
    matched, details = evaluate_node(
        definition.condition,
        {
            "vehicle.type": "MOTOR",
            "loan.ltv": 0.9,
            "vehicle.age_years": 4,
            "fraud.blacklist_hit": False,
        },
    )
    assert matched is True
    assert len(details) == 4  # every leaf condition evaluated and recorded

    matched, _ = evaluate_node(
        definition.condition,
        {
            "vehicle.type": "MOTOR",
            "loan.ltv": 0.9,
            "vehicle.age_years": 4,
            "fraud.blacklist_hit": True,
        },
    )
    assert matched is False


def test_dsl_rejects_unknown_operator_and_malformed_values() -> None:
    with pytest.raises(ValidationError):
        parse_rule_definition(
            {"all": [{"field": "a", "operator": "like", "value": "x"}]},
            {"decision": "REJECT", "reason_code": "X"},
        )
    with pytest.raises(ValidationError):
        parse_rule_definition(
            {"all": [{"field": "a", "operator": "in", "value": "not-a-list"}]},
            {"decision": "REJECT", "reason_code": "X"},
        )
    with pytest.raises(ValidationError):
        parse_rule_definition(
            {"all": [{"field": "a", "operator": ">", "value": "not-a-number"}]},
            {"decision": "REJECT", "reason_code": "X"},
        )

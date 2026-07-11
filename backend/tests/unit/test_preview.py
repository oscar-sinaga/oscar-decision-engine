from app.engine.dsl import ExpressionRuleDefinition, normalize_rule_definition
from app.engine.expression import ast_to_json, validate_expression
from app.engine.preview import dsl_to_sql_preview


def test_output_branches_render_as_case() -> None:
    definition = normalize_rule_definition(
        {
            "branches": [
                {
                    "when": {"all": [{"field": "loan.ltv", "operator": ">", "value": 0.85}]},
                    "then": [{"type": "SET_OUTPUT", "target": "outputs.risk", "value": "HIGH"}],
                },
                {
                    "when": {"all": [{"field": "loan.ltv", "operator": ">", "value": 0.7}]},
                    "then": [{"type": "SET_OUTPUT", "target": "outputs.risk", "value": "MEDIUM"}],
                },
            ],
            "default": [{"type": "SET_OUTPUT", "target": "outputs.risk", "value": "LOW"}],
        },
        None,
    )
    assert dsl_to_sql_preview(definition) == (
        "CASE\n"
        "  WHEN (loan.ltv > 0.85) THEN 'HIGH'\n"
        "  WHEN (loan.ltv > 0.7) THEN 'MEDIUM'\n"
        "  ELSE 'LOW'\n"
        "END  -- writes outputs.risk"
    )


def test_nested_condition_and_non_output_action_render_as_comments() -> None:
    definition = normalize_rule_definition(
        {
            "branches": [
                {
                    "when": {
                        "all": [
                            {"field": "loan.ltv", "operator": ">=", "value": 0.9},
                            {"not": {"field": "fraud.hit", "operator": "=", "value": True}},
                        ]
                    },
                    "then": [
                        {"type": "SET_DECISION", "decision": "REJECT", "reason_code": "HIGH_LTV"}
                    ],
                }
            ]
        },
        None,
    )
    preview = dsl_to_sql_preview(definition)
    assert "loan.ltv >= 0.9" in preview
    assert "NOT fraud.hit = TRUE" in preview
    assert "-- SET_DECISION REJECT (HIGH_LTV)" in preview


def test_expression_rule_preview_uses_original_text() -> None:
    validated = validate_expression("monthly_income * 0.3", {"monthly_income": "NUMBER"})
    definition = ExpressionRuleDefinition(
        expression_ast=ast_to_json(validated.root),
        output_target="outputs.limit",
        expression_text="monthly_income * 0.3",
    )
    assert dsl_to_sql_preview(definition) == ("monthly_income * 0.3\n-- writes outputs.limit")


def test_set_output_expression_is_rendered_without_execution() -> None:
    definition = normalize_rule_definition(
        {
            "branches": [
                {
                    "when": {"all": [{"field": "flag.active", "operator": "=", "value": True}]},
                    "then": [
                        {
                            "type": "SET_OUTPUT",
                            "target": "outputs.limit",
                            "expression": "income * 0.3",
                            "expression_ast": {"kind": "literal", "value": 1},
                        }
                    ],
                }
            ]
        },
        None,
    )
    preview = dsl_to_sql_preview(definition)
    assert "THEN income * 0.3" in preview
    assert "writes outputs.limit" in preview


def test_membership_preview_is_stable() -> None:
    definition = normalize_rule_definition(
        {
            "branches": [
                {
                    "when": {
                        "any": [
                            {"field": "vehicle.type", "operator": "in", "value": ["MOTOR", "CAR"]},
                            {"field": "bureau.score", "operator": "is_null"},
                        ]
                    },
                    "then": [{"type": "CONTINUE"}],
                }
            ]
        },
        None,
    )
    preview = dsl_to_sql_preview(definition)
    assert "vehicle.type IN ('MOTOR', 'CAR')" in preview
    assert "bureau.score IS NULL" in preview

"""Safe OSCAR expression language unit and abuse tests."""

from pathlib import Path

import pytest

from app.engine.expression import (
    ExpressionEvaluationError,
    ExpressionParseError,
    ExpressionValidationError,
    ast_from_json,
    ast_to_json,
    evaluate_expression,
    parse_expression,
    validate_expression,
)

FEATURE_TYPES = {
    "monthly_income": "NUMBER",
    "existing_monthly_obligation": "NUMBER",
    "vehicle.age_years": "NUMBER",
    "loan.ltv": "NUMBER",
    "vehicle.type": "STRING",
    "bureau.max_dpd_12m": "NUMBER",
    "loan.requested_amount": "NUMBER",
    "outputs.eligible_limit": "NUMBER",
    "flag.active": "BOOLEAN",
    "name": "STRING",
}


@pytest.mark.parametrize(
    ("text", "expects", "features", "expected"),
    [
        (
            "monthly_income * 0.3 - existing_monthly_obligation",
            "value",
            {"monthly_income": 10_000, "existing_monthly_obligation": 1_000},
            2_000,
        ),
        (
            "CASE WHEN vehicle.age_years > 10 THEN 'OLD' "
            "WHEN vehicle.age_years > 5 THEN 'MID' ELSE 'NEW' END",
            "value",
            {"vehicle.age_years": 7},
            "MID",
        ),
        (
            "loan.ltv > 0.85 AND vehicle.type = 'MOTOR'",
            "boolean",
            {"loan.ltv": 0.9, "vehicle.type": "MOTOR"},
            True,
        ),
        (
            "COALESCE(bureau.max_dpd_12m, 999) <= 30",
            "boolean",
            {"bureau.max_dpd_12m": None},
            False,
        ),
        (
            "ROUND(MIN(loan.requested_amount, outputs.eligible_limit) / 12)",
            "value",
            {"loan.requested_amount": 120_000, "outputs.eligible_limit": 96_000},
            8_000,
        ),
    ],
)
def test_documented_examples_round_trip_and_evaluate(
    text: str, expects: str, features: dict[str, object], expected: object
) -> None:
    validated = validate_expression(text, FEATURE_TYPES, expects=expects)  # type: ignore[arg-type]
    restored = ast_from_json(ast_to_json(validated.root))

    assert evaluate_expression(restored, features) == expected
    assert parse_expression(validated.normalized_preview).root == validated.root
    assert validated.referenced_features


def test_keywords_are_case_insensitive_but_identifiers_are_case_sensitive() -> None:
    validated = validate_expression(
        "case when flag.active then min(monthly_income, 100) else 0 end",
        FEATURE_TYPES,
    )
    assert evaluate_expression(validated.root, {"flag.active": True, "monthly_income": 120}) == 100

    with pytest.raises(ExpressionValidationError, match="unknown feature: Monthly_Income"):
        validate_expression("Monthly_Income + 1", FEATURE_TYPES)


def test_null_semantics_are_sql_like_and_explicit() -> None:
    assert evaluate_expression(validate_expression("loan.ltv > 1", FEATURE_TYPES).root, {}) is None
    assert evaluate_expression(validate_expression("loan.ltv + 1", FEATURE_TYPES).root, {}) is None
    assert (
        evaluate_expression(validate_expression("loan.ltv IS NULL", FEATURE_TYPES).root, {}) is True
    )
    assert (
        evaluate_expression(
            validate_expression("flag.active AND TRUE", FEATURE_TYPES).root,
            {},
        )
        is None
    )
    assert (
        evaluate_expression(
            validate_expression("flag.active AND FALSE", FEATURE_TYPES).root,
            {},
        )
        is False
    )


@pytest.mark.parametrize(
    "text",
    [
        "name + 1",
        "1 AND TRUE",
        "NOT 1",
        "CASE WHEN 1 THEN 'x' ELSE 'y' END",
        "COALESCE(name, monthly_income)",
        "loan.ltv IN ('HIGH')",
        "ABS(name)",
        "loan.ltv = name",
    ],
)
def test_static_type_errors_fail_validation(text: str) -> None:
    with pytest.raises(ExpressionValidationError):
        validate_expression(text, FEATURE_TYPES)


def test_runtime_errors_are_safe_and_do_not_echo_payload_values() -> None:
    validated = validate_expression("monthly_income / existing_monthly_obligation", FEATURE_TYPES)
    with pytest.raises(ExpressionEvaluationError) as caught:
        evaluate_expression(
            validated.root,
            {"monthly_income": 123_456_789, "existing_monthly_obligation": 0},
        )
    assert "123456789" not in str(caught.value)
    assert "division by zero" in str(caught.value)


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os')",
        "loan.ltv.__class__",
        "loan[0]",
        "lambda: 1",
        "1; DROP TABLE rules",
        "1 -- comment",
        '"double quoted"',
        "'unterminated",
        "'back\\slash'",
        "loan..ltv",
        "loan.ltv OR 1=1",
        "loan.ltv /* comment */ 1",
        "α + 1",
        "@name",
        "MIN()",
        "ROUND(1, 2, 3)",
    ],
)
def test_fuzz_payloads_fail_parse_or_resolution(text: str) -> None:
    with pytest.raises((ExpressionParseError, ExpressionValidationError)):
        validate_expression(text, FEATURE_TYPES, expects="boolean")


def test_limits_are_enforced() -> None:
    with pytest.raises(ExpressionParseError, match="2000 characters"):
        parse_expression("1" * 2_001)

    with pytest.raises(ExpressionParseError, match="nesting depth"):
        parse_expression("(" * 21 + "1" + ")" * 21)

    with pytest.raises(ExpressionParseError, match="200 AST nodes"):
        parse_expression(" + ".join("1" for _ in range(101)))

    case_text = "CASE " + " ".join("WHEN TRUE THEN 1" for _ in range(21)) + " END"
    with pytest.raises(ExpressionParseError, match="20 branches"):
        parse_expression(case_text)

    in_text = "loan.ltv IN (" + ",".join(str(i) for i in range(51)) + ")"
    with pytest.raises(ExpressionParseError, match="50 items"):
        parse_expression(in_text)


def test_stored_ast_is_revalidated_before_execution() -> None:
    nested: dict[str, object] = {"kind": "literal", "value": 1}
    for _ in range(21):
        nested = {"kind": "unary", "operator": "-", "operand": nested}
    with pytest.raises(ExpressionValidationError, match="safety limits"):
        ast_from_json(nested)

    with pytest.raises(ExpressionValidationError):
        ast_from_json({"kind": "identifier", "path": ["not", "a", "path"]})


def test_interpreter_is_deterministic_and_has_no_forbidden_runtime_bridge() -> None:
    validated = validate_expression("ROUND(monthly_income / 3, 2)", FEATURE_TYPES)
    payload = {"monthly_income": 10}
    assert evaluate_expression(validated.root, payload) == evaluate_expression(
        validated.root, payload
    )

    source = Path(__file__).parents[2] / "app" / "engine" / "expression.py"
    text = source.read_text(encoding="utf-8")
    forbidden_calls = ("eval" + "(", "exec" + "(", "compile" + "(")
    assert all(call not in text for call in forbidden_calls)
    assert "import ast" not in text

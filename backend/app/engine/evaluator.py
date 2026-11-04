"""Safe condition-tree evaluation over a flat feature mapping.

Evaluation is deterministic and side-effect free. Missing features never
raise: a comparison against a missing value evaluates to ``False`` and the
detail is captured so traces can show exactly what was compared (docs/10 §8).
"""

from typing import Any

from app.engine.dsl import (
    AllGroup,
    AnyGroup,
    Condition,
    ConditionNode,
    NotGroup,
    Operator,
)
from app.engine.input_validation import finite_number, iso_date

_MISSING = object()


def values_equal(actual: Any, expected: Any) -> bool:
    """JSON equality does not equate booleans to the numbers zero and one."""
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and bool(actual == expected)
    if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
        return finite_number(actual) and finite_number(expected) and bool(actual == expected)
    return type(actual) is type(expected) and bool(actual == expected)


def _compare_numbers(actual: Any, operator: Operator, expected: Any) -> bool:
    if not (
        (finite_number(actual) and finite_number(expected))
        or (iso_date(actual) and iso_date(expected))
    ):
        return False
    # Keep integer comparisons exact. Canonical ISO date strings sort chronologically.
    if operator is Operator.GT:
        return bool(actual > expected)
    if operator is Operator.GTE:
        return bool(actual >= expected)
    if operator is Operator.LT:
        return bool(actual < expected)
    return bool(actual <= expected)


def evaluate_condition(
    condition: Condition, features: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    """Evaluate one leaf condition. Returns (result, evaluation detail)."""
    actual = features.get(condition.field, _MISSING)
    present = actual is not _MISSING
    operator = condition.operator

    if operator is Operator.EXISTS:
        result = present and features[condition.field] is not None
    elif operator is Operator.IS_NULL:
        result = not present or features[condition.field] is None
    elif not present:
        result = False
    elif operator is Operator.EQ:
        result = values_equal(actual, condition.value)
    elif operator is Operator.NEQ:
        result = not values_equal(actual, condition.value)
    elif operator is Operator.IN:
        result = any(values_equal(actual, item) for item in condition.value)
    elif operator is Operator.NOT_IN:
        result = not any(values_equal(actual, item) for item in condition.value)
    else:
        result = _compare_numbers(actual, operator, condition.value)

    detail = {
        "field": condition.field,
        "operator": operator.value,
        "expected": condition.value,
        "actual": None if not present else actual,
        "field_present": present,
        "result": result,
    }
    return result, detail


def evaluate_node(
    node: ConditionNode, features: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    """Evaluate a condition tree. Returns (matched, flat list of leaf details)."""
    if isinstance(node, Condition):
        result, detail = evaluate_condition(node, features)
        return result, [detail]
    if isinstance(node, AllGroup):
        details: list[dict[str, Any]] = []
        matched = True
        for child in node.all:
            child_result, child_details = evaluate_node(child, features)
            details.extend(child_details)
            matched = matched and child_result
        return matched, details
    if isinstance(node, AnyGroup):
        details = []
        matched = False
        for child in node.any:
            child_result, child_details = evaluate_node(child, features)
            details.extend(child_details)
            matched = matched or child_result
        return matched, details
    if isinstance(node, NotGroup):
        child_result, child_details = evaluate_node(node.not_, features)
        return not child_result, child_details
    raise TypeError(f"Unsupported condition node: {type(node)!r}")  # pragma: no cover

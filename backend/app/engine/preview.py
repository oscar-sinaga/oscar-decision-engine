"""Display-only SQL-style rendering for safe OSCAR rule definitions.

The renderer never produces executable database input. It converts already
validated DSL/AST objects into a familiar review format for humans.
"""

from __future__ import annotations

from typing import Any

from app.engine.dsl import (
    ActionType,
    AllGroup,
    AnyGroup,
    BranchedRuleDefinition,
    Condition,
    ConditionNode,
    ExpressionRuleDefinition,
    NotGroup,
    Operator,
    RuleAction,
)


def _literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, list):
        return "(" + ", ".join(_literal(item) for item in value) + ")"
    return str(value)


def condition_to_sql_preview(node: ConditionNode) -> str:
    if isinstance(node, Condition):
        if node.operator is Operator.EXISTS:
            return f"{node.field} IS NOT NULL"
        if node.operator is Operator.IS_NULL:
            return f"{node.field} IS NULL"
        if node.operator is Operator.IN:
            return f"{node.field} IN {_literal(node.value)}"
        if node.operator is Operator.NOT_IN:
            return f"{node.field} NOT IN {_literal(node.value)}"
        return f"{node.field} {node.operator.value} {_literal(node.value)}"
    if isinstance(node, AllGroup):
        return "(" + " AND ".join(condition_to_sql_preview(item) for item in node.all) + ")"
    if isinstance(node, AnyGroup):
        return "(" + " OR ".join(condition_to_sql_preview(item) for item in node.any) + ")"
    if isinstance(node, NotGroup):
        return f"(NOT {condition_to_sql_preview(node.not_)})"
    raise TypeError("unsupported condition node")  # pragma: no cover


def _action_value(action: RuleAction) -> str:
    if action.expression is not None:
        return action.expression
    return _literal(action.value)


def _action_comment(action: RuleAction) -> str:
    pieces = [action.type.value]
    if action.decision is not None:
        pieces.append(action.decision.value)
    if action.target:
        pieces.append(action.target)
    if action.reason_code:
        pieces.append(f"({action.reason_code})")
    return " ".join(pieces)


def _single_output(actions: list[RuleAction]) -> RuleAction | None:
    outputs = [item for item in actions if item.type is ActionType.SET_OUTPUT and item.target]
    non_output = [item for item in actions if item.type is not ActionType.SET_OUTPUT]
    if len(outputs) == 1 and not non_output:
        return outputs[0]
    return None


def dsl_to_sql_preview(
    definition: BranchedRuleDefinition | ExpressionRuleDefinition,
) -> str:
    """Render a deterministic, display-only SQL-style preview."""

    if isinstance(definition, ExpressionRuleDefinition):
        return f"{definition.expression_text}\n-- writes {definition.output_target}"

    output_actions = [_single_output(branch.then) for branch in definition.branches]
    default_output = _single_output(definition.default or []) if definition.default else None
    targets = {item.target for item in output_actions if item is not None}
    if default_output is not None:
        targets.add(default_output.target)
    if all(item is not None for item in output_actions) and len(targets) == 1:
        target = next(iter(targets))
        lines = ["CASE"]
        for branch, output in zip(definition.branches, output_actions, strict=True):
            assert output is not None
            lines.append(
                f"  WHEN {condition_to_sql_preview(branch.when)} THEN {_action_value(output)}"
            )
        if default_output is not None:
            lines.append(f"  ELSE {_action_value(default_output)}")
        lines.append(f"END  -- writes {target}")
        return "\n".join(lines)

    preview_lines: list[str] = []
    for index, branch in enumerate(definition.branches):
        prefix = "WHEN" if index == 0 else "ELSE WHEN"
        preview_lines.append(f"{prefix} {condition_to_sql_preview(branch.when)}")
        for action in branch.then:
            preview_lines.append(f"  -- {_action_comment(action)}")
    if definition.default:
        preview_lines.append("ELSE")
        for action in definition.default:
            preview_lines.append(f"  -- {_action_comment(action)}")
    return "\n".join(preview_lines)

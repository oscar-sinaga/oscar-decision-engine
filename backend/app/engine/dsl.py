"""Rule DSL schema and validation (docs/10).

A rule is a safe JSON condition tree plus an action. No SQL, no eval — the
only executable form is this validated structure interpreted by the
evaluator against a flat feature mapping.
"""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.engine.input_validation import finite_number, iso_date
from app.shared.domain.enums import DecisionType


class Operator(StrEnum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    IS_NULL = "is_null"


COMPARISON_OPERATORS = frozenset({Operator.GT, Operator.GTE, Operator.LT, Operator.LTE})
MEMBERSHIP_OPERATORS = frozenset({Operator.IN, Operator.NOT_IN})
PRESENCE_OPERATORS = frozenset({Operator.EXISTS, Operator.IS_NULL})


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=200)
    operator: Operator
    value: Any = Field(default=None, validate_default=True)

    @field_validator("value")
    @classmethod
    def _value_shape(cls, value: Any, info: Any) -> Any:
        operator = info.data.get("operator")
        if operator in MEMBERSHIP_OPERATORS:
            if not isinstance(value, list) or len(value) > 1000:
                raise ValueError(f"operator '{operator}' requires a list of at most 1000 values")
            items = value
        else:
            items = [value]
        for item in items:
            if item is not None and not isinstance(item, (str, bool, int, float)):
                raise ValueError("condition values must be JSON scalars")
            if (
                isinstance(item, (int, float))
                and not isinstance(item, bool)
                and not finite_number(item)
            ):
                raise ValueError("condition numbers must be finite")
        if operator in COMPARISON_OPERATORS and not (finite_number(value) or iso_date(value)):
            raise ValueError("ordered comparisons require a finite number or an ISO date")
        return value


class AllGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    all: list["ConditionNode"] = Field(min_length=1)


class AnyGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    any: list["ConditionNode"] = Field(min_length=1)


class NotGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    not_: "ConditionNode" = Field(alias="not")


ConditionNode = AllGroup | AnyGroup | NotGroup | Condition

AllGroup.model_rebuild()
AnyGroup.model_rebuild()
NotGroup.model_rebuild()


class ActionType(StrEnum):
    SET_DECISION = "SET_DECISION"
    ADD_REASON_CODE = "ADD_REASON_CODE"
    SET_OUTPUT = "SET_OUTPUT"
    SET_ATTRIBUTE = "SET_ATTRIBUTE"
    ROUTE_MANUAL_REVIEW = "ROUTE_MANUAL_REVIEW"
    STOP_EXECUTION = "STOP_EXECUTION"
    CONTINUE = "CONTINUE"


class RuleAction(BaseModel):
    """Action applied when a rule matches.

    The compact document form ``{"decision": ..., "reason_code": ...}`` is the
    canonical MVP shape; ``type`` extends it for routing/stop/attribute actions.
    """

    model_config = ConfigDict(extra="forbid")

    type: ActionType = ActionType.SET_DECISION
    decision: DecisionType | None = None
    reason_code: str | None = None
    target: str | None = None
    value: Any = None
    expression: str | None = Field(default=None, min_length=1, max_length=2_000)
    expression_ast: dict[str, object] | None = None
    attribute: str | None = None
    attribute_value: Any = None
    stop_execution: bool = False

    @model_validator(mode="before")
    @classmethod
    def _normalize_set_attribute_alias(cls, value: Any) -> Any:
        if not isinstance(value, dict) or value.get("type") != ActionType.SET_ATTRIBUTE:
            return value
        normalized = dict(value)
        normalized["type"] = ActionType.SET_OUTPUT
        normalized["target"] = normalized.pop("attribute", None)
        normalized["value"] = normalized.pop("attribute_value", None)
        return normalized

    @field_validator("decision", mode="before")
    @classmethod
    def _normalize_decision(cls, value: Any) -> Any:
        return DecisionType(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_output_value_source(self) -> "RuleAction":
        if self.type is not ActionType.SET_OUTPUT:
            if self.expression is not None or self.expression_ast is not None:
                raise ValueError("expression is supported only for SET_OUTPUT")
            return self
        has_literal = "value" in self.model_fields_set
        has_expression = self.expression is not None
        if has_literal == has_expression:
            raise ValueError("SET_OUTPUT requires exactly one of value or expression")
        if self.expression_ast is not None and not has_expression:
            raise ValueError("expression_ast requires expression")
        return self


class RuleDefinition(BaseModel):
    """Validated executable form of one rule version."""

    model_config = ConfigDict(extra="forbid")

    condition: Annotated[ConditionNode, Field()]
    action: RuleAction


class RuleBranch(BaseModel):
    """One ordered CASE WHEN branch in a v2 rule definition."""

    model_config = ConfigDict(extra="forbid")

    when: Annotated[ConditionNode, Field()]
    then: list[RuleAction] = Field(min_length=1, max_length=10)


class BranchedRuleDefinition(BaseModel):
    """Normalized executable form shared by legacy and v2 rule documents."""

    model_config = ConfigDict(extra="forbid")

    branches: list[RuleBranch] = Field(min_length=1, max_length=20)
    default: list[RuleAction] | None = Field(default=None, min_length=1, max_length=10)


class ExpressionRuleDefinition(BaseModel):
    """Compiled safe expression writing one declared output feature."""

    model_config = ConfigDict(extra="forbid")

    expression_ast: dict[str, object]
    output_target: str = Field(min_length=1, max_length=200)
    expression_text: str = Field(min_length=1, max_length=2_000)


def parse_rule_definition(
    condition_json: dict[str, Any], action_json: dict[str, Any]
) -> RuleDefinition:
    return RuleDefinition.model_validate({"condition": condition_json, "action": action_json})


def normalize_rule_definition(
    condition_json: dict[str, Any], action_json: dict[str, Any] | None
) -> BranchedRuleDefinition:
    """Parse a v2 body or normalize the permanent legacy condition/action form."""
    if "branches" in condition_json:
        if action_json is not None:
            raise ValueError("branched rule definitions cannot include a legacy action")
        return BranchedRuleDefinition.model_validate(condition_json)
    if action_json is None:
        raise ValueError("legacy rule definitions require an action")
    return BranchedRuleDefinition.model_validate(
        {"branches": [{"when": condition_json, "then": [action_json]}]}
    )


def collect_condition_fields(node: ConditionNode) -> set[str]:
    """All feature field names referenced by a condition tree."""
    if isinstance(node, Condition):
        return {node.field}
    if isinstance(node, AllGroup):
        children: list[ConditionNode] = node.all
    elif isinstance(node, AnyGroup):
        children = node.any
    else:
        children = [node.not_]
    fields: set[str] = set()
    for child in children:
        fields |= collect_condition_fields(child)
    return fields

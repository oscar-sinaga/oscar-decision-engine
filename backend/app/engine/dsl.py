"""Rule DSL schema and validation (docs/10).

A rule is a safe JSON condition tree plus an action. No SQL, no eval — the
only executable form is this validated structure interpreted by the
evaluator against a flat feature mapping.
"""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    value: Any = None

    @field_validator("value")
    @classmethod
    def _value_shape(cls, value: Any, info: Any) -> Any:
        operator = info.data.get("operator")
        if operator in MEMBERSHIP_OPERATORS and not isinstance(value, list):
            raise ValueError(f"operator '{operator}' requires a list value")
        if operator in COMPARISON_OPERATORS and not isinstance(value, (int, float)):
            raise ValueError(f"operator '{operator}' requires a numeric value")
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
    attribute: str | None = None
    attribute_value: Any = None
    stop_execution: bool = False

    @field_validator("decision", mode="before")
    @classmethod
    def _normalize_decision(cls, value: Any) -> Any:
        return DecisionType(value) if isinstance(value, str) else value


class RuleDefinition(BaseModel):
    """Validated executable form of one rule version."""

    model_config = ConfigDict(extra="forbid")

    condition: Annotated[ConditionNode, Field()]
    action: RuleAction


def parse_rule_definition(
    condition_json: dict[str, Any], action_json: dict[str, Any]
) -> RuleDefinition:
    return RuleDefinition.model_validate({"condition": condition_json, "action": action_json})


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

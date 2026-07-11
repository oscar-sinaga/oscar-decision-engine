from typing import Any

import pytest
from pydantic import ValidationError

from app.engine.dsl import ActionType, normalize_rule_definition

CONDITION: dict[str, Any] = {"all": [{"field": "loan.ltv", "operator": ">", "value": 0.85}]}


def test_normalizes_legacy_rule_to_one_branch() -> None:
    definition = normalize_rule_definition(
        CONDITION, {"decision": "REJECT", "reason_code": "HIGH_LTV"}
    )

    assert len(definition.branches) == 1
    assert definition.branches[0].when.model_dump(by_alias=True) == CONDITION
    assert definition.branches[0].then[0].decision == "REJECT"
    assert definition.default is None


def test_parses_branched_rule_and_set_attribute_alias() -> None:
    definition = normalize_rule_definition(
        {
            "branches": [
                {
                    "when": CONDITION,
                    "then": [
                        {
                            "type": "SET_ATTRIBUTE",
                            "attribute": "outputs.risk",
                            "attribute_value": "HIGH",
                        }
                    ],
                }
            ],
            "default": [{"type": "SET_OUTPUT", "target": "outputs.risk", "value": "LOW"}],
        },
        None,
    )

    aliased = definition.branches[0].then[0]
    assert aliased.type is ActionType.SET_OUTPUT
    assert aliased.target == "outputs.risk"
    assert aliased.value == "HIGH"


@pytest.mark.parametrize(
    ("branches", "default"),
    [
        ([], None),
        (
            [{"when": CONDITION, "then": [{"type": "CONTINUE"}]} for _ in range(21)],
            None,
        ),
        (
            [
                {
                    "when": CONDITION,
                    "then": [{"type": "CONTINUE"} for _ in range(11)],
                }
            ],
            None,
        ),
        (
            [{"when": CONDITION, "then": [{"type": "CONTINUE"}]}],
            [{"type": "CONTINUE"} for _ in range(11)],
        ),
    ],
)
def test_rejects_branch_and_action_limit_violations(
    branches: list[dict[str, Any]], default: list[dict[str, Any]] | None
) -> None:
    with pytest.raises(ValidationError):
        normalize_rule_definition({"branches": branches, "default": default}, None)


def test_rejects_empty_then_list() -> None:
    with pytest.raises(ValidationError):
        normalize_rule_definition({"branches": [{"when": CONDITION, "then": []}]}, None)

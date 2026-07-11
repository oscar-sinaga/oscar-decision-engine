"""Pure graph traversal tests for the Phase 3 executor."""

from typing import Any

from pydantic import TypeAdapter

from app.engine.dsl import ConditionNode, parse_rule_definition
from app.engine.executor import (
    MAX_GRAPH_VISITS,
    ExecutablePlan,
    NodePlan,
    ResolvedRule,
    StepPlan,
    run_strategy,
)
from app.shared.domain.enums import DecisionType, NodeType, StepOnError, StepType

_CONDITION_ADAPTER: TypeAdapter[ConditionNode] = TypeAdapter(ConditionNode)


def _condition(value: dict[str, Any]) -> ConditionNode:
    return _CONDITION_ADAPTER.validate_python(value)


def _rule(code: str, threshold: int = 21) -> ResolvedRule:
    return ResolvedRule(
        rule_code=code,
        version=1,
        definition=parse_rule_definition(
            {"all": [{"field": "applicant.age", "operator": "<", "value": threshold}]},
            {"decision": "REJECT", "reason_code": "UNDER_AGE"},
        ),
    )


def _base_plan(
    nodes: dict[str, NodePlan], edges: dict[str, dict[str | None, str]]
) -> ExecutablePlan:
    return ExecutablePlan(
        strategy_code="GRAPH_TEST",
        strategy_version=1,
        strategy_version_id="00000000-0000-0000-0000-000000000001",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        nodes=nodes,
        edges=edges,
        start_key="start",
    )


def _payload(age: int = 30) -> dict[str, Any]:
    return {
        "application_id": "GRAPH-APP",
        "product_type": "MOTOR_LEASEBACK",
        "applicant": {"age": age},
        "fraud": {"blacklist_hit": False},
    }


def test_linear_graph_equals_legacy_ordered_plan() -> None:
    step = StepPlan(
        order=1,
        step_type=StepType.RULE_SET,
        name="Age",
        rules=[_rule("AGE")],
    )
    legacy = ExecutablePlan(
        strategy_code="GRAPH_TEST",
        strategy_version=1,
        strategy_version_id="00000000-0000-0000-0000-000000000001",
        product_type="MOTOR_LEASEBACK",
        segment="DEFAULT",
        steps=[step],
    )
    graph = _base_plan(
        {
            "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
            "age": NodePlan(
                node_key="age", node_type=NodeType.RULE_SET, name="Age", rules=[_rule("AGE")]
            ),
        },
        {"start": {None: "age"}},
    )

    legacy_result = run_strategy(legacy, _payload(age=18))
    graph_result = run_strategy(graph, _payload(age=18))

    assert graph_result.final_decision == legacy_result.final_decision
    assert graph_result.reason_codes == legacy_result.reason_codes
    assert graph_result.feature_values == legacy_result.feature_values
    assert graph_result.step_results[0]["node_key"] == "age"


def test_condition_routes_true_and_false() -> None:
    nodes = {
        "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
        "adult": NodePlan(
            node_key="adult",
            node_type=NodeType.CONDITION,
            name="Adult?",
            condition=_condition(
                {"all": [{"field": "applicant.age", "operator": ">=", "value": 21}]}
            ),
        ),
        "true_rule": NodePlan(
            node_key="true_rule",
            node_type=NodeType.RULE_SET,
            name="True branch",
            rules=[_rule("NEVER_TRUE", threshold=0)],
        ),
        "false_rule": NodePlan(
            node_key="false_rule",
            node_type=NodeType.RULE_SET,
            name="False branch",
            rules=[_rule("UNDER_AGE")],
        ),
    }
    edges: dict[str, dict[str | None, str]] = {
        "start": {None: "adult"},
        "adult": {"TRUE": "true_rule", "FALSE": "false_rule"},
    }
    plan = _base_plan(nodes, edges)

    adult = run_strategy(plan, _payload(age=30))
    minor = run_strategy(plan, _payload(age=18))

    assert adult.step_results[0]["condition_result"] is True
    assert adult.step_results[0]["taken_edge"] == "TRUE"
    assert adult.step_results[1]["node_key"] == "true_rule"
    assert adult.final_decision is DecisionType.MANUAL_REVIEW

    assert minor.step_results[0]["condition_result"] is False
    assert minor.step_results[0]["taken_edge"] == "FALSE"
    assert minor.step_results[1]["node_key"] == "false_rule"
    assert minor.final_decision is DecisionType.REJECT


def test_condition_branches_can_rejoin() -> None:
    nodes = {
        "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
        "condition": NodePlan(
            node_key="condition",
            node_type=NodeType.CONDITION,
            name="Adult?",
            condition=_condition(
                {"all": [{"field": "applicant.age", "operator": ">=", "value": 21}]}
            ),
        ),
        "left": NodePlan(node_key="left", node_type=NodeType.CALCULATION, name="Left"),
        "right": NodePlan(node_key="right", node_type=NodeType.CALCULATION, name="Right"),
        "join": NodePlan(
            node_key="join",
            node_type=NodeType.RULE_SET,
            name="Join",
            rules=[_rule("AGE")],
        ),
    }
    edges: dict[str, dict[str | None, str]] = {
        "start": {None: "condition"},
        "condition": {"TRUE": "left", "FALSE": "right"},
        "left": {None: "join"},
        "right": {None: "join"},
    }
    result = run_strategy(_base_plan(nodes, edges), _payload(age=18))
    assert [item["node_key"] for item in result.step_results] == ["condition", "right", "join"]


def test_terminal_node_without_end_is_legal() -> None:
    plan = _base_plan(
        {
            "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
            "terminal": NodePlan(
                node_key="terminal", node_type=NodeType.RULE_SET, name="Terminal", rules=[]
            ),
        },
        {"start": {None: "terminal"}},
    )
    result = run_strategy(plan, _payload())
    assert len(result.step_results) == 1
    assert result.step_results[0]["node_key"] == "terminal"


def test_on_error_paths_are_preserved_in_graph() -> None:
    for on_error, expected in (
        (StepOnError.FAIL, DecisionType.ERROR),
        (StepOnError.MANUAL_REVIEW, DecisionType.MANUAL_REVIEW),
        (StepOnError.CONTINUE, DecisionType.MANUAL_REVIEW),
    ):
        plan = _base_plan(
            {
                "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
                "broken": NodePlan(
                    node_key="broken",
                    node_type=NodeType.SCORECARD,
                    name="Broken",
                    on_error=on_error,
                ),
            },
            {"start": {None: "broken"}},
        )
        result = run_strategy(plan, _payload())
        assert result.final_decision is expected
        assert result.step_results[0]["fallback"] == on_error.value


def test_visit_guard_stops_hand_built_cycle() -> None:
    plan = _base_plan(
        {
            "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
            "loop": NodePlan(node_key="loop", node_type=NodeType.CALCULATION, name="Loop"),
        },
        {"start": {None: "loop"}, "loop": {None: "loop"}},
    )
    result = run_strategy(plan, _payload())
    assert len(result.step_results) == MAX_GRAPH_VISITS
    assert result.final_decision is DecisionType.ERROR
    assert result.errors[-1]["error_type"] == "GraphVisitLimitExceeded"


def test_graph_execution_is_deterministic_excluding_runtime_fields() -> None:
    plan = _base_plan(
        {
            "start": NodePlan(node_key="start", node_type=NodeType.START, name="Start"),
            "age": NodePlan(
                node_key="age", node_type=NodeType.RULE_SET, name="Age", rules=[_rule("AGE")]
            ),
        },
        {"start": {None: "age"}},
    )
    first = run_strategy(plan, _payload(age=18)).model_dump()
    second = run_strategy(plan, _payload(age=18)).model_dump()
    first.pop("latency_ms")
    first.pop("executed_at")
    second.pop("latency_ms")
    second.pop("executed_at")
    for record in first["step_results"]:
        record.pop("duration_ms")
    for record in second["step_results"]:
        record.pop("duration_ms")
    assert first == second

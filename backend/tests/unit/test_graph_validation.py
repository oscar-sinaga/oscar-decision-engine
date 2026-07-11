"""Structural strategy graph validation tests."""

from typing import Any

from app.modules.strategies.graph_validation import validate_graph_structure


def _node(key: str, node_type: str = "RULE_SET") -> dict[str, Any]:
    return {"node_key": key, "node_type": node_type}


def _edge(source: str, target: str, label: str | None = None) -> dict[str, Any]:
    return {"from": source, "to": target, "label": label}


def _issues(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[str]:
    return [item["issue"] for item in validate_graph_structure(nodes, edges)]


def test_requires_exactly_one_start() -> None:
    assert any("exactly one START" in issue for issue in _issues([_node("a")], []))
    assert any(
        "exactly one START" in issue
        for issue in _issues([_node("a", "START"), _node("b", "START")], [])
    )


def test_rejects_unknown_edge_endpoints() -> None:
    issues = _issues([_node("start", "START")], [_edge("start", "missing")])
    assert "unknown to node: missing" in issues


def test_rejects_self_loop() -> None:
    issues = _issues([_node("start", "START")], [_edge("start", "start")])
    assert any("self-loop" in issue for issue in issues)


def test_rejects_duplicate_edge() -> None:
    nodes = [_node("start", "START"), _node("end", "END")]
    issues = _issues(nodes, [_edge("start", "end"), _edge("start", "end")])
    assert any("duplicate edge" in issue for issue in issues)


def test_condition_requires_true_and_false_edges() -> None:
    nodes = [
        _node("start", "START"),
        _node("condition", "CONDITION"),
        _node("end", "END"),
    ]
    issues = _issues(nodes, [_edge("start", "condition"), _edge("condition", "end", "TRUE")])
    assert "CONDITION requires exactly TRUE and FALSE edges" in issues


def test_non_condition_out_degree_is_at_most_one() -> None:
    nodes = [
        _node("start", "START"),
        _node("work"),
        _node("a", "END"),
        _node("b", "END"),
    ]
    issues = _issues(
        nodes,
        [_edge("start", "work"), _edge("work", "a"), _edge("work", "b")],
    )
    assert "non-CONDITION node allows at most one outgoing edge" in issues


def test_rejects_cycle() -> None:
    nodes = [_node("start", "START"), _node("a"), _node("b")]
    issues = _issues(
        nodes,
        [_edge("start", "a"), _edge("a", "b"), _edge("b", "a")],
    )
    assert "cycle detected" in issues


def test_rejects_orphan() -> None:
    nodes = [_node("start", "START"), _node("end", "END"), _node("orphan")]
    issues = _issues(nodes, [_edge("start", "end")])
    assert "node is not reachable from START" in issues


def test_rejects_more_than_100_nodes() -> None:
    nodes = [_node("start", "START"), *[_node(f"n{i}") for i in range(100)]]
    issues = _issues(nodes, [_edge("start", "n0")])
    assert any("maximum is 100" in issue for issue in issues)


def test_valid_rejoining_graph_has_no_violations() -> None:
    nodes = [
        _node("start", "START"),
        _node("condition", "CONDITION"),
        _node("left"),
        _node("right"),
        _node("join"),
        _node("end", "END"),
    ]
    edges = [
        _edge("start", "condition"),
        _edge("condition", "left", "TRUE"),
        _edge("condition", "right", "FALSE"),
        _edge("left", "join"),
        _edge("right", "join"),
        _edge("join", "end"),
    ]
    assert validate_graph_structure(nodes, edges) == []

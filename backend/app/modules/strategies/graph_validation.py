"""Pure structural validation for versioned strategy graphs.

The validator intentionally has no database dependencies.  Service-layer
validation adds catalog and referenced-configuration checks after this module
has established that the graph shape is safe to traverse.
"""

from collections import Counter, defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any

from app.shared.domain.enums import NodeType

MAX_GRAPH_NODES = 100
MAX_GRAPH_EDGES = 200
EDGE_LABELS = {"TRUE", "FALSE"}


def validate_graph_structure(
    nodes: Sequence[Mapping[str, Any]], edges: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    """Return every structural graph violation in deterministic order."""

    details: list[dict[str, str]] = []
    if len(nodes) > MAX_GRAPH_NODES:
        details.append(
            {
                "field": "graph.nodes",
                "issue": f"graph has {len(nodes)} nodes; maximum is {MAX_GRAPH_NODES}",
            }
        )
    if len(edges) > MAX_GRAPH_EDGES:
        details.append(
            {
                "field": "graph.edges",
                "issue": f"graph has {len(edges)} edges; maximum is {MAX_GRAPH_EDGES}",
            }
        )

    keys = [str(node.get("node_key", "")) for node in nodes]
    key_counts = Counter(keys)
    for key, count in sorted(key_counts.items()):
        if not key:
            details.append({"field": "graph.nodes", "issue": "node_key must not be empty"})
        elif count > 1:
            details.append({"field": "graph.nodes", "issue": f"duplicate node_key: {key}"})

    node_by_key: dict[str, Mapping[str, Any]] = {
        key: node for key, node in zip(keys, nodes, strict=True) if key and key_counts[key] == 1
    }
    starts = [key for key, node in node_by_key.items() if _node_type(node) is NodeType.START]
    if len(starts) != 1:
        details.append(
            {
                "field": "graph.nodes",
                "issue": f"graph requires exactly one START node; found {len(starts)}",
            }
        )

    adjacency: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    incoming: dict[str, int] = defaultdict(int)
    seen_edges: set[tuple[str, str, str | None]] = set()
    valid_edges: list[tuple[str, str, str | None]] = []

    for index, edge in enumerate(edges):
        source = str(edge.get("from", edge.get("from_node_key", "")))
        target = str(edge.get("to", edge.get("to_node_key", "")))
        raw_label = edge.get("label")
        label = str(raw_label).upper() if raw_label is not None else None
        field = f"graph.edges[{index}]"

        if source not in node_by_key:
            details.append({"field": field, "issue": f"unknown from node: {source}"})
        if target not in node_by_key:
            details.append({"field": field, "issue": f"unknown to node: {target}"})
        if source and source == target:
            details.append({"field": field, "issue": f"self-loop is not allowed: {source}"})

        identity = (source, target, label)
        if identity in seen_edges:
            details.append(
                {
                    "field": field,
                    "issue": f"duplicate edge: {source} -> {target} ({label or 'default'})",
                }
            )
        else:
            seen_edges.add(identity)

        if source in node_by_key and target in node_by_key and source != target:
            valid_edges.append(identity)
            adjacency[source].append((target, label))
            incoming[target] += 1

    for key, node in sorted(node_by_key.items()):
        node_type = _node_type(node)
        outgoing = adjacency.get(key, [])
        labels = [label for _, label in outgoing]
        field = f"graph.nodes[{key}]"

        if node_type is NodeType.START:
            if len(outgoing) != 1:
                details.append(
                    {"field": field, "issue": "START requires exactly one outgoing edge"}
                )
            if any(label is not None for label in labels):
                details.append({"field": field, "issue": "START edge label must be null"})
        elif node_type is NodeType.CONDITION:
            if len(outgoing) != 2 or set(labels) != EDGE_LABELS:
                details.append(
                    {
                        "field": field,
                        "issue": "CONDITION requires exactly TRUE and FALSE edges",
                    }
                )
        elif node_type is NodeType.END:
            if outgoing:
                details.append({"field": field, "issue": "END must not have outgoing edges"})
        else:
            if len(outgoing) > 1:
                details.append(
                    {"field": field, "issue": "non-CONDITION node allows at most one outgoing edge"}
                )
            if any(label is not None for label in labels):
                details.append(
                    {"field": field, "issue": "edge label must be null for non-CONDITION node"}
                )

    if _has_cycle(node_by_key, valid_edges):
        details.append({"field": "graph.edges", "issue": "cycle detected"})

    if len(starts) == 1:
        reachable = _reachable(starts[0], adjacency)
        for key in sorted(set(node_by_key) - reachable):
            details.append(
                {"field": f"graph.nodes[{key}]", "issue": "node is not reachable from START"}
            )

    return details


def _node_type(node: Mapping[str, Any]) -> NodeType | None:
    raw = node.get("node_type", node.get("type"))
    try:
        return NodeType(str(raw))
    except ValueError:
        return None


def _has_cycle(
    node_by_key: Mapping[str, Mapping[str, Any]],
    edges: Sequence[tuple[str, str, str | None]],
) -> bool:
    indegree = dict.fromkeys(node_by_key, 0)
    outgoing: dict[str, list[str]] = defaultdict(list)
    for source, target, _ in edges:
        outgoing[source].append(target)
        indegree[target] += 1
    queue = deque(sorted(key for key, degree in indegree.items() if degree == 0))
    visited = 0
    while queue:
        key = queue.popleft()
        visited += 1
        for target in outgoing.get(key, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return visited != len(indegree)


def _reachable(start: str, adjacency: Mapping[str, Sequence[tuple[str, str | None]]]) -> set[str]:
    seen = {start}
    queue = deque([start])
    while queue:
        key = queue.popleft()
        for target, _ in adjacency.get(key, []):
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen

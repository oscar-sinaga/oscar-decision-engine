"""p3 strategy graph

Revision ID: f4b7c9d2e601
Revises: 8f3c2a1b7d04
Create Date: 2026-07-11
"""

import uuid
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f4b7c9d2e601"
down_revision: str | None = "8f3c2a1b7d04"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("strategy_version_id", sa.UUID(), nullable=False),
        sa.Column("node_key", sa.String(length=50), nullable=False),
        sa.Column("node_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), server_default="", nullable=False),
        sa.Column("reference_code", sa.String(length=100), nullable=True),
        sa.Column("on_error", sa.String(length=20), server_default="FAIL", nullable=False),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("position_x", sa.Integer(), server_default="0", nullable=False),
        sa.Column("position_y", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"],
            ["strategy_versions.id"],
            name=op.f("fk_strategy_nodes_strategy_version_id_strategy_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_nodes")),
        sa.UniqueConstraint(
            "strategy_version_id",
            "node_key",
            name=op.f("uq_strategy_nodes_strategy_version_id"),
        ),
    )
    op.create_index(
        op.f("ix_strategy_nodes_strategy_version_id"),
        "strategy_nodes",
        ["strategy_version_id"],
        unique=False,
    )
    op.create_table(
        "strategy_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("strategy_version_id", sa.UUID(), nullable=False),
        sa.Column("from_node_key", sa.String(length=50), nullable=False),
        sa.Column("to_node_key", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=10), nullable=True),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"],
            ["strategy_versions.id"],
            name=op.f("fk_strategy_edges_strategy_version_id_strategy_versions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_edges")),
        sa.UniqueConstraint(
            "strategy_version_id",
            "from_node_key",
            "to_node_key",
            "label",
            name=op.f("uq_strategy_edges_strategy_version_id"),
        ),
    )
    op.create_index(
        op.f("ix_strategy_edges_strategy_version_id"),
        "strategy_edges",
        ["strategy_version_id"],
        unique=False,
    )

    connection = op.get_bind()
    versions = sa.table("strategy_versions", sa.column("id", sa.UUID()))
    steps = sa.table(
        "strategy_steps",
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("step_order", sa.Integer()),
        sa.column("step_type", sa.String()),
        sa.column("name", sa.String()),
        sa.column("reference_code", sa.String()),
        sa.column("on_error", sa.String()),
        sa.column("config_json", postgresql.JSONB()),
    )
    nodes = sa.table(
        "strategy_nodes",
        sa.column("id", sa.UUID()),
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("node_key", sa.String()),
        sa.column("node_type", sa.String()),
        sa.column("name", sa.String()),
        sa.column("reference_code", sa.String()),
        sa.column("on_error", sa.String()),
        sa.column("config_json", postgresql.JSONB()),
        sa.column("position_x", sa.Integer()),
        sa.column("position_y", sa.Integer()),
    )
    edges = sa.table(
        "strategy_edges",
        sa.column("id", sa.UUID()),
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("from_node_key", sa.String()),
        sa.column("to_node_key", sa.String()),
        sa.column("label", sa.String()),
    )

    for version_id in connection.execute(sa.select(versions.c.id)).scalars():
        stored_steps = (
            connection.execute(
                sa.select(steps)
                .where(steps.c.strategy_version_id == version_id)
                .order_by(steps.c.step_order)
            )
            .mappings()
            .all()
        )
        connection.execute(
            nodes.insert().values(
                id=uuid.uuid4(),
                strategy_version_id=version_id,
                node_key="start",
                node_type="START",
                name="Start",
                reference_code=None,
                on_error="FAIL",
                config_json={},
                position_x=0,
                position_y=0,
            )
        )
        previous = "start"
        for index, step in enumerate(stored_steps, start=1):
            key = f"n{index}"
            node_type = "DECISION_TABLE" if step["step_type"] == "OUTPUT" else step["step_type"]
            connection.execute(
                nodes.insert().values(
                    id=uuid.uuid4(),
                    strategy_version_id=version_id,
                    node_key=key,
                    node_type=node_type,
                    name=step["name"],
                    reference_code=step["reference_code"],
                    on_error=step["on_error"],
                    config_json=step["config_json"] or {},
                    position_x=240 * index,
                    position_y=0,
                )
            )
            connection.execute(
                edges.insert().values(
                    id=uuid.uuid4(),
                    strategy_version_id=version_id,
                    from_node_key=previous,
                    to_node_key=key,
                    label=None,
                )
            )
            previous = key
        connection.execute(
            nodes.insert().values(
                id=uuid.uuid4(),
                strategy_version_id=version_id,
                node_key="end",
                node_type="END",
                name="End",
                reference_code=None,
                on_error="FAIL",
                config_json={},
                position_x=240 * (len(stored_steps) + 1),
                position_y=0,
            )
        )
        connection.execute(
            edges.insert().values(
                id=uuid.uuid4(),
                strategy_version_id=version_id,
                from_node_key=previous,
                to_node_key="end",
                label=None,
            )
        )

    op.drop_table("strategy_steps")


def downgrade() -> None:
    op.create_table(
        "strategy_steps",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("strategy_version_id", sa.UUID(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("reference_code", sa.String(length=100), nullable=True),
        sa.Column("on_error", sa.String(length=30), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"],
            ["strategy_versions.id"],
            name=op.f("fk_strategy_steps_strategy_version_id_strategy_versions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_steps")),
        sa.UniqueConstraint(
            "strategy_version_id",
            "step_order",
            name=op.f("uq_strategy_steps_strategy_version_id"),
        ),
    )

    connection = op.get_bind()
    versions = sa.table("strategy_versions", sa.column("id", sa.UUID()))
    nodes = sa.table(
        "strategy_nodes",
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("node_key", sa.String()),
        sa.column("node_type", sa.String()),
        sa.column("name", sa.String()),
        sa.column("reference_code", sa.String()),
        sa.column("on_error", sa.String()),
        sa.column("config_json", postgresql.JSONB()),
    )
    edges = sa.table(
        "strategy_edges",
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("from_node_key", sa.String()),
        sa.column("to_node_key", sa.String()),
        sa.column("label", sa.String()),
    )
    steps = sa.table(
        "strategy_steps",
        sa.column("id", sa.UUID()),
        sa.column("strategy_version_id", sa.UUID()),
        sa.column("step_order", sa.Integer()),
        sa.column("step_type", sa.String()),
        sa.column("name", sa.String()),
        sa.column("reference_code", sa.String()),
        sa.column("on_error", sa.String()),
        sa.column("config_json", postgresql.JSONB()),
    )

    reconstructed: list[tuple[Any, list[Mapping[str, Any]]]] = []
    for version_id in connection.execute(sa.select(versions.c.id)).scalars():
        stored_nodes = (
            connection.execute(sa.select(nodes).where(nodes.c.strategy_version_id == version_id))
            .mappings()
            .all()
        )
        stored_edges = (
            connection.execute(sa.select(edges).where(edges.c.strategy_version_id == version_id))
            .mappings()
            .all()
        )
        ordered = _linear_nodes(stored_nodes, stored_edges)
        reconstructed.append((version_id, ordered))

    for version_id, ordered in reconstructed:
        for index, node in enumerate(ordered, start=1):
            connection.execute(
                steps.insert().values(
                    id=uuid.uuid4(),
                    strategy_version_id=version_id,
                    step_order=index,
                    step_type=node["node_type"],
                    name=node["name"],
                    reference_code=node["reference_code"],
                    on_error=node["on_error"],
                    config_json=node["config_json"] or {},
                )
            )

    op.drop_index(op.f("ix_strategy_edges_strategy_version_id"), table_name="strategy_edges")
    op.drop_table("strategy_edges")
    op.drop_index(op.f("ix_strategy_nodes_strategy_version_id"), table_name="strategy_nodes")
    op.drop_table("strategy_nodes")


def _linear_nodes(
    stored_nodes: list[Mapping[str, Any]], stored_edges: list[Mapping[str, Any]]
) -> list[Mapping[str, Any]]:
    by_key = {str(node["node_key"]): node for node in stored_nodes}
    starts = [key for key, node in by_key.items() if node["node_type"] == "START"]
    if len(starts) != 1 or any(node["node_type"] == "CONDITION" for node in stored_nodes):
        raise RuntimeError(
            "Cannot downgrade Phase 3 graph migration: non-linear strategy graph exists"
        )
    outgoing: dict[str, list[str]] = defaultdict(list)
    for edge in stored_edges:
        if edge["label"] is not None:
            raise RuntimeError(
                "Cannot downgrade Phase 3 graph migration: labeled strategy edge exists"
            )
        outgoing[str(edge["from_node_key"])].append(str(edge["to_node_key"]))
    if any(len(targets) > 1 for targets in outgoing.values()):
        raise RuntimeError(
            "Cannot downgrade Phase 3 graph migration: branching strategy graph exists"
        )

    current = starts[0]
    visited = {current}
    ordered: list[Mapping[str, Any]] = []
    while current in outgoing:
        target = outgoing[current][0]
        if target in visited or target not in by_key:
            raise RuntimeError(
                "Cannot downgrade Phase 3 graph migration: cyclic or invalid strategy graph exists"
            )
        visited.add(target)
        node = by_key[target]
        if node["node_type"] == "END":
            current = target
            break
        if node["node_type"] == "START":
            raise RuntimeError(
                "Cannot downgrade Phase 3 graph migration: invalid START node in path"
            )
        ordered.append(node)
        current = target
    if visited != set(by_key):
        raise RuntimeError(
            "Cannot downgrade Phase 3 graph migration: orphaned/non-linear strategy nodes exist"
        )
    return ordered

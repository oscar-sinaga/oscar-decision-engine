"""Strategy management service: graph validation, versioning, activation, rollback.

Phase 3 stores strategy versions as deterministic DAGs while continuing to
accept the legacy ordered ``steps`` request shape.  Production decisions and
simulations still share ``plan_builder.build_plan``.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.engine.features import DERIVED_FEATURES
from app.modules.audit.service import record_audit_event
from app.modules.auth.models import User
from app.modules.features.service import active_feature_paths
from app.modules.governance.locking import lock_policy
from app.modules.governance.service import (
    ensure_independent_approver,
    open_approval_request,
    pending_approval_request,
    resolve_approval_request,
)
from app.modules.rules.models import RuleSet
from app.modules.scorecards.models import (
    DecisionTable,
    DecisionTableVersion,
    Scorecard,
    ScorecardVersion,
)
from app.modules.simulations.models import Simulation, SimulationResult
from app.modules.strategies.graph_validation import validate_graph_structure
from app.modules.strategies.models import (
    Strategy,
    StrategyEdge,
    StrategyNode,
    StrategyVersion,
)
from app.modules.strategies.plan_builder import build_plan, plan_fingerprint
from app.modules.strategies.schemas import (
    EdgeRequest,
    EdgeResponse,
    GraphRequest,
    GraphResponse,
    NodeRequest,
    NodeResponse,
    Position,
    StepRequest,
    StepResponse,
    StrategyCreateRequest,
    StrategyVersionCreateRequest,
)
from app.shared.config import get_settings
from app.shared.domain.enums import (
    ApprovalStatus,
    ConfigStatus,
    NodeType,
    SimulationStatus,
    StepType,
)
from app.shared.domain.errors import ConflictError, NotFoundError, ValidationFailedError
from app.shared.domain.version_lifecycle import (
    ensure_editable,
    reject_version,
    submit_for_approval,
)
from app.shared.logging import get_logger

logger = get_logger("oscar.strategies")


def _version_load_options() -> tuple[Any, Any]:
    return (
        selectinload(StrategyVersion.nodes),
        selectinload(StrategyVersion.edges),
    )


async def get_strategy(session: AsyncSession, strategy_id: uuid.UUID) -> Strategy:
    strategy = await session.scalar(
        select(Strategy)
        .where(Strategy.id == strategy_id)
        .options(
            selectinload(Strategy.versions).selectinload(StrategyVersion.nodes),
            selectinload(Strategy.versions).selectinload(StrategyVersion.edges),
        )
    )
    if strategy is None:
        raise NotFoundError(f"Strategy '{strategy_id}' not found")
    return strategy


def get_version(strategy: Strategy, version_id: uuid.UUID) -> StrategyVersion:
    for version in strategy.versions:
        if version.id == version_id:
            return version
    raise NotFoundError(f"Strategy version '{version_id}' not found for '{strategy.strategy_code}'")


def steps_to_linear_graph(steps: list[StepRequest]) -> GraphRequest:
    """Convert the legacy ordered API shape into a positioned linear graph."""

    ordered = sorted(steps, key=lambda item: item.order)
    nodes: list[NodeRequest] = [
        NodeRequest(
            node_key="start",
            node_type=NodeType.START,
            name="Start",
            position=Position(x=0, y=0),
        )
    ]
    edges: list[EdgeRequest] = []
    previous = "start"
    for index, step in enumerate(ordered, start=1):
        key = f"n{index}"
        node_type = (
            NodeType.DECISION_TABLE if step.type is StepType.OUTPUT else NodeType(step.type.value)
        )
        nodes.append(
            NodeRequest(
                node_key=key,
                node_type=node_type,
                name=step.name or f"{step.type.value.replace('_', ' ').title()} step",
                reference_code=step.reference_code,
                on_error=step.on_error,
                config=step.config,
                position=Position(x=240 * index, y=0),
            )
        )
        edges.append(EdgeRequest(from_node_key=previous, to_node_key=key))
        previous = key
    end_key = "end"
    nodes.append(
        NodeRequest(
            node_key=end_key,
            node_type=NodeType.END,
            name="End",
            position=Position(x=240 * (len(ordered) + 1), y=0),
        )
    )
    edges.append(EdgeRequest(from_node_key=previous, to_node_key=end_key))
    return GraphRequest(nodes=nodes, edges=edges)


def normalize_graph(graph: GraphRequest) -> GraphRequest:
    """Assign deterministic keys to nodes whose client omitted ``node_key``."""

    used = {node.node_key for node in graph.nodes if node.node_key}
    next_index = 1
    nodes: list[NodeRequest] = []
    for node in graph.nodes:
        key = node.node_key
        if key is None:
            while f"n{next_index}" in used:
                next_index += 1
            key = f"n{next_index}"
            used.add(key)
            next_index += 1
        nodes.append(node.model_copy(update={"node_key": key}))
    return GraphRequest(nodes=nodes, edges=graph.edges)


def request_graph(request: StrategyVersionCreateRequest) -> GraphRequest:
    if request.graph is not None:
        return normalize_graph(request.graph)
    assert request.steps is not None
    return steps_to_linear_graph(request.steps)


def _graph_dicts(graph: GraphRequest) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes = [node.model_dump(mode="json") for node in graph.nodes]
    edges = [edge.model_dump(mode="json", by_alias=True) for edge in graph.edges]
    return nodes, edges


async def validate_graph(session: AsyncSession, graph: GraphRequest) -> None:
    """Validate structure plus catalog/config references and condition DSL."""

    node_dicts, edge_dicts = _graph_dicts(graph)
    details = validate_graph_structure(node_dicts, edge_dicts)
    known_features = await active_feature_paths(session)

    for node in graph.nodes:
        key = node.node_key or "?"
        prefix = f"graph.nodes[{key}]"
        if node.node_type in (NodeType.START, NodeType.END):
            if node.reference_code:
                details.append({"field": f"{prefix}.reference_code", "issue": "not allowed"})
            if node.config:
                details.append({"field": f"{prefix}.config", "issue": "must be empty"})
        elif node.node_type is NodeType.VALIDATION:
            for field in node.config.get("required_fields", []):
                if field not in known_features:
                    details.append(
                        {"field": f"{prefix}.required_fields", "issue": f"unknown feature: {field}"}
                    )
        elif node.node_type is NodeType.CALCULATION:
            for code in node.config.get("calculations", []):
                if code not in DERIVED_FEATURES:
                    details.append(
                        {
                            "field": f"{prefix}.calculations",
                            "issue": f"unknown calculation: {code}",
                        }
                    )
        elif node.node_type is NodeType.RULE_SET:
            if not node.reference_code or not await session.scalar(
                select(RuleSet).where(RuleSet.code == node.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown rule set: {node.reference_code}",
                    }
                )
        elif NodeType(node.node_type) is NodeType.DECISION_TABLE:
            if not node.reference_code or not await session.scalar(
                select(DecisionTable).where(DecisionTable.code == node.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown decision table: {node.reference_code}",
                    }
                )
        elif NodeType(node.node_type) is NodeType.SCORECARD:
            if not node.reference_code or not await session.scalar(
                select(Scorecard).where(Scorecard.code == node.reference_code)
            ):
                details.append(
                    {
                        "field": f"{prefix}.reference_code",
                        "issue": f"unknown scorecard: {node.reference_code}",
                    }
                )
        elif NodeType(node.node_type) is NodeType.CONDITION:
            raw_condition = node.config.get("condition")
            if not isinstance(raw_condition, dict):
                details.append(
                    {"field": f"{prefix}.config.condition", "issue": "condition is required"}
                )
            else:
                # Reuse the governed rule validator for DSL shape, catalog
                # membership, typed operators, and literal types.
                from app.modules.rules.service import validate_rule_definition

                try:
                    await validate_rule_definition(
                        session,
                        {
                            "branches": [
                                {
                                    "when": raw_condition,
                                    "then": [{"type": "CONTINUE"}],
                                }
                            ]
                        },
                        None,
                    )
                except ValidationFailedError as exc:
                    for item in exc.details:
                        details.append(
                            {
                                "field": f"{prefix}.config.condition",
                                "issue": str(item.get("issue", "invalid condition")),
                            }
                        )

    if details:
        raise ValidationFailedError("Strategy graph is invalid", details=details)


async def _verify_references_activatable(session: AsyncSession, version: StrategyVersion) -> None:
    """Revalidate graph and require active table/scorecard versions."""

    await validate_graph(session, graph_request_from_version(version))
    details: list[dict[str, str]] = []
    for node in version.nodes:
        if NodeType(node.node_type) is NodeType.DECISION_TABLE:
            table = await session.scalar(
                select(DecisionTable).where(DecisionTable.code == node.reference_code)
            )
            active = table and await session.scalar(
                select(DecisionTableVersion).where(
                    DecisionTableVersion.decision_table_id == table.id,
                    DecisionTableVersion.status == ConfigStatus.ACTIVE,
                )
            )
            if not active:
                details.append(
                    {
                        "field": node.reference_code or "",
                        "issue": "decision table has no active version",
                    }
                )
        elif NodeType(node.node_type) is NodeType.SCORECARD:
            scorecard = await session.scalar(
                select(Scorecard).where(Scorecard.code == node.reference_code)
            )
            active = scorecard and await session.scalar(
                select(ScorecardVersion).where(
                    ScorecardVersion.scorecard_id == scorecard.id,
                    ScorecardVersion.status == ConfigStatus.ACTIVE,
                )
            )
            if not active:
                details.append(
                    {"field": node.reference_code or "", "issue": "scorecard has no active version"}
                )
    if details:
        raise ValidationFailedError(
            "Strategy references configuration without an active version", details=details
        )


async def create_strategy(
    session: AsyncSession, request: StrategyCreateRequest, actor: User
) -> Strategy:
    await lock_policy(session)
    duplicate = await session.scalar(
        select(Strategy).where(Strategy.strategy_code == request.strategy_code)
    )
    if duplicate is not None:
        raise ConflictError(f"Strategy code '{request.strategy_code}' already exists")
    strategy = Strategy(
        strategy_code=request.strategy_code,
        name=request.name,
        product_type=request.product_type,
        segment=request.segment,
        owner_team=request.owner_team,
    )
    session.add(strategy)
    await session.flush()
    record_audit_event(
        session,
        event_type="STRATEGY_CREATED",
        entity_type="STRATEGY",
        entity_id=strategy.strategy_code,
        action="CREATE_STRATEGY",
        actor=actor,
        after_value={
            "name": request.name,
            "product_type": request.product_type,
            "segment": request.segment,
        },
    )
    await session.commit()
    return await get_strategy(session, strategy.id)


def graph_request_from_version(version: StrategyVersion) -> GraphRequest:
    return GraphRequest(
        nodes=[
            NodeRequest(
                node_key=node.node_key,
                node_type=node.node_type,
                name=node.name,
                reference_code=node.reference_code,
                on_error=node.on_error,
                config=node.config_json or {},
                position=Position(x=node.position_x, y=node.position_y),
            )
            for node in version.nodes
        ],
        edges=[
            EdgeRequest(
                from_node_key=edge.from_node_key,
                to_node_key=edge.to_node_key,
                label=edge.label,
            )
            for edge in version.edges
        ],
    )


def graph_response(version: StrategyVersion) -> GraphResponse:
    return GraphResponse(
        nodes=[
            NodeResponse(
                node_key=node.node_key,
                node_type=node.node_type,
                name=node.name,
                reference_code=node.reference_code,
                on_error=node.on_error,
                config=node.config_json or {},
                position=Position(x=node.position_x, y=node.position_y),
            )
            for node in sorted(version.nodes, key=lambda item: item.node_key)
        ],
        edges=[
            EdgeResponse(
                from_node_key=edge.from_node_key,
                to_node_key=edge.to_node_key,
                label=edge.label,
            )
            for edge in sorted(
                version.edges,
                key=lambda item: (item.from_node_key, item.label or "", item.to_node_key),
            )
        ],
    )


def derive_linear_steps(version: StrategyVersion) -> list[StepResponse] | None:
    """Return transition ``steps`` only when the stored graph is one linear path."""

    nodes = {node.node_key: node for node in version.nodes}
    starts = [node.node_key for node in version.nodes if NodeType(node.node_type) is NodeType.START]
    if len(starts) != 1 or any(node.node_type is NodeType.CONDITION for node in version.nodes):
        return None
    outgoing: dict[str, list[StrategyEdge]] = {}
    for edge in version.edges:
        if edge.label is not None:
            return None
        outgoing.setdefault(edge.from_node_key, []).append(edge)
    if any(len(items) > 1 for items in outgoing.values()):
        return None

    result: list[StepResponse] = []
    visited = {starts[0]}
    current = starts[0]
    while current in outgoing:
        target = outgoing[current][0].to_node_key
        if target in visited or target not in nodes:
            return None
        visited.add(target)
        node = nodes[target]
        if NodeType(node.node_type) is NodeType.END:
            current = target
            break
        if NodeType(node.node_type) is NodeType.START:
            return None
        try:
            step_type = StepType(NodeType(node.node_type).value)
        except ValueError:
            return None
        result.append(
            StepResponse(
                order=len(result) + 1,
                type=step_type,
                name=node.name,
                reference_code=node.reference_code,
                on_error=node.on_error,
                config=node.config_json or {},
            )
        )
        current = target

    if visited != set(nodes):
        return None
    return result


def _graph_snapshot(version: StrategyVersion) -> dict[str, Any]:
    return graph_response(version).model_dump(mode="json", by_alias=True)


def _apply_graph(session: AsyncSession, version: StrategyVersion, graph: GraphRequest) -> None:
    for node in graph.nodes:
        assert node.node_key is not None
        session.add(
            StrategyNode(
                strategy_version_id=version.id,
                node_key=node.node_key,
                node_type=node.node_type,
                name=node.name,
                reference_code=node.reference_code,
                on_error=node.on_error,
                config_json=node.config,
                position_x=node.position.x,
                position_y=node.position.y,
            )
        )
    for edge in graph.edges:
        session.add(
            StrategyEdge(
                strategy_version_id=version.id,
                from_node_key=edge.from_node_key,
                to_node_key=edge.to_node_key,
                label=edge.label,
            )
        )


async def create_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    request: StrategyVersionCreateRequest,
    actor: User,
) -> StrategyVersion:
    await lock_policy(session, strategy)
    graph = request_graph(request)
    await validate_graph(session, graph)
    open_versions = [
        version
        for version in strategy.versions
        if version.status in (ConfigStatus.DRAFT, ConfigStatus.PENDING_APPROVAL)
    ]
    if open_versions:
        raise ConflictError(
            f"Strategy '{strategy.strategy_code}' already has an open draft/pending version"
        )
    next_version = max((version.version for version in strategy.versions), default=0) + 1
    version = StrategyVersion(
        strategy_id=strategy.id,
        version=next_version,
        status=ConfigStatus.DRAFT,
        version_note=request.version_note,
        created_by=actor.id,
    )
    session.add(version)
    await session.flush()
    _apply_graph(session, version, graph)
    await session.flush()
    await session.refresh(version, ["nodes", "edges"])
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_CREATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(next_version),
        action="CREATE_STRATEGY_VERSION",
        actor=actor,
        after_value={"graph": _graph_snapshot(version)},
    )
    await session.commit()
    return version


async def update_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    request: StrategyVersionCreateRequest,
    actor: User,
) -> StrategyVersion:
    await lock_policy(session, strategy, version)
    ensure_editable(version)
    graph = request_graph(request)
    await validate_graph(session, graph)
    before = {"graph": _graph_snapshot(version)}
    for edge in list(version.edges):
        await session.delete(edge)
    for node in list(version.nodes):
        await session.delete(node)
    await session.flush()
    _apply_graph(session, version, graph)
    version.version_note = request.version_note or version.version_note
    await session.flush()
    await session.refresh(version, ["nodes", "edges"])
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_UPDATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="UPDATE_STRATEGY_VERSION",
        actor=actor,
        before_value=before,
        after_value={"graph": _graph_snapshot(version)},
    )
    await session.commit()
    return version


async def _validate_simulation_ref(
    session: AsyncSession, version: StrategyVersion, simulation_id: str
) -> str:
    simulation = await session.scalar(
        select(Simulation).where(Simulation.simulation_id == simulation_id)
    )
    if (
        simulation is None
        or simulation.strategy_version_id != version.id
        or simulation.status != SimulationStatus.COMPLETED
    ):
        raise ValidationFailedError(
            "Attached simulation does not match this strategy version",
            details=[{"field": "simulation_id", "issue": f"invalid: {simulation_id}"}],
        )
    evidence = await session.scalar(
        select(SimulationResult).where(SimulationResult.simulation_pk == simulation.id)
    )
    trace = evidence.trace_json if evidence is not None else {}
    draft = trace.get("draft_trace") or {}
    fingerprint = trace.get("plan_fingerprint") or draft.get("strategy", {}).get("plan_fingerprint")
    current = plan_fingerprint(await build_plan(session, version))
    if fingerprint != current:
        raise ValidationFailedError(
            "Simulation evidence is stale; rerun the current resolved strategy before approval",
            details=[{"field": "simulation_id", "issue": "configuration fingerprint mismatch"}],
        )
    return simulation.simulation_id


async def submit_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    actor: User,
    simulation_id: str | None = None,
) -> StrategyVersion:
    await lock_policy(session, strategy, version)
    await validate_graph(session, graph_request_from_version(version))
    before = version.status
    simulation_ref = (
        await _validate_simulation_ref(session, version, simulation_id) if simulation_id else None
    )
    submit_for_approval(version)
    open_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        requested_by=actor,
        change_summary=version.version_note,
        simulation_ref=simulation_ref,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_SUBMITTED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="SUBMIT_FOR_APPROVAL",
        actor=actor,
        before_value={"status": before},
        after_value={"status": version.status, "simulation_ref": simulation_ref},
    )
    await session.commit()
    return version


async def reject_strategy_version(
    session: AsyncSession, strategy: Strategy, version: StrategyVersion, actor: User, reason: str
) -> StrategyVersion:
    await lock_policy(session, strategy, version)
    before = version.status
    reject_version(version)
    await resolve_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        status=ApprovalStatus.REJECTED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_REJECTED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="REJECT_STRATEGY_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": version.status},
    )
    await session.commit()
    return version


async def _retire_competing_active_versions(
    session: AsyncSession, strategy: Strategy, keep: StrategyVersion
) -> list[str]:
    competing = (
        await session.scalars(
            select(StrategyVersion)
            .join(Strategy, StrategyVersion.strategy_id == Strategy.id)
            .where(
                Strategy.product_type == strategy.product_type,
                Strategy.segment == strategy.segment,
                StrategyVersion.status == ConfigStatus.ACTIVE,
                StrategyVersion.id != keep.id,
            )
            .options(selectinload(StrategyVersion.strategy))
        )
    ).all()
    retired: list[str] = []
    for version in competing:
        version.status = ConfigStatus.RETIRED
        version.effective_to = datetime.now(UTC)
        retired.append(f"{version.strategy.strategy_code}_V{version.version}")
    return retired


async def activate_strategy_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    actor: User,
    reason: str | None,
) -> StrategyVersion:
    await lock_policy(session, strategy, version)
    if version.status != ConfigStatus.PENDING_APPROVAL:
        raise ConflictError(
            f"Version {version.version} is {version.status}; submit for approval first"
        )
    await ensure_independent_approver(
        session,
        version.created_by,
        actor,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
    )
    await _verify_references_activatable(session, version)
    if get_settings().require_strategy_simulation_before_activation:
        request = await pending_approval_request(
            session,
            entity_type="STRATEGY_VERSION",
            entity_id=strategy.strategy_code,
            entity_version=str(version.version),
        )
        if request is None or not request.simulation_ref:
            raise ConflictError(
                "A simulation of this strategy version must be attached before activation "
                "(submit for approval with simulation_id)"
            )
        await _validate_simulation_ref(session, version, request.simulation_ref)
    before = version.status
    retired = await _retire_competing_active_versions(session, strategy, version)
    version.status = ConfigStatus.ACTIVE
    version.activated_at = datetime.now(UTC)
    version.activated_by = actor.id
    version.effective_from = datetime.now(UTC)
    await resolve_approval_request(
        session,
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        status=ApprovalStatus.APPROVED,
        decided_by=actor,
        decision_reason=reason,
    )
    record_audit_event(
        session,
        event_type="STRATEGY_VERSION_ACTIVATED",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="ACTIVATE_STRATEGY_VERSION",
        actor=actor,
        reason=reason,
        before_value={"status": before},
        after_value={"status": ConfigStatus.ACTIVE, "retired_versions": retired},
        metadata={"product_type": strategy.product_type, "segment": strategy.segment},
    )
    await session.commit()
    logger.info(
        "strategy.version_activated",
        extra={
            "strategy_code": strategy.strategy_code,
            "version": version.version,
            "retired_versions": retired,
        },
    )
    return version


async def rollback_to_version(
    session: AsyncSession,
    strategy: Strategy,
    version: StrategyVersion,
    actor: User,
    reason: str,
) -> StrategyVersion:
    await lock_policy(session, strategy, version)
    if not reason.strip():
        raise ValidationFailedError(
            "Rollback requires a reason",
            details=[{"field": "reason", "issue": "required"}],
        )
    if version.status != ConfigStatus.RETIRED:
        raise ConflictError(
            f"Only RETIRED versions can be rolled back to (current: {version.status})"
        )
    await _verify_references_activatable(session, version)
    retired = await _retire_competing_active_versions(session, strategy, version)
    version.status = ConfigStatus.ACTIVE
    version.activated_at = datetime.now(UTC)
    version.activated_by = actor.id
    version.effective_from = datetime.now(UTC)
    version.effective_to = None
    record_audit_event(
        session,
        event_type="STRATEGY_ROLLED_BACK",
        entity_type="STRATEGY_VERSION",
        entity_id=strategy.strategy_code,
        entity_version=str(version.version),
        action="ROLLBACK_STRATEGY",
        actor=actor,
        reason=reason,
        before_value={"status": ConfigStatus.RETIRED, "previously_active": retired},
        after_value={"status": ConfigStatus.ACTIVE},
    )
    await session.commit()
    logger.info(
        "strategy.rolled_back",
        extra={"strategy_code": strategy.strategy_code, "version": version.version},
    )
    return version

"""Ordered strategy execution (docs/03 §9, docs/10, docs/11).

The executor consumes an :class:`ExecutablePlan` — a fully resolved,
version-pinned snapshot of the strategy and its referenced configuration —
and produces an :class:`ExecutionResult` containing everything a decision
trace needs. It touches no database and performs no I/O.

Decision aggregation is severity-based engine mechanics: every triggered
action contributes a candidate decision and the most severe candidate wins
(``DECISION_SEVERITY``). If no step produces any candidate, the engine falls
back to ``MANUAL_REVIEW`` with reason ``NO_DECISION_PRODUCED`` — a
conservative safeguard, not credit policy.
"""

import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.decision_table import (
    DecisionTableConfig,
    evaluate_decision_table,
)
from app.engine.dsl import (
    ActionType,
    BranchedRuleDefinition,
    ConditionNode,
    ExpressionRuleDefinition,
    RuleAction,
    RuleBranch,
    RuleDefinition,
)
from app.engine.evaluator import evaluate_node
from app.engine.expression import ast_from_json, evaluate_expression
from app.engine.features import build_base_features, compute_derived_feature
from app.engine.scorecard import ScorecardConfig, resolve_score
from app.shared.domain.enums import (
    DECISION_SEVERITY,
    DecisionType,
    NodeType,
    StepOnError,
    StepStatus,
    StepType,
)

NO_DECISION_REASON_CODE = "NO_DECISION_PRODUCED"
STEP_ERROR_REASON_CODE = "STEP_EXECUTION_ERROR"
MAX_GRAPH_VISITS = 200


class ResolvedRule(BaseModel):
    """A rule pinned to the exact version used for this execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rule_code: str
    version: int
    rule_kind: str = "POLICY_OUTCOME"
    definition: BranchedRuleDefinition | RuleDefinition | ExpressionRuleDefinition


class StepPlan(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    order: int
    step_type: StepType
    name: str
    reference_code: str | None = None
    reference_version: int | None = None
    on_error: StepOnError = StepOnError.FAIL
    config: dict[str, Any] = Field(default_factory=dict)
    rules: list[ResolvedRule] = Field(default_factory=list)
    decision_table: DecisionTableConfig | None = None
    scorecard: ScorecardConfig | None = None


class NodePlan(BaseModel):
    """A resolved strategy graph node.

    Executable business nodes carry the same resolved configuration as the
    legacy :class:`StepPlan`.  START/END are routing sentinels and CONDITION
    carries a safe DSL condition evaluated against the in-memory feature map.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    node_key: str
    node_type: NodeType
    name: str
    reference_code: str | None = None
    reference_version: int | None = None
    on_error: StepOnError = StepOnError.FAIL
    config: dict[str, Any] = Field(default_factory=dict)
    rules: list[ResolvedRule] = Field(default_factory=list)
    decision_table: DecisionTableConfig | None = None
    scorecard: ScorecardConfig | None = None
    condition: ConditionNode | None = None

    def as_step(self, order: int) -> StepPlan:
        """Return the existing step-runner input for an executable node."""

        if self.node_type in (NodeType.START, NodeType.CONDITION, NodeType.END):
            raise ValueError(f"Node type {self.node_type} is not an executable step")
        step_type = StepType(self.node_type.value)
        return StepPlan(
            order=order,
            step_type=step_type,
            name=self.name,
            reference_code=self.reference_code,
            reference_version=self.reference_version,
            on_error=self.on_error,
            config=self.config,
            rules=self.rules,
            decision_table=self.decision_table,
            scorecard=self.scorecard,
        )


class ExecutablePlan(BaseModel):
    strategy_code: str
    strategy_version: int
    strategy_version_id: str
    product_type: str
    segment: str
    nodes: dict[str, NodePlan] = Field(default_factory=dict)
    edges: dict[str, dict[str | None, str]] = Field(default_factory=dict)
    start_key: str = "start"
    # Internal compatibility input for existing engine unit fixtures.  It is
    # normalized into a linear graph at model creation and is not used by the
    # runtime driver afterward.
    steps: list[StepPlan] = Field(default_factory=list, exclude=True)
    legacy_trace_skips: bool = Field(default=False, exclude=True)

    @model_validator(mode="after")
    def normalize_legacy_steps(self) -> "ExecutablePlan":
        self._normalize_legacy_steps()
        return self

    def _normalize_legacy_steps(self) -> None:
        if not self.steps or (self.nodes and not self.legacy_trace_skips):
            return
        start = NodePlan(node_key=self.start_key, node_type=NodeType.START, name="Start")
        nodes: dict[str, NodePlan] = {self.start_key: start}
        edges: dict[str, dict[str | None, str]] = {}
        previous = self.start_key
        for index, step in enumerate(sorted(self.steps, key=lambda item: item.order), start=1):
            key = f"n{index}"
            node_type = (
                NodeType.DECISION_TABLE
                if step.step_type is StepType.OUTPUT
                else NodeType(step.step_type.value)
            )
            nodes[key] = NodePlan(
                node_key=key,
                node_type=node_type,
                name=step.name,
                reference_code=step.reference_code,
                reference_version=step.reference_version,
                on_error=step.on_error,
                config=step.config,
                rules=step.rules,
                decision_table=step.decision_table,
                scorecard=step.scorecard,
            )
            edges[previous] = {None: key}
            previous = key
        self.nodes = nodes
        self.edges = edges
        self.legacy_trace_skips = True


class ValidationFailure(BaseModel):
    field: str
    issue: str


class ExecutionResult(BaseModel):
    final_decision: DecisionType
    reason_codes: list[str]
    risk_grade: str | None = None
    score: float | None = None
    approved_limit: float | None = None
    approved_tenor_months: int | None = None
    pricing_rate: float | None = None
    feature_values: dict[str, Any]
    step_results: list[dict[str, Any]]
    score_result: dict[str, Any] | None = None
    errors: list[dict[str, Any]]
    validation_failures: list[ValidationFailure]
    latency_ms: int
    executed_at: str


def most_severe(candidates: list[DecisionType]) -> DecisionType | None:
    if not candidates:
        return None
    return min(candidates, key=DECISION_SEVERITY.index)


class _ExecutionContext:
    def __init__(self, features: dict[str, Any]) -> None:
        self.features = features
        self.candidates: list[DecisionType] = []
        self.reason_codes: list[str] = []
        self.errors: list[dict[str, Any]] = []
        self.validation_failures: list[ValidationFailure] = []
        self.score_result: dict[str, Any] | None = None
        self.table_output: dict[str, Any] = {}
        self.stop = False

    def add_reason(self, code: str | None) -> None:
        if code and code not in self.reason_codes:
            self.reason_codes.append(code)

    def add_candidate(self, decision: DecisionType | None, reason_code: str | None) -> None:
        if decision is not None:
            self.candidates.append(decision)
        self.add_reason(reason_code)


def run_strategy(plan: ExecutablePlan, payload: dict[str, Any]) -> ExecutionResult:
    # Existing engine fixtures may mutate ``steps`` after construction. Keep
    # that compatibility path deterministic while native graph plans ignore it.
    plan._normalize_legacy_steps()
    started = time.perf_counter()
    executed_at = datetime.now(UTC)
    context = _ExecutionContext(build_base_features(payload))
    step_results: list[dict[str, Any]] = []

    current = plan.edges.get(plan.start_key, {}).get(None)
    visits = 0

    while current is not None and not context.stop:
        visits += 1
        if visits > MAX_GRAPH_VISITS:
            error_record = {
                "step_order": visits,
                "step_name": "graph traversal",
                "error_type": "GraphVisitLimitExceeded",
                "on_error": StepOnError.FAIL.value,
            }
            context.errors.append(error_record)
            context.add_candidate(DecisionType.ERROR, STEP_ERROR_REASON_CODE)
            break

        node = plan.nodes.get(current)
        if node is None:
            error_record = {
                "step_order": visits,
                "step_name": current,
                "error_type": "UnknownGraphNode",
                "on_error": StepOnError.FAIL.value,
            }
            context.errors.append(error_record)
            context.add_candidate(DecisionType.ERROR, STEP_ERROR_REASON_CODE)
            break

        if node.node_type is NodeType.END:
            break

        if node.node_type is NodeType.CONDITION:
            condition_started = time.perf_counter()
            if node.condition is None:
                error_record = {
                    "step_order": visits,
                    "step_name": node.name,
                    "error_type": "MissingCondition",
                    "on_error": StepOnError.FAIL.value,
                }
                context.errors.append(error_record)
                context.add_candidate(DecisionType.ERROR, STEP_ERROR_REASON_CODE)
                break
            matched, details = evaluate_node(node.condition, context.features)
            label = "TRUE" if matched else "FALSE"
            duration_ms = round((time.perf_counter() - condition_started) * 1000, 2)
            step_results.append(
                {
                    "order": visits,
                    "node_key": node.node_key,
                    "type": NodeType.CONDITION.value,
                    "name": node.name,
                    "reference_code": None,
                    "reference_version": None,
                    "status": StepStatus.EVALUATED.value,
                    "duration_ms": duration_ms,
                    "condition_result": matched,
                    "taken_edge": label,
                    "evaluated_conditions": details,
                }
            )
            current = plan.edges.get(current, {}).get(label)
            continue

        step = node.as_step(visits)
        step_started = time.perf_counter()
        try:
            status, detail = _run_step(step, context)
        except Exception as exc:  # noqa: BLE001 - fallback path must be recorded
            status, detail = _apply_step_error(step, context, exc)
        duration_ms = round((time.perf_counter() - step_started) * 1000, 2)
        step_results.append(
            _step_record(step, status, duration_ms, node_key=node.node_key, **detail)
        )
        current = plan.edges.get(current, {}).get(None)

    # Ordered-plan compatibility: historical unit fixtures and pre-M2 plans
    # recorded remaining linear steps as SKIPPED after a stop. Native graph
    # execution records only the visited path.
    while context.stop and plan.legacy_trace_skips and current is not None:
        node = plan.nodes.get(current)
        if node is None or node.node_type in (NodeType.CONDITION, NodeType.END):
            break
        step = node.as_step(len(step_results) + 1)
        step_results.append(_step_record(step, StepStatus.SKIPPED, 0.0, node_key=node.node_key))
        current = plan.edges.get(current, {}).get(None)

    final_decision = _resolve_final_decision(context)
    limit_fields = _resolve_outputs(context)

    return ExecutionResult(
        final_decision=final_decision,
        reason_codes=list(context.reason_codes),
        risk_grade=context.table_output.get("risk_grade")
        or (context.score_result or {}).get("risk_grade"),
        score=(context.score_result or {}).get("score"),
        approved_limit=limit_fields.get("approved_limit"),
        approved_tenor_months=limit_fields.get("approved_tenor_months"),
        pricing_rate=limit_fields.get("pricing_rate"),
        feature_values=dict(context.features),
        step_results=step_results,
        score_result=context.score_result,
        errors=context.errors,
        validation_failures=context.validation_failures,
        latency_ms=int((time.perf_counter() - started) * 1000),
        executed_at=executed_at.isoformat(),
    )


def _step_record(
    step: StepPlan, status: StepStatus, duration_ms: float, **detail: Any
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "order": step.order,
        "type": step.step_type.value,
        "name": step.name,
        "reference_code": step.reference_code,
        "reference_version": step.reference_version,
        "status": status.value,
        "duration_ms": duration_ms,
    }
    record.update(detail)
    return record


def _run_step(step: StepPlan, context: _ExecutionContext) -> tuple[StepStatus, dict[str, Any]]:
    if step.step_type is StepType.VALIDATION:
        return _run_validation_step(step, context)
    if step.step_type is StepType.CALCULATION:
        return _run_calculation_step(step, context)
    if step.step_type is StepType.RULE_SET:
        return _run_rule_set_step(step, context)
    if step.step_type is StepType.SCORECARD:
        return _run_scorecard_step(step, context)
    if step.step_type in (StepType.DECISION_TABLE, StepType.OUTPUT):
        return _run_decision_table_step(step, context)
    raise ValueError(f"Unsupported step type: {step.step_type}")  # pragma: no cover


def _run_validation_step(
    step: StepPlan, context: _ExecutionContext
) -> tuple[StepStatus, dict[str, Any]]:
    required = step.config.get("required_fields", [])
    missing = [field for field in required if context.features.get(field) is None]
    for field in missing:
        context.validation_failures.append(ValidationFailure(field=field, issue="required"))
    if missing:
        context.stop = True
        return StepStatus.FAILED, {"missing_fields": missing}
    return StepStatus.PASSED, {"checked_fields": list(required)}


def _run_calculation_step(
    step: StepPlan, context: _ExecutionContext
) -> tuple[StepStatus, dict[str, Any]]:
    calculated: dict[str, Any] = {}
    for code in step.config.get("calculations", []):
        value = compute_derived_feature(code, context.features)
        context.features[code] = value
        calculated[code] = value
    return StepStatus.PASSED, {"calculated": calculated}


def _run_rule_set_step(
    step: StepPlan, context: _ExecutionContext
) -> tuple[StepStatus, dict[str, Any]]:
    rule_results: list[dict[str, Any]] = []
    triggered = False
    for resolved in step.rules:
        if isinstance(resolved.definition, ExpressionRuleDefinition):
            value = evaluate_expression(
                ast_from_json(resolved.definition.expression_ast), context.features
            )
            action = RuleAction(
                type=ActionType.SET_OUTPUT,
                target=resolved.definition.output_target,
                value=value,
            )
            expression_applied = _apply_action(action, context)
            rule_results.append(
                {
                    "rule_code": resolved.rule_code,
                    "version": resolved.version,
                    "rule_kind": resolved.rule_kind,
                    "matched": True,
                    "status": StepStatus.TRIGGERED.value,
                    "evaluated_conditions": [],
                    "matched_branch": "expression",
                    "actions_applied": [expression_applied],
                }
            )
            triggered = True
            if context.stop:
                break
            continue

        legacy = isinstance(resolved.definition, RuleDefinition)
        if isinstance(resolved.definition, RuleDefinition):
            branches = [
                RuleBranch(
                    when=resolved.definition.condition,
                    then=[resolved.definition.action],
                )
            ]
            default = None
        else:
            branches = resolved.definition.branches
            default = resolved.definition.default
        matched_branch: int | str | None = None
        matched_actions: list[Any] = []
        details: list[dict[str, Any]] = []
        for branch_index, branch in enumerate(branches):
            branch_matched, branch_details = evaluate_node(branch.when, context.features)
            details.extend(branch_details)
            if branch_matched:
                matched_branch = branch_index
                matched_actions = branch.then
                break
        if matched_branch is None and default is not None:
            matched_branch = "default"
            matched_actions = default
        matched = matched_branch is not None
        record: dict[str, Any] = {
            "rule_code": resolved.rule_code,
            "version": resolved.version,
            "rule_kind": resolved.rule_kind,
            "matched": matched,
            "status": StepStatus.TRIGGERED.value if matched else StepStatus.PASSED.value,
            "evaluated_conditions": details,
        }
        if matched:
            triggered = True
            applied = [_apply_action(action, context) for action in matched_actions]
            record["matched_branch"] = matched_branch
            if legacy:
                record["action_applied"] = applied[0]
            else:
                record["actions_applied"] = applied
        rule_results.append(record)
        if context.stop:
            break
    status = StepStatus.TRIGGERED if triggered else StepStatus.PASSED
    return status, {"rule_results": rule_results}


def _apply_action(action: Any, context: _ExecutionContext) -> dict[str, Any]:
    applied: dict[str, Any] = {"type": action.type.value}
    if action.type is ActionType.SET_DECISION:
        context.add_candidate(action.decision, action.reason_code)
        applied["decision"] = action.decision.value if action.decision else None
    elif action.type is ActionType.ROUTE_MANUAL_REVIEW:
        context.add_candidate(DecisionType.MANUAL_REVIEW, action.reason_code)
        applied["decision"] = DecisionType.MANUAL_REVIEW.value
    elif action.type is ActionType.ADD_REASON_CODE:
        context.add_reason(action.reason_code)
    elif action.type is ActionType.SET_OUTPUT:
        if action.target:
            value = action.value
            if action.expression_ast is not None:
                value = evaluate_expression(ast_from_json(action.expression_ast), context.features)
            context.features[action.target] = value
            applied["target"] = action.target
            applied["value"] = value
        context.add_reason(action.reason_code)
    elif action.type is ActionType.STOP_EXECUTION:
        context.add_candidate(action.decision, action.reason_code)
        context.stop = True
        applied["decision"] = action.decision.value if action.decision else None
    elif action.type is ActionType.CONTINUE:
        context.add_reason(action.reason_code)
    if action.reason_code:
        applied["reason_code"] = action.reason_code
    if action.stop_execution:
        context.stop = True
        applied["stopped_execution"] = True
    return applied


def _run_scorecard_step(
    step: StepPlan, context: _ExecutionContext
) -> tuple[StepStatus, dict[str, Any]]:
    if step.scorecard is None:
        raise ValueError(f"Scorecard step '{step.name}' has no scorecard configuration")
    outcome = resolve_score(step.scorecard, context.features)
    context.score_result = {
        "score": outcome.score,
        "risk_grade": outcome.risk_grade,
        "model_version": outcome.model_version,
        "scorecard_code": step.reference_code,
        "scorecard_version": step.reference_version,
        "score_missing": outcome.score_missing,
    }
    context.features["score.value"] = outcome.score
    context.features["score.risk_grade"] = outcome.risk_grade
    if outcome.score_missing:
        config = step.scorecard
        context.add_candidate(config.missing_score_decision, config.missing_score_reason_code)
        return StepStatus.TRIGGERED, {"score_result": context.score_result}
    return StepStatus.PASSED, {"score_result": context.score_result}


def _run_decision_table_step(
    step: StepPlan, context: _ExecutionContext
) -> tuple[StepStatus, dict[str, Any]]:
    if step.decision_table is None:
        raise ValueError(f"Decision table step '{step.name}' has no table configuration")
    evaluation = evaluate_decision_table(step.decision_table, context.features)
    output = evaluation.output

    decision = output.decision
    reason_code = output.reason_code
    approved_limit = output.approved_limit
    if output.approved_limit_pct_of is not None:
        base = context.features.get(output.approved_limit_pct_of.field)
        if isinstance(base, (int, float)) and not isinstance(base, bool):
            approved_limit = round(float(base) * output.approved_limit_pct_of.pct, 2)

    # Configurable escalation: approval with a limit below the requested amount
    # becomes a conditional approval.
    requested = context.features.get("loan.requested_amount")
    if (
        decision is DecisionType.APPROVE
        and approved_limit is not None
        and isinstance(requested, (int, float))
        and not isinstance(requested, bool)
        and float(requested) > approved_limit
        and step.decision_table.above_limit_reason_code
    ):
        decision = DecisionType.APPROVE_WITH_CONDITION
        context.add_reason(step.decision_table.above_limit_reason_code)

    context.add_candidate(decision, reason_code)
    context.table_output = {
        "decision": decision.value,
        "risk_grade": output.risk_grade,
        "approved_limit": approved_limit,
        "approved_tenor_months": output.approved_tenor_months,
        "pricing_rate": output.pricing_rate,
    }
    status = StepStatus.TRIGGERED if evaluation.matched else StepStatus.FAILED
    return status, {
        "table_result": {
            "matched": evaluation.matched,
            "row_index": evaluation.row_index,
            "output": context.table_output,
            "row_details": evaluation.row_details,
        }
    }


def _apply_step_error(
    step: StepPlan, context: _ExecutionContext, exc: Exception
) -> tuple[StepStatus, dict[str, Any]]:
    error_record = {
        "step_order": step.order,
        "step_name": step.name,
        "error_type": type(exc).__name__,
        "on_error": step.on_error.value,
    }
    context.errors.append(error_record)
    if step.on_error is StepOnError.MANUAL_REVIEW:
        context.add_candidate(DecisionType.MANUAL_REVIEW, STEP_ERROR_REASON_CODE)
        return StepStatus.FAILED, {"error": error_record, "fallback": "MANUAL_REVIEW"}
    if step.on_error is StepOnError.CONTINUE:
        return StepStatus.FAILED, {"error": error_record, "fallback": "CONTINUE"}
    context.add_candidate(DecisionType.ERROR, STEP_ERROR_REASON_CODE)
    context.stop = True
    return StepStatus.FAILED, {"error": error_record, "fallback": "FAIL"}


def _resolve_final_decision(context: _ExecutionContext) -> DecisionType:
    if context.validation_failures:
        return DecisionType.ERROR
    decision = most_severe(context.candidates)
    if decision is None:
        context.add_reason(NO_DECISION_REASON_CODE)
        return DecisionType.MANUAL_REVIEW
    return decision


def _resolve_outputs(context: _ExecutionContext) -> dict[str, Any]:
    final = most_severe(context.candidates)
    approve_like = final in (DecisionType.APPROVE, DecisionType.APPROVE_WITH_CONDITION)
    if not approve_like or not context.table_output:
        return {}
    return {
        "approved_limit": context.table_output.get("approved_limit"),
        "approved_tenor_months": context.table_output.get("approved_tenor_months"),
        "pricing_rate": context.table_output.get("pricing_rate"),
    }

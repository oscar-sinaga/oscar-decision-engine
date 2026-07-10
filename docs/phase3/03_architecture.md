# Phase 3 Architecture — DAG Execution Engine

## 1. Verified current state (do NOT re-discover; verified 2026-07-11)

- `backend/app/engine/` is framework/DB-free (no fastapi/sqlalchemy imports). Modules: `dsl.py`, `evaluator.py`, `decision_table.py`, `scorecard.py`, `features.py`, `executor.py`.
- `dsl.py` **already supports nested `all`/`any`/`not` condition trees** (recursive `ConditionNode`) and action types `SET_DECISION`, `ADD_REASON_CODE`, `SET_ATTRIBUTE`, `ROUTE_MANUAL_REVIEW`, `STOP_EXECUTION`, `CONTINUE`.
- `executor.py:_apply_action` **already writes `SET_ATTRIBUTE` into `context.features`** (executor.py:252-257) — later steps can read rule-written values today. Phase 3 formalizes this as `SET_OUTPUT` + catalog enforcement; it does not invent the mechanism.
- Strategy execution today: `ExecutablePlan` (built by `backend/app/modules/strategies/plan_builder.py` from `strategy_steps` rows) is a **list** executed in order by `run_strategy`; severity aggregation picks the most severe candidate decision; `STOP_EXECUTION` and `on_error` (`FAIL`/`MANUAL_REVIEW`/`CONTINUE`) short-circuit.
- `plan_builder.build_plan` is shared by production (`decisions/service.py`) and simulation (`simulations/service.py`) — the single point guaranteeing "simulation = production".
- Trace: `decision_traces.step_results` = ordered list of step dicts (order, type, name, reference_code/version, status, duration_ms, rule_results...).

## 2. Design overview

Replace the *shape* of a strategy version (ordered list → directed graph) while keeping every other invariant: deterministic, versioned, immutable when active, trace-reproducible, simulation-identical, governance-unchanged.

```
START ──▶ VALIDATION ──▶ CALCULATION ──▶ CONDITION(fraud.device_risk_score > 0.5)
                                          │ TRUE                    │ FALSE
                                          ▼                         ▼
                                     RULE_SET(FRAUD_DEEP)      RULE_SET(FRAUD_BASIC)
                                          │                         │
                                          └────────────▶ SCORECARD ◀┘        (rejoin allowed)
                                                             │
                                                        DECISION_TABLE
                                                             │
                                                            END
```

## 3. Node and edge model

**Node types** (enum `NodeType`): `START`, `VALIDATION`, `CALCULATION`, `RULE_SET`, `SCORECARD`, `DECISION_TABLE`, `CONDITION`, `END`.

- `START`: exactly one per graph; no config; exactly one outgoing edge; not executed.
- `VALIDATION`/`CALCULATION`/`RULE_SET`/`SCORECARD`/`DECISION_TABLE`: identical semantics/config to today's step types (`reference_code`, `config_json`, `on_error`); **at most one** outgoing edge (none ⇒ terminal).
- `CONDITION`: `config_json.condition` = a `ConditionNode` (same DSL as rules, same catalog validation); **exactly two** outgoing edges labeled `TRUE` and `FALSE`. Missing/null feature values evaluate exactly as rule conditions do today (no match ⇒ FALSE path). Condition nodes are recorded in trace but set no decision.
- `END`: zero outgoing edges; optional (a step node without outgoing edge is an implicit end); recommended for canvas clarity.

**Edges**: `{from_node_key, to_node_key, label}` — `label ∈ {TRUE, FALSE}` required from CONDITION nodes, must be `null` otherwise.

**Node identity**: `node_key` is a stable string (slug, unique per version) authored by the client/canvas; used in edges, traces, and diffs. Server generates one when absent (`n1`, `n2`, ...).

## 4. Graph validation (at version create/update; re-checked at activation)

Reject with `VALIDATION_ERROR` (422) listing every violation:
1. Exactly one `START`.
2. Edge endpoints reference existing node keys; no self-loops; no duplicate `(from,to,label)`.
3. Out-degree: START = 1; CONDITION = 2 with labels exactly `{TRUE, FALSE}`; others ≤ 1; END = 0.
4. **Acyclic** (Kahn/DFS). Rejoins (in-degree > 1) are legal.
5. Every node reachable from START (no orphans).
6. Reference resolution per node type (existing checks reused): rule set / decision table / scorecard codes must exist; at **activation**, referenced tables/scorecards must have an ACTIVE version (reuse `_verify_references_activatable`).
7. CONDITION conditions validate against the feature catalog (reuse rule condition validation) — including `outputs.*` features that earlier rules may write.
8. Graph size limits: ≤ 100 nodes, ≤ 200 edges (config constants).

Acyclicity + out-degree ≤ 1 (except CONDITION choosing exactly one edge) ⇒ any execution is a **simple path**, trivially deterministic and terminating; a runtime visit-counter (max 200 visits) remains as a defense-in-depth guard.

## 5. Execution semantics (`engine/executor.py`)

`ExecutablePlan` becomes:
```python
@dataclass
class ExecutablePlan:
    strategy_code: str; strategy_version: int
    nodes: dict[str, NodePlan]          # node_key -> resolved plan (same resolution as today's StepPlan)
    edges: dict[str, dict[str|None, str]]  # from_key -> {label_or_None: to_key}
    start_key: str
```
Traversal:
```
current = follow(start)
while current:
    if node.type == CONDITION:
        result = evaluate(condition, context.features)   # existing evaluator
        record trace entry {node_key, type: CONDITION, result, taken_edge}
        current = edges[current][ "TRUE" if result else "FALSE" ]
    else:
        run node exactly as the current step runner does (validation/calc/rules/scorecard/table)
        if STOP_EXECUTION raised or on_error(FAIL) → break (same as today)
        current = edges[current].get(None)               # None ⇒ terminal
```
- Severity aggregation, reason codes, validation-failure handling, `on_error`, scorecard fallback: **unchanged** (reuse the existing step-runner functions; only the *driver loop* changes from list iteration to edge following).
- Trace `step_results[]`: same entry shape as today **plus** `node_key` and (for CONDITION) `condition_result`/`taken_edge`; `order` = visit sequence (1..n) so existing UI keeps rendering. Trace `strategy` gains `"execution": "GRAPH"`.

## 6. Data model & migration (details in `07_data_model.md`)

- New tables `strategy_nodes`, `strategy_edges` (per strategy_version, with canvas `position_x/y`).
- **Data migration** (single Alembic revision): for every existing `strategy_versions` row, convert its ordered `strategy_steps` into `START → s1 → ... → sn` (+ implicit terminal), preserving name/reference/on_error/config and generating positions (x = 240*i); then drop `strategy_steps`. Downgrade recreates `strategy_steps` from **linear** graphs (best effort; documented).
- Golden tests (`10_test_plan.md` §5) prove seeded strategies produce identical decisions pre/post migration.

## 7. API compatibility (details in `08_api_contract.md`)

- `POST/PUT /v1/strategies/{id}/versions[...]` accept **either** `{steps: [...]}` (legacy; server converts to linear graph) **or** `{graph: {nodes: [...], edges: [...]}}`. Responses always include `graph` and additionally `steps` **derived** when the graph is linear (so existing frontend/tests keep working until P3.5 lands).
- `plan_builder` resolves graphs; simulation, activation checks, rollback, maker-checker, simulation-attachment: unchanged call sites.

## 8. Impact map (files an implementing agent must touch in P3.4)

| Layer | Files |
|---|---|
| Engine | `backend/app/engine/executor.py` (traversal driver, NodePlan), `engine/__init__.py` exports |
| Modules | `modules/strategies/models.py` (+nodes/edges), `schemas.py` (GraphRequest/Response), `service.py` (validation §4), `plan_builder.py` (graph resolution) |
| Migration | new Alembic revision (tables + data conversion + drop strategy_steps) |
| Seeds | `app/seed.py` seeds the LEASEBACK_MOTOR strategy as a linear graph |
| Tests | executor graph tests, validation tests, migration golden tests, adapt strategy API tests |
| Frontend (P3.5) | `routes/strategies/[id]` canvas; until then the derived-`steps` response keeps the current screen working |

## 9. Why not parallel branches / sub-flows now

Parallel paths require merge semantics for candidate decisions/outputs (ordering of `SET_OUTPUT` writes becomes ambiguous → breaks determinism guarantees that credit audit relies on). Sub-flow nodes add cross-version pinning complexity. Both are cleanly additive later (new node types) and are parked in the stretch backlog (`02_scope.md` §3).

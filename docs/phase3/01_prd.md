# Phase 3 PRD — Generic Rule Authoring & Visual Decision Flow

## 1. Problem statement

Benchmarking against IDX iDecision (screenshots reviewed 2026-07-10) exposed structural gaps, confirmed by an external review:

1. **Rule model is outcome-bound.** Every OSCAR rule terminates in a final decision + reason code. iDecision rules are *generic*: a rule can produce a **value** (`WHEN saving_balance > 50jt THEN 20000 ... ELSE 0` → output `Harga Kendaraan`), a classification, a parameter update, or a decision. OSCAR cannot express "rule 1 sets `collateral_risk=HIGH`, rule 2 sets `affordability_risk=HIGH`, decision table combines them" from the UI — even though the engine's `SET_ATTRIBUTE` already supports the runtime half.
2. **No multi-branch rules.** One condition → one action. No CASE WHEN chains, no ELSE/default.
3. **Rule authoring is JSON-first.** The detail page edits raw JSON; the create-builder supports only one flat ALL/ANY group, untyped operators, untyped value input, no human-readable preview. Unsuitable for the target persona (non-technical Risk Policy Analyst).
4. **No output catalog.** iDecision constrains rule outputs to a governed catalog (like its input parameter catalog). OSCAR's feature catalog (Phase 2) governs *inputs* only.
5. **Strategies are linear.** iDecision designs flows on a **node canvas with conditional branching** (Condition node → labeled edges). OSCAR executes a fixed ordered list.
6. **No power-user text authoring.** iDecision offers Formatted SQL / Free SQL. OSCAR has nothing between the builder and raw JSON.

## 2. Goals

| ID | Goal | Measure |
|----|------|---------|
| G1 | Rules can produce **outputs/classifications**, not only decisions | A value-producing rule (iDecision "AR balance" example) is authorable end-to-end from the UI and its output is consumed by a later decision table |
| G2 | Multi-branch **CASE WHEN / ELSE** rules with **multiple actions** per branch | Branch rule executes first-match with ELSE; trace shows matched branch |
| G3 | **Builder-first authoring** for non-technical analysts | A rule can be created *and edited* without ever seeing JSON; JSON demoted to an "Advanced" tab |
| G4 | **Typed authoring** | Operators filtered by feature data type; value inputs typed (number/string/boolean/date); invalid combinations rejected server-side |
| G5 | Strategies are **decision-flow graphs (DAG)** with condition branches, designed on a **visual node canvas** | The iDecision-style flow (condition node → two labeled paths → different sub-steps) is buildable, executable, and fully traced |
| G6 | **Safe expression language** (admin-gated) with **SQL-style preview** | Admin authors `CASE WHEN ... THEN ... ELSE ... END` text; server validates against catalog; preview panel renders SQL-style text for any rule; **no SQL/eval is ever executed** |
| G7 | **Decision-table grid editor** | Analyst edits rows/columns in a typed grid with inline overlap warnings; no JSON |
| G8 | Nothing regresses | All existing tests keep passing; existing seeded strategies/decisions/traces stay reproducible; every production decision remains deterministic, versioned, traced, audited |

## 3. Non-goals (Phase 3)

- Raw SQL execution in any form (see ADR-012; expression preview is display-only).
- Parallel/concurrent flow paths, loops, or wait states in the DAG (single-token traversal only).
- The removed old Phase-3 items: fraud monitoring, champion/challenger, model/drift monitoring, portfolio/vintage dashboards, collection integration.
- Real external data-source integrations and deployment/environment promotion (still deferred; business decision).
- AI-assisted rule authoring.

## 4. Personas and what changes for them

| Persona | Today | After Phase 3 |
|---|---|---|
| Risk Policy Analyst (primary) | Can create simple outcome rules via builder; edits = JSON | Authors branch rules, value rules, classification rules, decision-table grids, and flow graphs entirely visually |
| Risk Manager | Approves versions; reads JSON diffs | Same governance (maker-checker, simulation attachment) over the new artifacts; readable previews in approval context |
| Admin / Engineering | — | Additionally authors expression rules (`rule.author_expression`); manages output/category catalogs |
| Compliance / Auditor | Reads traces | Traces additionally show graph path and matched branches; reproducibility guarantees unchanged |

## 5. Functional requirements

### FR-RULE — Rule model v2 (spec: `04_rule_model_v2.md`)
- FR-RULE-1: A rule version is either legacy shape `{condition, action}` (still valid forever) or v2 shape `{branches: [{when, then[]}], default: then[]?}`.
- FR-RULE-2: Branch evaluation is **first-match** top-down; `default` (ELSE) applies when no branch matches; a rule with no match and no default is a non-event (PASSED).
- FR-RULE-3: A branch's `then` is an **ordered list of actions**; supported: `SET_OUTPUT`, `SET_DECISION`, `ADD_REASON_CODE`, `ROUTE_MANUAL_REVIEW`, `STOP_EXECUTION`, `CONTINUE`.
- FR-RULE-4: `SET_OUTPUT.target` must be an **active, writable** feature-catalog entry; the written value becomes readable by every later rule/table/condition in the same execution.
- FR-RULE-5: Operators are validated against the target feature's `data_type` (matrix in `04_rule_model_v2.md` §5) at create/update time.
- FR-RULE-6: Rules carry a `rule_kind` (`POLICY_OUTCOME` | `STATEMENT` | `CLASSIFICATION` | `EXPRESSION`) for listing/filtering; behavior derives from content, not the label.
- FR-RULE-7: Rule test endpoint accepts feature values and returns matched branch index, per-condition evaluation, and actions that would apply.
- FR-RULE-8: `GET /v1/rules/{id}/usage` lists rule sets and strategies (via rule sets) referencing the rule.

### FR-FLOW — DAG strategies (spec: `03_architecture.md`)
- FR-FLOW-1: A strategy version is a graph of typed nodes (`START`, `VALIDATION`, `CALCULATION`, `RULE_SET`, `SCORECARD`, `DECISION_TABLE`, `CONDITION`, `END`) connected by directed edges.
- FR-FLOW-2: `CONDITION` nodes hold a condition (same DSL as rules) and exactly two outgoing edges labeled `TRUE`/`FALSE`; all other nodes have at most one outgoing edge.
- FR-FLOW-3: Graphs are validated at save: exactly one START, acyclic, all nodes reachable, terminal correctness (see `03_architecture.md` §4).
- FR-FLOW-4: Execution is single-token deterministic traversal; trace records the visited path and each condition's taken edge.
- FR-FLOW-5: Legacy `steps[]` payloads remain accepted (server converts to a linear graph); existing DB strategies are auto-converted by migration with **provably identical decisions** (golden tests).
- FR-FLOW-6: All existing governance applies unchanged: versioning, immutability of active versions, maker-checker, mandatory simulation attachment, rollback, audit events.

### FR-CANVAS — Visual designer (spec: `09_screen_spec.md` §2)
- FR-CANVAS-1: Node canvas (Svelte Flow) with palette, drag-drop, connectable edges, node config drawer, condition editing via the same condition-builder component.
- FR-CANVAS-2: Draft versions are editable; PENDING/ACTIVE/RETIRED render read-only.
- FR-CANVAS-3: Graph validation errors surface inline (node/edge highlighting + message list) before save.
- FR-CANVAS-4: Migrated linear strategies auto-layout left-to-right.

### FR-EXPR — Expression language (spec: `05_expression_language.md`)
- FR-EXPR-1: Text form supports value expressions, boolean expressions, and `CASE WHEN ... THEN ... ELSE ... END`.
- FR-EXPR-2: Parsed to a whitelisted AST; identifiers must be catalog features; **no eval/exec/SQL**; hard limits on length/depth/node-count; deterministic (no time/random).
- FR-EXPR-3: Gated by new permission `rule.author_expression` (ADMIN-only initially).
- FR-EXPR-4: `POST /v1/expressions/validate` returns parse result, referenced features, inferred type, and normalized preview.
- FR-EXPR-5: Every rule (builder- or expression-authored) exposes a **read-only SQL-style preview** clearly labeled "preview only — never executed".

### FR-TABLE — Decision-table grid (spec: `09_screen_spec.md` §3)
- FR-TABLE-1: Grid editor with typed condition columns (catalog-picked, including rule outputs) and output columns; add/remove/reorder rows; hit-policy selector.
- FR-TABLE-2: Backend overlap warnings render inline on offending rows.

### FR-CAT — Catalogs (spec: `06_catalogs_and_metadata.md`)
- FR-CAT-1: Feature catalog gains `writable`; writable entries form the **output catalog** (seeded: `outputs.*` examples).
- FR-CAT-2: Rule categories become a managed catalog (seeded from the current enum) instead of a hardcoded list.
- FR-CAT-3: `/v1/meta` exposes operators-by-data-type, rule kinds, node types, writable outputs, and categories so no frontend list is hardcoded.

## 6. Acceptance criteria (phase-level)

The phase is done when, on a rebuilt compose stack, a Playwright-driven session can — **without editing JSON**:
1. Add writable outputs `outputs.collateral_risk` and `outputs.vehicle_price_band` in the catalog screen.
2. Author a **STATEMENT** rule reproducing the iDecision example (3 CASE WHEN branches + ELSE writing a numeric output), see its human-readable and SQL-style previews, and dry-run it via the generated test form.
3. Author two **CLASSIFICATION** rules setting risk outputs, then build a decision table **in the grid** combining those outputs into final decisions.
4. Design a strategy on the **canvas** containing a CONDITION node with TRUE/FALSE paths to different rule sets, save the draft, attach a simulation, submit, approve (maker≠checker), and activate.
5. Submit a synthetic application through `/v1/decisions` and see the trace render the graph path, the taken branch of every condition, matched rule branches, and outputs set.
6. As admin, author an **EXPRESSION** rule textually; as riskanalyst, be denied (`403`).
7. All gates pass: backend ruff+mypy+pytest (old 114 + new), frontend lint/check/vitest/build, migrations from clean DB, golden reproducibility tests, Playwright suite.

## 7. Success metrics

- 100% of the authoring flows in §6 completable with zero JSON editing.
- 0 regressions in the pre-existing test suite; decision outputs for all seeded golden payloads byte-identical (excluding IDs/timestamps) before vs after the graph migration.
- Expression fuzz suite: 0 successful escapes (no attribute access, no imports, no callables outside whitelist).
- P95 local decision latency remains under the existing 500ms budget with graph execution.

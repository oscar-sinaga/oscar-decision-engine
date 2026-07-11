# Phase 3 Atomic Task Breakdown

**Purpose:** execution checklist sized for any coding agent, including smaller/cheaper models. Each task is one sitting of work with an exact file list, a done-condition, and a verify command. **Execute strictly top-to-bottom. Do not start a task before the previous task's verify command passes.** Mark each task in `IMPLEMENTATION_STATUS.md` as you go.

Verify shorthand used below:
- `BE-FAST` = `cd backend && uv run pytest -q -x <given test path>`
- `BE-FULL` = `cd backend && uv run ruff format --check . && uv run ruff check . && uv run mypy app tests && uv run pytest -q`
- `FE-FULL` = `cd frontend && npm run lint && npm run check && npm run test:unit -- --run && npm run build`

---

## P3.1 — Rule Model v2

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 1.1 | Add `RuleBranch` (`when: ConditionNode`, `then: list[RuleAction]` 1..10) and `BranchedRuleDefinition` (`branches` 1..20, `default: list[RuleAction] | None`) to the DSL. Add `normalize_rule_definition(condition_json, action_json) -> BranchedRuleDefinition` that also converts the legacy `{condition, action}` shape into one branch. Extend `ActionType` with `SET_OUTPUT` and add fields `target: str | None`, `value: Any` to `RuleAction`; treat incoming `SET_ATTRIBUTE` as alias for `SET_OUTPUT` during validation | `backend/app/engine/dsl.py` | unit tests for normalization + shape limits pass | new `tests/unit/test_dsl_v2.py`, BE-FAST |
| 1.2 | Teach the executor branches: in `_run_rule_set_step`, evaluate `branches` top-down (first match), apply all `then` actions via existing `_apply_action`, apply `default` when nothing matches; record `matched_branch` (int or `"default"`) and `actions_applied` (list) in the rule result; keep `action_applied` key for legacy single-action rules. `SET_OUTPUT` writes `context.features[target] = value` (mechanism already exists at `_apply_action` SET_ATTRIBUTE arm) | `backend/app/engine/executor.py` | branch/ELSE/multi-action unit tests pass; ALL existing tests still pass | new `tests/unit/test_executor_branches.py`, then BE-FULL |
| 1.3 | Alembic migration **M1** exactly per `07_data_model.md` §M1 (rule_versions + rule_kind/expression_text, features + writable, new rule_categories with enum-seeded rows). Apply to dev DB | new `backend/alembic/versions/*_p3_rule_model_v2.py` | `alembic upgrade head` then `downgrade -1` then `upgrade head` all succeed on seeded dev DB (port 5455) | commands in `11_execution_plan.md` header |
| 1.4 | API: rules create/version accept exactly one authoring form (`condition+action` XOR `branches[+default]`); persist v2 body in `condition_json`, set `action_json=NULL` for v2; add `rule_kind` (default POLICY_OUTCOME); response includes normalized `branches/default` + `rule_kind`. Typed-operator matrix (`04` §5) enforced in `validate_rule_definition` using catalog `data_type`; SET_OUTPUT target checks stubbed to "feature exists & active" (writable check comes in 2.2) | `backend/app/modules/rules/{models,schemas,service,router}.py` | integration tests for v2 create, XOR-422, typed-operator 422 pass | new `tests/integration/test_rules_v2.py`, BE-FAST |
| 1.5 | Extend rule test endpoint response: `matched_branch`, `actions_applied`, `outputs_after` | `service.py`, `router.py`, `schemas.py` (rules) | test-endpoint integration test passes | BE-FAST |
| 1.6 | Worked patterns from `04` §7 as integration tests (statement rule feeding a decision table; classification pair; mixed branch). Update `IMPLEMENTATION_STATUS.md`. Commit `feat(rules): rule model v2 with CASE WHEN branches and typed outputs` | tests + status doc | **BE-FULL green** (expect 114 old + ~15 new) | BE-FULL |

## P3.2 — Catalogs & metadata (no new migration; M1 already covers schema)

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 2.1 | `features.writable` in API: create/patch/list-filter + `source: RULE_OUTPUT`; reject `writable=true` when `source == PAYLOAD` (422). Seed `outputs.*` rows per `06` §1 in `seed_features` | `modules/features/{models,router,service}.py`, `app/seed.py` | features integration tests pass | extend `test_feature_catalog.py`, BE-FAST |
| 2.2 | Enforce SET_OUTPUT target = active+writable feature; value literal type must match `data_type` | `modules/rules/service.py` | 422 tests for non-writable / PAYLOAD / wrong-type pass | BE-FAST |
| 2.3 | Rule categories: model `RuleCategory` in `modules/rules/models.py`, router file `modules/rules/categories_router.py` (`GET/POST /v1/rule-categories`, `PATCH /{id}`), wire in `api/v1/router.py`; rules create validates category against active rows; audited events `RULE_CATEGORY_*` | listed files | category CRUD + unknown-category-422 tests pass | new `tests/integration/test_rule_categories.py`, BE-FAST |
| 2.4 | `/v1/meta` additions exactly per `06` §3 (widen `features[]`; add `operators_by_type`, `rule_kinds`, `action_types`, `node_types`, `edge_labels`, `rule_categories`, `writable_outputs`) | `api/v1/meta.py` | meta integration assertions pass | BE-FAST |
| 2.5 | `GET /v1/rules/{id}/usage` per `06` §4 (rule sets via `rule_set_members`; strategies via steps—switches to nodes after P3.4 automatically if it queries by reference_code table of the strategies module) | `modules/rules/router.py` | usage test passes (rule in set, set referenced by seeded strategy) | BE-FAST |
| 2.6 | Permission `rule.author_expression` in `Permissions`, `ALL_PERMISSIONS`, ADMIN default grant (seed only, **no migration**). Status update + commit `feat(catalog): output catalog, rule categories, typed metadata` | `modules/auth/permissions.py`, `app/seed.py` | **BE-FULL green** | BE-FULL |

## P3.3 — Rule authoring UX (frontend only)

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 3.1 | `frontend/src/lib/rule-format.ts`: types for builder state; `jsonToBuilder` (legacy + v2 + nested; returns `{state, supported: boolean}`), `builderToJson`, `humanPreview(state): string` | new file + `lib/api/types.ts` | Vitest round-trip suite passes (legacy, v2 nested, branch+else, unsupported→`supported:false`) | new `src/lib/rule-format.spec.ts`, `npm run test:unit -- --run` |
| 3.2 | ConditionBuilder v2: nested groups (recursive component, ALL/ANY/NOT, add group/condition, max depth 5), searchable feature combobox (from meta, shows type chip), operator options from `operators_by_type`, typed value inputs (number/text/taglist/boolean select/date) | `lib/components/ConditionBuilder.svelte` (+ small `FeaturePicker.svelte`) | svelte-check clean; manual smoke via dev server | `npm run check` |
| 3.3 | `BranchEditor.svelte` + `ActionListEditor.svelte` per `09` §1.3 (branch cards, reorder, ELSE toggle; action rows typed; SET_OUTPUT target from `writable_outputs`) | new components | check clean | `npm run check` |
| 3.4 | Rewrite `/rules/new`: kind selector (EXPRESSION hidden without permission), builder v2 + branch editor, right column live human preview + JSON tab | `routes/rules/new/+page.svelte` | create a STATEMENT rule end-to-end against local stack without JSON | manual + Playwright later (task 8.2) |
| 3.5 | Rewrite `/rules/[id]` builder-first: parse stored JSON → builder (edit only when DRAFT and `supported`); tabs Human/JSON; generated typed test form from referenced features calling test endpoint; "Used by" panel from `/usage`; keep lifecycle buttons | `routes/rules/[id]/+page.svelte` | edit + dry-run + usage visible without JSON | manual |
| 3.6 | FE-FULL + status + commit `feat(ui): builder-first rule authoring with branches and typed inputs` | — | **FE-FULL green**, BE suite untouched | FE-FULL |

## P3.4 — DAG execution engine (highest risk — follow order exactly)

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 4.1 | **Golden tests FIRST**: run the 4 canonical payloads against current seeded strategy, hard-code expected `(decision, reason_codes, risk_grade, approved_limit)` into `tests/integration/test_golden_reproducibility.py`; must pass on CURRENT code before anything else changes | new test file | green on unmodified engine | BE-FAST |
| 4.2 | Engine graph types: `NodePlan` (wraps current StepPlan fields + `node_key`, `node_type`, condition for CONDITION), `ExecutablePlan{nodes: dict, edges: dict[str, dict[str|None,str]], start_key}`; rewrite `run_strategy` driver to edge-following per `03` §5 (reuse ALL step-runner functions unchanged); visit-guard 200 | `engine/executor.py` | unit tests: linear graph ≡ old list result; condition TRUE/FALSE; rejoin; guard | new `tests/unit/test_executor_graph.py`, BE-FAST |
| 4.3 | Graph validator per `03` §4 returning full violation list (pure function in `modules/strategies/graph_validation.py`) | new file | one test per violation class (10 cases) | new `tests/unit/test_graph_validation.py` |
| 4.4 | Models `StrategyNode`/`StrategyEdge` per `07` M2 DDL; delete `StrategyStep` model; update `app/models.py` | `modules/strategies/models.py` | mypy clean (call sites updated in 4.5–4.7 same commit train) | `uv run mypy app` |
| 4.5 | Schemas + service: `GraphRequest/NodeRequest/EdgeRequest`, accept `graph` XOR legacy `steps` (convert steps→linear graph server-side incl. START/END, positions x=240·i); run validator; version responses include `graph` and derived `steps` when linear; step-validation logic (required_fields/calculations/reference existence) moves to node validation | `modules/strategies/{schemas,service}.py` | strategy API tests (adapted) + new graph tests pass | `tests/integration/test_strategy_graph.py` |
| 4.6 | `plan_builder.build_plan` resolves nodes+edges into engine plan (reference resolution helpers reused verbatim) | `modules/strategies/plan_builder.py` | decision + simulation integration tests pass unchanged | BE-FAST on decisions/simulation tests |
| 4.7 | Trace additions: `node_key` per step entry, CONDITION entries (`condition_result`, `taken_edge`), `strategy.execution="GRAPH"`, top-level `outputs` snapshot (masked) | `modules/decisions/{service,schemas}.py`, simulations trace | trace assertions in graph E2E test pass | BE-FAST |
| 4.8 | Alembic **M2**: create tables, convert ALL existing versions' steps→linear graphs (pure SQL/core, per `07` M2 pseudocode), drop `strategy_steps`; downgrade = linear-only reconstruction | new migration | up→down→up on seeded dev DB succeeds | alembic commands |
| 4.9 | Seeds write graph; adapt existing strategy tests (`VALID_STEPS` may stay — legacy path converts); run **golden tests** — must pass byte-identical | `app/seed.py`, tests | golden green + full suite green | BE-FULL |
| 4.10 | CONDITION end-to-end: seed/or-create branching strategy in a test, run two payloads covering both edges, assert paths in trace. Status + commit `feat(strategy): DAG decision-flow execution with graph migration` | tests | **BE-FULL green** | BE-FULL |

## P3.5 — Visual flow canvas

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 5.1 | `npm install @xyflow/svelte@<latest-stable>` (pin exact in package.json; lockfile committed; ADR-013 recorded) | frontend deps, ADR | build passes with lib imported in a stub | `npm run build` |
| 5.2 | `lib/flow/`: node components per type (CONDITION diamond, two labeled source handles), edge styling, `graphToFlow`/`flowToGraph` serializers, simple layered auto-layout | new `frontend/src/lib/flow/*` | serializer Vitest round-trip (API graph ⇄ canvas state) | `npm run test:unit -- --run` |
| 5.3 | Rewrite `/strategies/[id]`: canvas (editable when DRAFT, read-only otherwise), palette, config drawer per node type (reference selects from existing endpoints/meta; CONDITION uses ConditionBuilder), save via graph API, server validation errors highlighted, lifecycle bar unchanged (submit still attaches simulation) | `routes/strategies/[id]/+page.svelte` | build the `08` §3 example graph via UI against local stack; activate as manager | manual + Playwright (8.2) |
| 5.4 | Trace screen: `node_key`/branch display + "view flow" read-only link. FE-FULL + status + commit `feat(ui): visual decision-flow canvas` | trace page | **FE-FULL green** | FE-FULL |

## P3.6 — Expression language + SQL preview

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 6.1 | `engine/expression.py`: tokenizer + recursive-descent parser → JSON-serializable AST dataclasses; limits (len 2000, depth 20, nodes 200, branches 20, list 50); interpreter `(ast, features) -> value` with NULL semantics per `05` §4.7; **zero** use of `eval/exec/ast module` | new file | §7 examples + NULL/type-error/limit unit tests | new `tests/unit/test_expression.py` |
| 6.2 | Security fuzz suite: every entry in `10` §2 fuzz list must fail to parse or resolve | same test file | all fuzz cases 422/parse-error | BE-FAST |
| 6.3 | `engine/preview.py`: `dsl_to_sql_preview(defn) -> str` for branch rules and expression rules; include in rule GET responses as `sql_preview` | new file + rules router | parity fixtures for 5 canonical rules | new unit test |
| 6.4 | EXPRESSION authoring: rules API accepts `{expression, output_target}` form (third XOR branch), gated by `rule.author_expression`; stores `expression_text` + compiled AST in `condition_json`; execution path in executor evaluates AST → SET_OUTPUT to target; `POST /v1/expressions/validate` endpoint | rules module + new `api/v1/expressions.py` (wired) | admin-200/analyst-403 + execution-in-decision integration tests | new `tests/integration/test_expression_rules.py` |
| 6.5 | Frontend: expression editor (debounced validate, insert-feature, output picker), SQL-preview tab on all rule pages with the "never executed" banner. FE-FULL + BE-FULL + status + commit `feat(rules): safe expression language with SQL-style preview (admin-gated)` | rule pages | both suites green | BE-FULL + FE-FULL |

## P3.7 — Decision-table grid editor

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 7.1 | `/decision-tables` list + `/decision-tables/[id]` grid per `09` §3 (typed cells, row ops, hit-policy, inline overlap badges from version response, lifecycle buttons); nav entry | new routes + layout + types | author the `04` §7.2 combining table via grid against local stack | manual |
| 7.2 | FE-FULL + status + commit `feat(ui): decision table grid editor` | — | **FE-FULL green** | FE-FULL |

## P3.8 — Hardening, E2E, docs sync

| # | Task | Files | Done when | Verify |
|---|---|---|---|---|
| 8.1 | `docker compose up -d --build`; smoke: health, login, one decision through a graph strategy | — | all 200s | curl |
| 8.2 | Playwright: 3 new specs per `10` §4 (authoring journey; grid+canvas+governance+trace; expression permissions); keep old 4 green | `frontend/e2e/*` | `npx playwright test` all green | playwright |
| 8.3 | Docs sync: phase-3 addenda in `docs/06/07/09/10`, ADR-013/014 finalized, `docs/IMPLEMENTATION_STATUS.md`, `docs/FINAL_IMPLEMENTATION_REPORT.md` Phase-3 section, pack `IMPLEMENTATION_STATUS.md` complete; run `10` §7 exit checklist | docs | every checklist box checked | manual checklist |
| 8.4 | Commit `docs: synchronize Phase 3 documentation and final report` | — | clean `git status` | git |

# Phase 3 Execution Plan

Discipline (unchanged from AGENTS.md / docs/17): one coherent local commit per sub-phase; all relevant gates green before commit; `docs/phase3/IMPLEMENTATION_STATUS.md` updated in the same commit; material decisions → ADR in `docs/IMPLEMENTATION_DECISIONS.md`; never push/deploy; synthetic data only.

Environment quickstart for the implementing agent:
```bash
docker compose up -d postgres                      # host port 5455
cd backend  && uv sync && uv run pytest -q         # 114 green before you start
cd frontend && npm install && npm run check        # 0 errors before you start
# dev DB migrate+seed when needed:
OSCAR_DATABASE_URL=postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar uv run alembic upgrade head
OSCAR_DATABASE_URL=... uv run python -m app.seed
```

---

## P3.1 — Rule Model v2 (engine)
**Files**: `backend/app/engine/dsl.py` (BranchedRuleDefinition, actions, normalization), `engine/executor.py` (branch loop around existing `_apply_action`; `actions_applied`), `modules/rules/{models,schemas,service,router}.py` (rule_kind, v2 bodies, typed-operator validation, SET_OUTPUT catalog checks — writable check stubs until P3.2 lands in same commit train), Alembic **M1** (`07_data_model.md`), seeds untouched.
**Accept**: `04_rule_model_v2.md` §7 patterns pass; legacy suite untouched; typed-operator matrix enforced; test endpoint returns matched_branch/actions/outputs_after.
**Commit**: `feat(rules): rule model v2 with CASE WHEN branches and typed outputs`

## P3.2 — Catalogs & metadata
**Files**: `modules/features/*` (writable, RULE_OUTPUT), NEW `modules/rules/categories_router.py` (model class `RuleCategory` lives in `modules/rules/models.py`), `api/v1/meta.py`, `modules/rules/usage` endpoint (in `router.py`), `auth/permissions.py` (+`rule.author_expression` seed), `app/seed.py` (outputs.*). **Migrations: none in this sub-phase** — the single M1 revision created in P3.1 already contains every P3.2 schema change (features.writable, rule_categories); P3.2 is API/seed/meta work only.
**Accept**: writable enforcement live (SET_OUTPUT to PAYLOAD/non-writable ⇒ 422); meta keys per `06` §3; usage endpoint correct incl. graph-era stub (rule sets + step/node references); category CRUD audited.
**Commit**: `feat(catalog): output catalog, rule categories, typed metadata`

## P3.3 — Rule authoring UX overhaul
**Files**: `frontend/src/lib/components/ConditionBuilder.svelte` (v2 nested/typed/searchable), NEW `BranchEditor.svelte`, `ActionListEditor.svelte`, NEW `frontend/src/lib/rule-format.ts` (JSON↔builder + human preview + client sql-preview), rewrite `routes/rules/new/+page.svelte` & `routes/rules/[id]/+page.svelte` (builder-first, tabs, generated test form, usage panel), `lib/api/types.ts`.
**Accept**: PRD §6 items 2 (minus expression) authorable with zero JSON; round-trip Vitest green; existing rules render read-only correctly; unsupported shapes fall back gracefully.
**Commit**: `feat(ui): builder-first rule authoring with branches and typed inputs`

## P3.4 — DAG execution engine  ⚠ highest-risk sub-phase
**Order inside the phase**: (1) write golden tests against current behavior and commit them green **first**; (2) engine `ExecutablePlan` graph + traversal + validator; (3) models/schemas/service/plan_builder; (4) Alembic **M2** with data conversion + drop `strategy_steps`; (5) legacy `steps[]` request conversion + derived steps in responses; (6) seeds → graph; (7) adapt existing strategy tests; (8) run golden tests.
**Files**: `engine/executor.py`, `modules/strategies/{models,schemas,service,plan_builder}.py`, `app/models.py`, `app/seed.py`, M2, `modules/decisions/service.py` + `simulations/service.py` (trace additions only — plan interface stays `build_plan(session, version)`), trace schema in `modules/decisions/schemas.py`.
**Accept**: `10_test_plan.md` §1 graph rows + §5 golden green; upgrade→downgrade→upgrade on seeded dev DB; simulation of CONDITION draft works; all lifecycle/governance tests green unchanged.
**Commit**: `feat(strategy): DAG decision-flow execution with graph migration`

## P3.5 — Visual flow canvas
**Files**: `frontend/package.json` (+`@xyflow/svelte` pinned — record ADR-013), NEW `frontend/src/lib/flow/` (node components, serializer, layout), rewrite `routes/strategies/[id]/+page.svelte` (canvas editor + read-only mode + lifecycle bar), trace screen "view flow" link.
**Accept**: FR-CANVAS-1..4; build/check green; Playwright canvas spec (build the `08_api_contract.md` §3 example graph via UI, save, submit with simulation, activate as manager).
**Commit**: `feat(ui): visual decision-flow canvas`

## P3.6 — Expression language + SQL preview
**Files**: NEW `backend/app/engine/expression.py` (tokenizer/parser/interpreter/limits) + NEW `engine/preview.py` (dsl→sql-style text), `modules/rules/*` (EXPRESSION authoring form, expression_text, validate endpoint in NEW `api/v1/expressions.py` or rules router), permissions seed live from P3.2, frontend expression editor + SQL preview tab everywhere (`rule-format.ts` + detail pages).
**Accept**: `10_test_plan.md` §2 (incl. full fuzz list) green; §7 examples round-trip; analyst 403 / admin 200; previews shown for builder rules too.
**Commit**: `feat(rules): safe expression language with SQL-style preview (admin-gated)`

## P3.7 — Decision-table grid editor
**Files**: NEW `frontend/src/routes/decision-tables/{+page.svelte,[id]/+page.svelte}` (list + grid per `09` §3), nav entry in `routes/+layout.svelte`, `lib/api/types.ts`; backend untouched (existing endpoints).
**Accept**: table authored via grid combining `outputs.*` columns; overlap warnings inline; lifecycle buttons work; Playwright grid spec green.
**Commit**: `feat(ui): decision table grid editor`

## P3.8 — Hardening, E2E, docs sync
**Work**: rebuild compose stack; full Playwright suite incl. PRD §6 journey; latency smoke; PII spot-check on `outputs` in traces/logs; update `docs/05_mvp_scope.md` (point Phase 3 → this pack; already stubbed), `docs/06/07/09/10` phase-3 addenda, `docs/IMPLEMENTATION_STATUS.md`, `docs/FINAL_IMPLEMENTATION_REPORT.md` (Phase 3 section), ADR-012/013/014 finalized, this pack's `IMPLEMENTATION_STATUS.md` complete.
**Commit**: `docs: synchronize Phase 3 documentation and final report` (plus `test(e2e): ...` if E2E lands separately)

---

## Risk register

| # | Risk | Mitigation |
|---|---|---|
| 1 | M2 data conversion corrupts existing strategies | Golden tests written & committed BEFORE M2; conversion covers all statuses; up→down→up rehearsal on seeded DB; conversion is pure-SQL (no app imports) |
| 2 | Expression sandbox escape | Hand-written parser (no `ast`/eval); whitelist grammar; fuzz list is a hard gate; permission-gated authoring |
| 3 | Canvas library churn/bloat | Pin exact `@xyflow/svelte` version (lockfile); wrap in `lib/flow/` adapter so the lib is swappable; route-level code-split |
| 4 | Trace/UI back-compat breaks for old decisions | Additive-only trace fields; UI renders entries with and without `node_key`; integration test loads a pre-P3.4 trace fixture |
| 5 | Scope creep into stretch items | `02_scope.md` §3 list is explicitly out of the definition of done; status doc tracks only P3.1–P3.8 |
| 6 | Non-linear graphs authored before governance review | Unchanged gates already cover it: draft → mandatory simulation attach → maker-checker approval → activation re-validation |

## Definition of done (phase)

All P3.1–P3.8 committed locally; `10_test_plan.md` §7 checklist fully checked; nothing pushed or deployed; `IMPLEMENTATION_STATUS.md` (pack) shows every sub-phase Complete with evidence.

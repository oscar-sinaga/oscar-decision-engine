# Phase 3 Test Plan

Baseline to preserve: 114 backend pytest, 12 Vitest, 4 Playwright — all green before and after every sub-phase. New tests land **with** their sub-phase (same commit). Postgres for tests: existing session fixture (recreates `oscar_test`, runs `alembic upgrade head`) — every new migration is therefore exercised from clean DB on every run.

## 1. Engine unit tests (`backend/tests/unit/`)

| Area | Cases |
|---|---|
| Rule v2 branches | first-match order; ELSE applied; no-match+no-default ⇒ PASSED; ≤20 branches enforced; legacy shape normalization equals v2 single-branch |
| Multi-action | ordered application; SET_OUTPUT then ADD_REASON_CODE in one branch; STOP_EXECUTION mid-list stops strategy |
| SET_OUTPUT | value visible to later rule/table/condition in same run; overwrite by later rule wins; type mismatch rejected at validation |
| Typed operators | full matrix (`04_rule_model_v2.md` §5): each disallowed (data_type, operator) pair ⇒ error naming the field |
| Graph executor | linear graph ≡ old ordered result (same fixtures); CONDITION true/false routing; rejoin path; terminal-without-END; STOP inside branch; on_error FAIL/MANUAL_REVIEW/CONTINUE on a branch node; visit-guard triggers on hand-built cyclic plan (bypassing validator) |
| Graph validator | each violation class from `03_architecture.md` §4 produces its own 422 detail: no START, two STARTs, cycle, orphan, CONDITION with 1/3 edges or wrong labels, dup edge, unknown node ref, self-loop, >100 nodes |
| Determinism | same plan+payload twice ⇒ identical result & step_results (excluding durations) |

## 2. Expression tests (`backend/tests/unit/test_expression*.py`)

- Round-trip/eval for every example in `05_expression_language.md` §7.
- NULL semantics: missing feature, COALESCE, IS NULL, NULL arithmetic ⇒ NULL, NULL in WHEN ⇒ branch skipped.
- Type errors: string+number, divide by zero, non-boolean WHEN ⇒ safe engine error, on_error path, no payload values in message.
- Limits: 2001-char input, depth-21 parens bomb, 201-node expr, 21 CASE branches, 51-item IN list ⇒ 422 each.
- **Security fuzz (must all fail to parse or resolve, never execute):**
  `__import__('os')`, `().__class__`, `open('/etc/passwd')`, `exec('x')`, `eval('1')`, `lambda: 1`, `[x for x in y]`, `f(1)` for any non-whitelisted `f`, backtick/semicolon/`--` SQL fragments, `'a' OR 1=1`-style injections (parses as boolean expr but identifiers unknown ⇒ 422), unicode homoglyph identifiers, nested quotes escapes, `\x00` bytes.
- Determinism: interpreter is pure — same AST+features twice ⇒ identical value; AST JSON stored equals re-parsed text AST.
- Permission: analyst creating EXPRESSION rule / SET_OUTPUT.expression / calling validate ⇒ 403; admin ⇒ 200.

## 3. API integration tests (`backend/tests/integration/`)

- Rules: create v2 via branches; create legacy (unchanged assertions); exactly-one-authoring-form 422; SET_OUTPUT to non-writable/inactive/PAYLOAD feature ⇒ 422; test endpoint returns matched_branch/actions/outputs_after; usage endpoint (rule in set + set in graph node + active flag); category catalog CRUD + rule create with unknown/inactive category ⇒ 422; sql_preview present.
- Strategies: create via `graph`; create via legacy `steps` and read back linear graph + derived steps; every validator violation via API; lifecycle unchanged (submit+simulation attach, maker-checker, activate re-validation, rollback) against a graph version; simulation of a draft **graph with CONDITION** (both paths covered by two payloads).
- Decisions: end-to-end through a CONDITION strategy — trace has node_keys, taken_edge, matched_branch, outputs snapshot; idempotency unchanged; PII masking on outputs snapshot (deny-list keys still redacted).
- Meta: operators_by_type, writable_outputs, node_types, rule_categories present.

## 4. Frontend tests

Vitest: `rule-format` JSON↔builder round-trip (legacy, v2 nested, branch+else, unsupported-shape fallback flag); sql-preview renderer matches backend for 5 canonical rules (fixture parity); graph serializer (canvas state → API body; TRUE/FALSE handles). Playwright (compose stack): PRD §6 journey split into 3 specs — (a) catalog+rule authoring+test form, (b) grid table + canvas + governance + decide + trace, (c) expression admin-allowed / analyst-denied. Keep existing 4 specs green.

## 5. Golden reproducibility tests (migration gate — REQUIRED before M2 merges)

`backend/tests/integration/test_golden_reproducibility.py`:
1. Golden payload set = the 4 canonical synthetic payloads (approve-with-condition, blacklist reject, borderline-DTI manual review, fraud mismatch) — already used across the suite.
2. **Before writing M2**: run them against seeded `LEASEBACK_MOTOR` and hard-code expected `(decision, reason_codes, risk_grade, approved_limit)` into the test.
3. After M2 (graph execution): same payloads ⇒ identical expectations; plus trace `strategy.execution == "GRAPH"` and step order matches old step order.
4. Retired-version reproducibility: activate v2 graph, roll back to v1, both versions' plans still build and produce their recorded outcomes.

## 6. Non-functional gates

- mypy `--strict` clean (new engine modules fully typed; no `Any` leaks in expression AST types).
- ruff format+check clean.
- Latency smoke: decision P95 on compose stack for golden payloads < 500ms (existing informal budget) with graph executor.
- `alembic upgrade head` from clean DB (fixture) + `upgrade→downgrade→upgrade` on seeded dev DB for M1/M2 (documented command in execution plan).
- Frontend: svelte-check strict 0 errors; production build. Canvas lib is imported only from the strategy-detail route modules (SvelteKit code-splits per route automatically — no manual dynamic import required).

## 7. Exit checklist (P3.8)

- [ ] All suites green on rebuilt compose stack — backend/Vitest gates are green; Docker and browser runtime are workstation-pending.
- [x] Golden reproducibility green.
- [x] Expression fuzz list green.
- [ ] PRD §6 journey recorded in Playwright and passing — all 3 new specs are recorded and discovered; browser execution is workstation-pending.
- [ ] No JSON required anywhere in the §6 journey — implemented by the primary UI surfaces; final manual spot-check is workstation-pending.
- [x] Docs sync (05/06/07/09/10 + Phase 3 statuses + ADRs) completed in the final Phase 3 commit.

The unchecked items are environmental acceptance gates, not unfinished implementation. See `LOCAL_ENVIRONMENT_VALIDATION.md`.

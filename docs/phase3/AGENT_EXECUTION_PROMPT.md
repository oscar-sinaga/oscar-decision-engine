# Autonomous Implementation Mission — OSCAR Phase 3: Generic Rule Authoring & Visual Decision Flow

You are the autonomous Lead Architect, Backend Engineer, Frontend Engineer, Database Engineer, QA Engineer, and Technical Writer executing **Phase 3** of OSCAR Decision Engine.

Do not return only a plan. Inspect the repository, then execute sub-phase by sub-phase until the Phase 3 Definition of Done is satisfied or a genuine hard blocker remains.

## Mandatory context (read before coding)

1. `docs/phase3/00_README.md` … `11_execution_plan.md` — **the authoritative Phase 3 specification.**
2. `CLAUDE.md`, `AGENTS.md` — engineering discipline (git, gates, audit, PII, logging). Two amendments apply (ADR-012): the visual flow canvas is in scope, and "free SQL" is implemented as the safe expression language + display-only SQL preview. Raw SQL/eval/exec remain forbidden.
3. Existing code you will extend — read these before touching them:
   `backend/app/engine/{dsl,evaluator,executor,decision_table,scorecard,features}.py`,
   `backend/app/modules/strategies/{models,schemas,service,plan_builder}.py`,
   `backend/app/modules/rules/{models,schemas,service,router}.py`,
   `backend/app/modules/features/`, `backend/app/api/v1/meta.py`, `backend/app/seed.py`,
   `frontend/src/lib/components/ConditionBuilder.svelte`, `frontend/src/routes/rules/**`, `frontend/src/routes/strategies/[id]/+page.svelte`, `frontend/src/lib/api/types.ts`.

## Verified facts (2026-07-11 — trust these; do not re-derive)

- Branch `feature/oscar-mvp`; MVP + Phase 2 complete; 20 local commits; working tree clean.
- Gates green at baseline: backend ruff + mypy `--strict` + **114 pytest**; frontend prettier/eslint/svelte-check strict/**12 Vitest**/build; **4 Playwright** E2E; compose stack (postgres :5455, backend :8000, frontend :3000) boots with migrations+seed.
- Alembic head `1864d7efc83f` (5 revisions). Test DB `oscar_test` is dropped/recreated+migrated by the pytest session fixture.
- Engine DSL already supports nested `all/any/not`; executor already applies `SET_ATTRIBUTE` into `context.features` (`executor.py` ~line 252) — Phase 3 formalizes, it does not invent.
- `plan_builder.build_plan(session, strategy_version)` is the single entry shared by production decisions and simulation — keep that property.
- Demo users (password `OscarDemo123!`): admin, riskanalyst, riskmanager, underwriter, compliance, datascientist, engineer, auditor, los-client.
- Windows host; backend uses `uv` (Python 3.13); frontend npm; never bind-assume port 5432 (dev/test Postgres is host port **5455**).

## Execution sequence (each = one conventional local commit; details in `11_execution_plan.md`)

1. **P3.1** Rule Model v2 — CASE WHEN branches + ELSE, multi-action, SET_OUTPUT, typed-operator matrix, `rule_kind`, migration M1, full legacy compatibility.
2. **P3.2** Catalogs & metadata — `features.writable` output catalog + seeds, `rule_categories`, meta additions, `GET /v1/rules/{id}/usage`, permission `rule.author_expression` seeded.
3. **P3.3** Rule authoring UX — nested/typed/searchable builder, branch+ELSE+action editors, human-readable preview, builder-first detail page, generated test form, usage panel.
4. **P3.4** DAG execution — graph model/validator/executor/trace-path, Alembic M2 with data conversion (drop `strategy_steps`), legacy `steps[]` accepted, seeds as graphs. **Write the golden reproducibility tests against CURRENT behavior and get them green BEFORE starting M2.**
5. **P3.5** Visual flow canvas — `@xyflow/svelte` (pin version; ADR-013), palette/config-drawer/validation surfacing, draft edit + read-only active.
6. **P3.6** Expression language — hand-written tokenizer/parser/interpreter (`engine/expression.py`), limits + fuzz suite, `POST /v1/expressions/validate`, SQL-style preview for all rules (`engine/preview.py`), admin gating.
7. **P3.7** Decision-table grid editor (frontend only).
8. **P3.8** Hardening + E2E (PRD §6 journey) + docs sync + ADRs + final report.

Do not wait for approval between sub-phases. Update `docs/phase3/IMPLEMENTATION_STATUS.md` before every commit.

## Non-negotiable controls

- No `eval`, no `exec`, no SQL built from user text, no execution of analyst-supplied SQL — the expression language is parsed by a hand-written whitelist parser and interpreted in-process.
- Determinism: same payload + same version ⇒ same decision and same trace path. Graphs must be validated acyclic; runtime visit-guard stays as defense.
- Every production decision keeps an immutable trace; new trace fields are additive; old traces must still render.
- Governance unchanged: versioning, active-version immutability, maker-checker (approver ≠ maker), mandatory simulation attachment before strategy activation, rollback, append-only audit events for every state change.
- Backward compatibility contract in `02_scope.md` §5 (legacy rule JSON, legacy steps API, golden decisions) is part of the definition of done.
- PII masking everywhere it exists today, including the new trace `outputs` snapshot; no payload values in error messages.
- Pin new frontend deps exactly (`@xyflow/svelte`); record dependency decisions in `docs/IMPLEMENTATION_DECISIONS.md` per `docs/16`.
- Local commits only. Never push, deploy, force-push, or rewrite existing commits. Synthetic data only.

## Quality gates per sub-phase (all must pass before its commit)

```bash
cd backend  && uv run ruff format --check . && uv run ruff check . && uv run mypy app tests && uv run pytest -q
cd frontend && npm run lint && npm run check && npm run test:unit -- --run && npm run build
# migration sub-phases additionally (seeded dev DB):
OSCAR_DATABASE_URL=postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar uv run alembic upgrade head
#   + upgrade → downgrade -1 → upgrade head rehearsal for M1/M2
# P3.5/P3.7/P3.8 additionally: docker compose up -d --build && npx playwright test
```

## Hard blockers (stop only if)

Spec conflict that changes credit-decision meaning; destructive migration risk to non-test data that golden tests cannot bound; required credential/production access; repo/environment corruption; a security requirement needing a human decision. Routine ambiguity → resolve conservatively + record in `docs/IMPLEMENTATION_DECISIONS.md`. Anything else → `docs/BLOCKERS.md` only if truly blocked.

## Completion requirements

Phase 3 is complete only when: P3.1–P3.8 are committed; `docs/phase3/10_test_plan.md` §7 exit checklist is fully satisfied on a rebuilt compose stack (old suites + new suites + golden reproducibility + expression fuzz + PRD §6 Playwright journey); docs are synchronized (`docs/05/06/07/09/10` + this pack + ADR-012/013/014 + final report); `docs/phase3/IMPLEMENTATION_STATUS.md` shows every sub-phase Complete with evidence; nothing is pushed or deployed.

Begin with P3.1 immediately.

# OSCAR Phase 3 — Generic Rule Authoring & Visual Decision Flow

**Specification pack v1.0 — 2026-07-11 — approved by product owner (oscar.m.sinaga@smmf.co.id)**

This folder is the **authoritative implementation specification for Phase 3**. It replaces the old Phase 3 roadmap in `docs/05_mvp_scope.md` (fraud monitoring, champion/challenger, model/drift monitoring, portfolio/vintage, collection integration — all removed by product-owner decision; see ADR-012 in `docs/IMPLEMENTATION_DECISIONS.md`).

## Mission in one paragraph

Evolve OSCAR from a *credit policy outcome rule engine* (rule → decision + reason code) into a *generic enterprise decision rule engine* in the spirit of IDX iDecision: rules can produce **values and classifications** (multi-branch CASE WHEN → outputs) that later steps combine into final decisions; strategies become **visual decision-flow graphs (DAG)** with conditional branching designed on a node canvas; power users get a **safe expression language** (with SQL-style preview) instead of raw SQL; and every authoring surface (rule builder, flow canvas, decision-table grid) is usable by a **non-technical Risk Policy Analyst** without touching JSON.

## Authority and precedence

1. This pack (`docs/phase3/*`) governs Phase 3 scope and design.
2. `AGENTS.md` and `CLAUDE.md` still govern engineering discipline (git, quality gates, audit, PII, logging) **with two explicit amendments** recorded in ADR-012:
   - A visual drag-and-drop flow canvas is now **in scope** (was out of scope for MVP).
   - "Free SQL" is implemented as a **safe expression language with SQL-style *preview*** (admin-gated). Raw SQL execution remains forbidden — this *complies* with AGENTS.md ("use safe structured expressions; never use eval, exec, or unrestricted SQL").
3. Older `docs/01..18` remain authoritative for everything Phase 3 does not change; where this pack contradicts them, this pack wins and the older doc must be updated in the same commit as the code change (`docs/17` sync rule).

## Reading order

| # | File | What it defines |
|---|------|-----------------|
| 1 | `01_prd.md` | Problem, goals, personas, functional requirements, acceptance criteria |
| 2 | `02_scope.md` | In/out of scope, sub-phase breakdown P3.1–P3.8, stretch backlog |
| 3 | `03_architecture.md` | DAG execution engine design, back-compat and migration strategy |
| 4 | `04_rule_model_v2.md` | Rule DSL v2: CASE WHEN branches, multi-action, typed operators |
| 5 | `05_expression_language.md` | Safe expression grammar, security requirements, SQL-style preview |
| 6 | `06_catalogs_and_metadata.md` | Output catalog, category catalog, meta/usage endpoints |
| 7 | `07_data_model.md` | New/changed tables, Alembic migrations, data conversion |
| 8 | `08_api_contract.md` | Endpoint additions/changes with examples |
| 9 | `09_screen_spec.md` | Rule builder v2, flow canvas, decision-table grid, expression editor |
| 10 | `10_test_plan.md` | Test matrix incl. determinism, security fuzzing, migration golden tests |
| 11 | `11_execution_plan.md` | Ordered sub-phases, per-phase acceptance criteria, commit plan, risks |
| 12 | `12_penjelasan_fitur_id.md` | Non-normative Indonesian explainer: analogies and case studies for every feature |
| 13 | `13_task_breakdown.md` | **Atomic task checklist** — ordered task cards with file lists, done-conditions, verify commands |
| 14 | `14_code_reference.md` | **Verified ground truth** about the existing codebase: signatures, fixtures, conventions, seeds |
| 15 | `AGENT_EXECUTION_PROMPT.md` | Self-contained autonomous prompt for any coding agent |
| 16 | `IMPLEMENTATION_STATUS.md` | Live progress tracker (update before every phase commit) |

## How to execute this pack with an AI coding agent

Open the repository, ensure Docker is running, then provide the agent the contents of `docs/phase3/AGENT_EXECUTION_PROMPT.md`. The prompt is self-contained: it lists verified facts about the current codebase (so the agent does not re-discover them), mandatory operating rules, the exact execution sequence, quality gates, and completion criteria. Any capable coding agent (Claude, GPT, etc.) should be able to execute it; sub-phases are independent commits so different agents can execute different sub-phases as long as they run in the specified order and keep `IMPLEMENTATION_STATUS.md` current.

The pack is deliberately hardened for **smaller/cheaper executor models**: `13_task_breakdown.md` decomposes every sub-phase into ordered atomic tasks with per-task verify commands, `14_code_reference.md` supplies verified signatures/fixtures/conventions so the executor never has to guess internal APIs, every design choice in files 01–11 is pinned (no "implementer's choice" remains), and the prompt's operating rules define a stuck-resolution priority order so ambiguity never stalls or derails a run.

## Baseline the pack assumes (verified 2026-07-11)

- Branch `feature/oscar-mvp`, 20 local commits, MVP + Phase 2 complete.
- Backend: FastAPI 0.139.0, Python 3.13 (uv), SQLAlchemy 2 async, Alembic (5 migrations, head `1864d7efc83f`), 114 pytest tests green, mypy `--strict` clean, ruff clean.
- Frontend: SvelteKit 2 / Svelte 5 runes, TS strict, Tailwind 4; Vitest 12 tests; Playwright 4 E2E; production build green.
- Runtime: `docker compose up -d` — postgres on host port **5455** (dev/test), backend :8000, workbench :3000. Test DB `oscar_test` is recreated by the pytest session fixture.
- Demo users (password `OscarDemo123!`): `admin`, `riskanalyst`, `riskmanager`, `underwriter`, `compliance`, `datascientist`, `engineer`, `auditor`, `los-client`.

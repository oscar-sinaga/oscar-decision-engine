# Phase 3 Implementation Status

> Maintained by the implementing agent. Update **before every sub-phase commit** with status, evidence (test counts, migration IDs), and any recorded decisions. This file tracks Phase 3 only; the repository-wide tracker remains `docs/IMPLEMENTATION_STATUS.md`.

## Overall

- Status: **In progress**
- Baseline: MVP + Phase 2 complete — 114 backend tests, 12 Vitest, 4 Playwright, Alembic head `1864d7efc83f`
- Current sub-phase: P3.5 — Visual flow canvas
- Latest Phase 3 commit: `feat(ui): builder-first rule authoring with branches and typed inputs`

## Sub-phase tracker

| Sub-phase | Title | Status | Evidence (fill on completion) |
|---|---|---|---|
| P3.1 | Rule Model v2 (engine) | **Complete** | tests: 135 passed; ruff + mypy strict clean · migration: `8f3c2a1b7d04`, up/down/up green · commit: `feat(rules): rule model v2 with CASE WHEN branches and typed outputs` |
| P3.2 | Catalogs & metadata | **Complete** | tests: 141 backend passed; ruff + mypy clean; frontend lint/check, 12 Vitest, build green · commit: `feat(catalog): output catalog, rule categories, typed metadata` |
| P3.3 | Rule authoring UX overhaul | **Complete** | frontend lint + svelte-check 0/0 + 15 Vitest + production build green · commit: `feat(ui): builder-first rule authoring with branches and typed inputs` |
| P3.4 | DAG execution engine | **Complete** | golden: 4 canonical cases green · 63 unit + 102 integration tests green in segmented runs · migration `f4b7c9d2e601` up/down/up green · ruff + mypy clean · commit: `feat(strategy): DAG decision-flow execution with graph migration` |
| P3.5 | Visual flow canvas | Pending | playwright: — · commit: — |
| P3.6 | Expression language + SQL preview | Pending | fuzz: — · commit: — |
| P3.7 | Decision-table grid editor | Pending | playwright: — · commit: — |
| P3.8 | Hardening, E2E, docs sync | Pending | exit checklist: — · commit: — |

## Decisions recorded during execution

- Baseline drift: the clean `feature/oscar-mvp` branch is five commits ahead of its remote,
  rather than the prompt's older local-commit count; existing history is preserved.
- M1 makes `rule_versions.action_json` nullable because the authoritative v2 storage
  contract requires `NULL` for branched rules; retaining its legacy NOT NULL constraint
  would make task 1.4 impossible. Legacy rows and semantics are unchanged.
- Typed comparison value validation moves from the framework-free DSL shape parser to
  catalog-aware rule validation, as required by `04_rule_model_v2.md` §5; this enables
  DATE comparisons while preserving numeric/string/boolean type enforcement at the API.
- Task 1.6 also updates `strategies/plan_builder.py` (not named in that atomic card)
  because it is the mandatory shared production/simulation bridge and otherwise active
  v2 rules would validate through the API but fail when executed.
- P3.4 adds `NodeType` to `shared/domain/enums.py` although task 4.2 names only
  `engine/executor.py`; graph persistence, API metadata, validation, and execution must
  share one typed enum to prevent drift between layers.

## Known limitations / follow-ups discovered

- Docker/Compose is unavailable in the ChatGPT container. Compose rebuild and Playwright verification are recorded in `docs/phase3/LOCAL_ENVIRONMENT_VALIDATION.md` for execution on the user's workstation.
- A monolithic `pytest -q` invocation is terminated by the container timeout after roughly 69 tests; every test file was therefore run in segmented groups (63 unit + 102 integration, all green).

## Blockers

- None.

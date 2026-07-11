# Phase 3 Implementation Status

> Maintained by the implementing agent. Update **before every sub-phase commit** with status, evidence (test counts, migration IDs), and any recorded decisions. This file tracks Phase 3 only; the repository-wide tracker remains `docs/IMPLEMENTATION_STATUS.md`.

## Overall

- Status: **In progress**
- Baseline: MVP + Phase 2 complete — 114 backend tests, 12 Vitest, 4 Playwright, Alembic head `1864d7efc83f`
- Current sub-phase: P3.3 — Rule authoring UX overhaul
- Latest Phase 3 commit: `feat(catalog): output catalog, rule categories, typed metadata`

## Sub-phase tracker

| Sub-phase | Title | Status | Evidence (fill on completion) |
|---|---|---|---|
| P3.1 | Rule Model v2 (engine) | **Complete** | tests: 135 passed; ruff + mypy strict clean · migration: `8f3c2a1b7d04`, up/down/up green · commit: `feat(rules): rule model v2 with CASE WHEN branches and typed outputs` |
| P3.2 | Catalogs & metadata | **Complete** | tests: 141 backend passed; ruff + mypy clean; frontend lint/check, 12 Vitest, build green · commit: `feat(catalog): output catalog, rule categories, typed metadata` |
| P3.3 | Rule authoring UX overhaul | Pending | vitest: — · commit: — |
| P3.4 | DAG execution engine | Pending | golden: — · migration M2: — · commit: — |
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

## Known limitations / follow-ups discovered

- (none yet)

## Blockers

- None.

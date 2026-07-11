# Phase 3 — Local Repository Integration Guide

This guide explains how to bring the completed OSCAR Phase 3 implementation into an older local clone safely, how to migrate the database, and where merge conflicts are most likely.

## 1. Reference state

- Source branch: `feature/oscar-mvp`
- Common ancestor with the previously published branch: `ea1cedb87a14822f6c19b292cadf26ffb2fb185d`
- Phase 3 code commits begin at `58c6efb`.
- The P3.8 completion commit uses the message `docs: synchronize Phase 3 documentation and final report`.
- New Alembic revisions:
  - `8f3c2a1b7d04` — Rule Model v2, writable features, rule categories.
  - `f4b7c9d2e601` — strategy graph storage and conversion from `strategy_steps`.

Use the supplied Git bundle when possible. It retains commit history and gives Git the best chance of performing a three-way merge.

## 2. Before integrating

Do not integrate over an uncommitted working tree.

```powershell
cd C:\path\to\your\old\oscar-decision-engine
git status
git switch -c backup/before-phase3-integration
git add -A
git commit -m "chore: snapshot local work before Phase 3 integration"
```

If the local changes are temporary and should not become a commit:

```powershell
git stash push -u -m "before Phase 3 integration"
```

Also create a PostgreSQL backup before applying either Phase 3 migration. The M2 migration replaces `strategy_steps` with graph tables. Do not use a database downgrade as the primary rollback after users have authored non-linear graphs; restore the backup instead.

## 3. Recommended method — fetch the Git bundle

The final handoff package includes `oscar-phase3-complete.bundle`.

```powershell
cd C:\path\to\your\old\oscar-decision-engine
git fetch C:\path\to\oscar-phase3-complete.bundle feature/oscar-mvp:phase3-complete
git log --oneline --decorate -12 phase3-complete
```

### Case A — your branch has no local commits after the common ancestor

```powershell
git switch feature/oscar-mvp
git merge --ff-only phase3-complete
```

### Case B — your local repository has additional commits

Create a dedicated integration branch and merge instead of forcing the history:

```powershell
git switch feature/oscar-mvp
git switch -c integrate/phase3
git merge --no-ff phase3-complete
```

Resolve conflicts, then run every gate in this guide before merging `integrate/phase3` into your working branch.

## 4. Alternative method — apply the commit series

The handoff also includes `oscar-phase3-commits.mbox`. This applies all commits that are ahead of the old published branch and preserves individual commit messages:

```powershell
git switch -c integrate/phase3
git am --3way C:\path\to\oscar-phase3-commits.mbox
```

On a conflict:

```powershell
git status
# edit and resolve the conflicting files
git add <resolved-files>
git am --continue
```

To cancel the whole operation:

```powershell
git am --abort
```

A plain unified patch is included only as a review/fallback artifact. Prefer the bundle or `git am --3way` because they retain ancestry.

## 5. Implementation commits

The functional Phase 3 sequence is:

```text
58c6efb feat(rules): rule model v2 with CASE WHEN branches and typed outputs
6bef0cb feat(catalog): output catalog, rule categories, typed metadata
4eadf83 feat(ui): builder-first rule authoring with branches and typed inputs
18500d3 feat(strategy): DAG decision-flow execution with graph migration
a5f998d feat(ui): visual decision-flow canvas
8da4863 feat(rules): safe expression language with SQL-style preview (admin-gated)
f757811 feat(ui): decision table grid editor
<final> docs: synchronize Phase 3 documentation and final report
```

The earlier commits in the bundle add the authoritative Phase 3 specification and Indonesian learning documentation. They are safe to keep and are useful to local agents.

## 6. Files most likely to conflict

| Area | Main files | Integration rule |
|---|---|---|
| Alembic | `backend/alembic/versions/8f3c2a1b7d04_*`, `f4b7c9d2e601_*` | Never rename revision IDs or edit previously applied local revisions. Resolve multiple heads with an Alembic merge revision. |
| Rule engine | `engine/dsl.py`, `executor.py`, `expression.py`, `preview.py` | Preserve the no-`eval`, no-`exec`, no-user-SQL controls and golden behavior. |
| Rules API | `modules/rules/{models,schemas,service,router}.py` | Keep legacy rule JSON compatibility and exactly-one-authoring-form validation. |
| Strategy engine | `modules/strategies/*` | Preserve `plan_builder.build_plan` as the shared production/simulation path. |
| Shared metadata | `api/v1/{meta,router}.py`, `shared/domain/enums.py`, `app/seed.py` | Merge new enum values, permissions, routes, and idempotent seeds rather than choosing one side wholesale. |
| Frontend dependencies | `frontend/package.json`, `package-lock.json` | Keep exact `@xyflow/svelte` version `1.6.2`; regenerate with `npm install` only when a real lock conflict requires it. |
| Frontend contracts | `frontend/src/lib/api/types.ts` | Combine local API additions with Phase 3 graph/rule/catalog/table types. |
| Main screens | rule, strategy, decision-table, feature-catalog routes | Preserve local branding/layout changes while retaining the Phase 3 controls and test IDs used by Playwright. |

## 7. Alembic conflict handling

After merging code, inspect the migration graph before upgrading a database:

```powershell
cd backend
uv sync --frozen
uv run alembic history
uv run alembic heads
```

Expected Phase 3 head:

```text
f4b7c9d2e601
```

If your local branch already introduced another migration head, do not change the two Phase 3 revision IDs. Create a merge migration:

```powershell
uv run alembic merge -m "merge local and Phase 3 heads" <local_head> f4b7c9d2e601
uv run alembic heads
```

The result should be one head.

## 8. Install and database migration

```powershell
# Repository root
cd C:\path\to\oscar-decision-engine
docker compose down

docker compose up -d postgres

cd backend
uv sync --frozen
$env:OSCAR_DATABASE_URL="postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar"
uv run alembic current
uv run alembic upgrade head
uv run python -m app.seed
uv run alembic current
```

Then install the frontend exactly from its lock file:

```powershell
cd ..\frontend
npm ci
```

### Migration warning

`f4b7c9d2e601` converts every existing linear strategy version into `strategy_nodes` and `strategy_edges`, then removes `strategy_steps`. Its downgrade can reconstruct only a linear representation. Once branching graphs exist, use a database backup/restore for rollback rather than downgrading M2.

## 9. Required validation after integration

Run the workstation instructions in `docs/phase3/LOCAL_ENVIRONMENT_VALIDATION.md`. At minimum:

```powershell
# Backend
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
$env:OSCAR_DATABASE_URL="postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar_test"
uv run pytest -q

# Frontend
cd ..\frontend
npm run lint
npm run check
npm run test:unit -- --run
npm run build
npx playwright install chromium
$env:OSCAR_API_BASE_URL="http://127.0.0.1:8000"
$env:OSCAR_WEB_BASE_URL="http://127.0.0.1:4173"
npx playwright test
```

Expected browser suite: **7 Playwright tests**.

## 10. Manual acceptance priorities

1. Open a pre-Phase-3 strategy and verify that it renders as an equivalent linear graph.
2. Simulate both TRUE and FALSE paths of a CONDITION node and inspect `node_key`/`taken_edge` in the trace.
3. Verify active strategy versions are read-only.
4. Verify submit/activate still requires exact-version simulation evidence and maker-checker approval.
5. Create a writable `outputs.*` catalog item and use it from a rule, expression, and decision table.
6. Verify an administrator can author expressions while a risk analyst receives HTTP 403.
7. Verify decision trace `outputs` remains PII-masked.

## 11. Safe rollback

Code rollback:

```powershell
git switch backup/before-phase3-integration
```

Database rollback for a real environment should restore the backup taken before migration. Avoid `alembic downgrade` after non-linear strategy graphs or new Phase 3 authoring data have been created.

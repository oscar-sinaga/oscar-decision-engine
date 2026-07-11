# Phase 3 Local Environment Validation Notes

This file records checks that depend on Docker, browser services, or the user's workstation. Code-level and database checks that are available in the implementation environment are executed by the agent; the commands below remain as the final workstation gate.

## Environment used by the implementing agent

- Python/uv backend checks: available.
- PostgreSQL on `localhost:5455`: available.
- Alembic migration rehearsal: available.
- Node/npm frontend checks: available.
- Docker / Docker Compose: **not installed** in the ChatGPT container.
- Browser-backed Playwright against the compose stack: requires the user's workstation.

## Completed in the agent environment

- [x] Backend Ruff format/check.
- [x] Backend mypy strict.
- [x] Backend unit tests, segmented: 63 passed at P3.4.
- [x] Backend integration tests, segmented: 102 passed at P3.4.
- [x] P3.6 backend: Ruff + mypy clean, 104 unit and 106 integration tests passed in segmented runs.
- [x] P3.6 frontend: lint, Svelte check (0 errors / 0 warnings), 24 Vitest, and production build passed.
- [x] P3.4 golden reproducibility: 4 canonical cases passed.
- [x] Migration M2 `f4b7c9d2e601`: upgrade → seed → downgrade -1 → upgrade head passed on PostgreSQL port 5455.

A single monolithic `pytest -q` process is terminated by the execution-container timeout after roughly 69 tests. All test files were run in segmented groups and passed; this is a runner limitation rather than a failing test.

## Run on the user's workstation after pulling/copying the completed repository

```powershell
# Backend full gate
cd backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
uv run pytest -q

# Migration rehearsal against the seeded development database
$env:OSCAR_DATABASE_URL="postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar"
uv run alembic upgrade head
uv run python -m app.seed
uv run alembic downgrade -1
uv run alembic upgrade head

# Frontend gate
cd ..\frontend
npm ci
npm run format
npm run lint
npm run check
npm run test:unit -- --run
npm run build

# Full stack and browser gate
cd ..
docker compose up -d --build
cd frontend
npx playwright test
```

## Manual acceptance checks

- [ ] Open an existing migrated strategy and confirm the canvas renders a linear flow.
- [ ] Create a CONDITION node with TRUE/FALSE branches, save, simulate both paths, and inspect trace node keys.
- [ ] Confirm active strategy versions are read-only.
- [ ] Confirm maker-checker and mandatory simulation attachment still block activation correctly.
- [ ] Confirm decision-table grid overlap warnings appear inline.
- [ ] Confirm an administrator can author an expression rule and a risk analyst receives 403.

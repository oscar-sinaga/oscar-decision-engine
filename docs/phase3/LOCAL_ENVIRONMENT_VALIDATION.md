# Phase 3 Local Environment Validation Notes

This file separates completed implementation evidence from checks that require the user's Docker/browser environment.

## Completed in the implementation environment

- [x] PostgreSQL available on `localhost:5455`; Alembic head `f4b7c9d2e601` and seed completed.
- [x] M2 migration rehearsal: upgrade → seed → downgrade → upgrade.
- [x] Final P3.8 backend rerun: Ruff and mypy clean; 105 unit + 106 integration tests, segmented, all passed.
- [x] Four golden reproducibility cases passed.
- [x] Expression parser limits, NULL/type behavior, and the required security fuzz list passed.
- [x] P3.8 frontend: Prettier/ESLint, Svelte check 0 errors/0 warnings, 27 Vitest, production build.
- [x] Playwright discovers all seven scenarios (four existing plus three Phase 3 specs).
- [x] Local non-Docker smoke: `/health` 200; login 200; seeded graph-backed decision 201 with `APPROVE_WITH_CONDITION` and `LEASEBACK_MOTOR_V1`.

## Not executable in the implementation container

- Docker and Docker Compose are not installed.
- The Playwright-managed Chromium binary is not cached; download from `cdn.playwright.dev` failed with DNS `EAI_AGAIN`.
- System Chromium exists and launches, but this container applies managed `URLBlocklist: ["*"]`; every local page navigation is rejected with `ERR_BLOCKED_BY_ADMINISTRATOR`.
- Consequently, no claim is made that the seven browser tests passed here. Their definitions compile, lint, and are discovered successfully, and the full graph/governance API setup used by the new journey was separately smoke-tested successfully.

## Workstation gate

PowerShell:

```powershell
# 1. Start a clean full stack
cd <repo-root>
docker compose down -v
docker compose up -d --build

# 2. Backend full gate
cd backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
$env:OSCAR_DATABASE_URL="postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar_test"
uv run pytest -q

# 3. Frontend and browser gate
cd ..\frontend
npm ci
npm run lint
npm run check
npm run test:unit -- --run
npm run build
npx playwright install chromium
$env:OSCAR_API_BASE_URL="http://127.0.0.1:8000"
$env:OSCAR_WEB_BASE_URL="http://127.0.0.1:4173"
npx playwright test
```

Expected: 7 Playwright tests pass.

## Manual acceptance spot-check

- [ ] Existing migrated strategy renders as the same linear flow.
- [ ] CONDITION TRUE/FALSE paths both execute and appear in trace.
- [ ] Active strategy versions are read-only.
- [ ] Maker-checker plus exact-version simulation evidence blocks/permits activation correctly.
- [ ] Decision-table overlap warnings appear after save and reopen.
- [ ] Admin can author expressions; analyst receives 403 from the API.
- [ ] Primary PRD journey can be completed without editing JSON.

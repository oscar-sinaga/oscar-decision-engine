# Prompt for the Local AI Agent — Finish Phase 3 Workstation Acceptance

Copy the prompt below into the AI coding agent that runs inside the user's local OSCAR repository.

```text
You are completing workstation acceptance for OSCAR Decision Engine Phase 3. The implementation P3.1–P3.8 is already present. Do not rewrite or redesign completed features.

Read first:
1. docs/phase3/AGENT_EXECUTION_PROMPT.md
2. docs/phase3/IMPLEMENTATION_STATUS.md
3. docs/phase3/LOCAL_ENVIRONMENT_VALIDATION.md
4. docs/phase3/LOCAL_REPOSITORY_INTEGRATION.md
5. docs/phase3/10_test_plan.md, especially section 7
6. docs/IMPLEMENTATION_DECISIONS.md

Mission:
A. Verify that the repository is on the integrated Phase 3 commit and that the working tree is clean. Record branch, HEAD, `git status`, Alembic heads, Python, uv, Node, npm, Docker, and browser versions.
B. Rebuild a clean local stack with PostgreSQL exposed on host port 5455. Never assume port 5432.
C. Run the complete backend gate: Ruff format check, Ruff lint, mypy strict, and full pytest against `oscar_test`.
D. Run the complete frontend gate: lint, Svelte check, all Vitest, production build.
E. Install Playwright Chromium and run all 7 Playwright scenarios against the local backend and preview frontend.
F. Execute the Phase 3 manual acceptance spot-checks in `LOCAL_ENVIRONMENT_VALIDATION.md`.
G. Run a decision latency smoke using the four golden payloads and report count, min, average, P50, P95, and max. The informal P95 target is <500 ms on the compose stack.
H. Spot-check PII masking in decision trace `outputs`, application logs, and error responses. Do not use real customer data.
I. Update documentation only with evidence actually produced on this workstation:
   - docs/phase3/LOCAL_ENVIRONMENT_VALIDATION.md
   - docs/phase3/10_test_plan.md section 7
   - docs/phase3/IMPLEMENTATION_STATUS.md
   - docs/IMPLEMENTATION_STATUS.md
J. If a test fails, diagnose and fix the smallest root cause. Never delete, skip, xfail, loosen, or rewrite a test merely to get green. Preserve backward compatibility and all Phase 3 security controls.
K. Do not push or deploy. Create a local commit only after every gate passes. Suggested commit message: `test(e2e): validate Phase 3 workstation acceptance`.

PowerShell baseline:

cd <repo-root>
docker compose down -v
docker compose up -d --build

cd backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
$env:OSCAR_DATABASE_URL="postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar_test"
uv run pytest -q

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

Before declaring completion, provide:
- exact command results and test counts;
- migration head and migration rehearsal evidence;
- result of all 7 Playwright tests;
- latency statistics;
- PII masking evidence using synthetic data;
- list of files changed by any fixes;
- remaining blockers, if any;
- final `git status --short` and local commit hash.
```

## Environment-only failures that are not application defects

Handle these first before modifying application code:

- Docker Desktop not running or WSL integration disabled.
- Host port 5455 already occupied.
- `oscar_test` held by another process.
- Playwright browser not installed.
- Backend is on port 8000 but `OSCAR_API_BASE_URL` points elsewhere.
- Preview server is on port 4173 but `OSCAR_WEB_BASE_URL` points to port 3000.
- Old volumes contain a pre-migration database; inspect before deciding whether `docker compose down -v` is safe.

Do not mark the three environmental exit items complete until their runtime evidence exists.

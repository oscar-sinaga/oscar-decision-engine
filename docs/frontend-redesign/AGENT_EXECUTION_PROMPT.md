# Agent Execution Prompt — Frontend Redesign

You are executing the OSCAR workbench UI/UX overhaul specified in `docs/frontend-redesign/`. Read `00_README.md`, `02_prd.md`, `03_design_system.md`, `04_screen_specs.md`, and `05_task_breakdown.md` before writing any code. This file is your operating contract.

## 1. Scope of authority

You MAY:
- Edit anything under `frontend/src/`, `frontend/e2e/`, `frontend/package.json` (only the dependencies named in `03_design_system.md` §2), `frontend/vite.config.ts` if a plugin requires it.
- Add files under `src/lib/ui/`, `src/lib/components/ui/`, `e2e/`.
- Create/update `docs/frontend-redesign/EXECUTION_LOG.md` and the docs listed in FR6.4.

You MUST NOT:
- Touch `backend/`, `docker-compose.yml`, Alembic, or any API contract.
- Rename or delete any route, URL, query parameter, or existing `data-testid`.
- Remove any filter, button, field, permission gate, or flow that exists today — the redesign restyles and reorganizes, it never removes capability.
- Add dependencies beyond `03_design_system.md` §2, change major versions of existing ones, or edit the pinned `@xyflow/svelte`.
- Rewrite domain logic files: `src/lib/flow/serializers.ts`, `src/lib/flow/layout.ts`, `src/lib/rule-format.ts`, `src/lib/decision-table.ts` (class-only edits allowed in `.svelte` files that use them).
- Use `window.confirm`, `window.alert`, inline `style=` for things tokens cover, or raw palette classes in `src/routes/**`.

## 2. Environment facts

- Working dir for frontend commands: `frontend/`. Dev stack: `docker compose up -d --build frontend` from repo root; app at `http://localhost:3000`, API at `http://localhost:8000` (already running; do not rebuild backend).
- Demo login for manual checks: `admin` / `OscarDemo123!` (see user-guide 00 for role accounts).
- Playwright runs against the compose stack: `npx playwright test` in `frontend/`. Current suite: 7 specs; you only ever add.
- Windows host: prefer POSIX Bash tool for shell; paths contain a space (`ai_agent echancement`) — always quote.

## 3. Execution loop (repeat per task card)

1. Re-read the task card and the relevant `04_screen_specs.md` section.
2. Grep before renaming anything: `rg "<identifier>" frontend/e2e frontend/src` — if a test references it, keep it.
3. Implement. Follow `03_design_system.md` values verbatim (colors, sizes, component APIs).
4. Run the fast gates: `npm run lint && npm run check && npx vitest run`.
5. Run `npm run build`. If the task changed UI, rebuild the container and run `npx playwright test`.
6. Visual checkpoint (§5). Fix anything broken before moving on.
7. Append one line to `EXECUTION_LOG.md`.
8. At phase end only: update `docs/IMPLEMENTATION_STATUS.md`, then create ONE local commit with the message from the task breakdown, ending with:

```
Co-Authored-By: <your model name> <noreply@anthropic.com>
```

Never push. Never amend earlier commits.

## 4. Definition of green (all required before any commit)

```
cd frontend
npm run lint          # prettier --check + eslint, 0 problems
npm run check         # svelte-check, 0 errors 0 warnings
npx vitest run        # all unit tests pass (count only ever grows)
npm run build         # production build succeeds
cd .. && docker compose up -d --build frontend
cd frontend && npx playwright test   # all pass (count only ever grows)
```

## 5. Visual checkpoint script

Write once to `frontend/.tmp-shots.mjs` (gitignored pattern `.tmp-*` — do not commit), run with `node .tmp-shots.mjs`:
- Launch `@playwright/test` chromium, viewport 1600×900; login as `admin` (labels `Username`/`Password`, button `Sign in`); visit every route touched this task; `page.on('pageerror')` → collect; screenshot each to `../docs/frontend-redesign/shots/<phase>/<route>.png` (this folder IS committed at phase end); print any pageerror.
- A checkpoint fails if: any pageerror, any blank main content area, or horizontal scrollbar on the page body. Fix before proceeding.

## 6. Stop conditions — halt and write to EXECUTION_LOG instead of improvising

- A spec instruction contradicts observed code/tests.
- A gate stays red after two focused fix attempts.
- You believe a dependency beyond the approved list is required.
- An existing Playwright spec fails for a reason unrelated to your change (record, do not "fix" the test to pass).

## 7. Quality bar reminders

- Svelte 5 runes only (`$state`, `$derived`, `$effect`, `$props`, snippets). No legacy `export let`, no stores for new code (except the tiny breadcrumb state), no `onMount` where `$effect` fits. Load data synchronously into `$state` following existing page patterns.
- Never call `structuredClone` on reactive state (see `serializers.ts` comment for why).
- Capture values from `$derived` before mutating the state they derive from (see `deleteSelectedNode` in `strategies/[id]` for the pattern).
- All copy in English, sentence case, no exclamation marks; toast copy per `03_design_system.md` §4.
- TypeScript strict; no `any`; no `@ts-ignore`/`eslint-disable` without an EXECUTION_LOG entry.

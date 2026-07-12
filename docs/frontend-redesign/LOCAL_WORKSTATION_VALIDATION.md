# Local Workstation Validation — Frontend Redesign

Acceptance record for integrating the ChatGPT-produced frontend redesign (FR0–FR6) into the
local repository and validating it on this workstation. This file records **actual executed
results**, not aspirations.

## Environment

| Item | Value |
|---|---|
| Date | 2026-07-12 |
| OS | Windows 11 Home Single Language 10.0.26200 |
| Shell | Git Bash (POSIX) + PowerShell |
| Node | v24.16.0 |
| npm | 11.13.0 |
| Docker | 28.2.2 (build e6534b4) |
| Handoff source | `D:\ai_agent echancement\SMMF\OSCAR-Frontend-Redesign\oscar-decision-engine` |
| Handoff branch / HEAD | `feature/frontend-redesign` @ `fb22875` (working tree clean, FR0–FR6 present) |
| Local repo | `D:\ai_agent echancement\SMMF\oscar-decision-engine` |

## Git integration

| Step | Result |
|---|---|
| Pre-integration local HEAD | `integrate/phase3-20260711` @ `74ab127` |
| Backup branch created | `backup/before-frontend-redesign-local-20260712` @ `74ab127` (not moved) |
| Handoff imported as | `handoff/frontend-redesign` @ `fb22875` (via `git fetch <path> feature/frontend-redesign:refs/heads/handoff/frontend-redesign`) |
| Common ancestor with local | `74ab127` (shared history confirmed; no `--allow-unrelated-histories`) |
| `d248408` (Phase 3) ancestor of handoff | yes (exit 0) |
| Scope check `d248408..handoff` on `backend/`, `docker-compose.yml` | the only backend/compose deltas belong to the pre-existing local commit `316470d`, **not** to the FR0–FR6 range (`74ab127..handoff` touches only `frontend/` and `docs/`) — redesign scope is clean |
| Integration branch | `integrate/frontend-redesign-local` created from local HEAD `74ab127` |
| Merge method | **fast-forward** (`git merge --ff-only handoff/frontend-redesign`) — local HEAD was an ancestor of the handoff, so all FR0–FR6 commits and prior local commits are preserved linearly; **no conflicts** |
| Integration HEAD | `fb22875` |

No `reset --hard`, `clean -fd`, `rebase`, `commit --amend`, `push`, or `--allow-unrelated-histories`
was used. Protected branches were left untouched.

## Dependency install

- `npm ci` initially failed twice:
  1. `EPERM unlink` on a locked leftover dir `node_modules/.pre_acceptance_leftovers_20260711/lightningcss-*` — moved aside (gitignored, later removed), not deleted from tracked tree.
  2. `ETIMEDOUT` connecting to `packages.applied-caas-gateway1.internal.api.openai.org` — the handoff `package-lock.json` had **one** `resolved` URL pointing at ChatGPT's internal npm mirror (`@fontsource/jetbrains-mono`). Rewrote that single URL to `https://registry.npmjs.org/`; lockfile remained valid JSON (332 packages). This is committed as an app/build fix.
- `npm ci` then succeeded; `npm ls --depth=0` shows the expected tree including `bits-ui@2.18.1`, `svelte-sonner@1.1.1`, `@lucide/svelte@1.24.0`, `shadcn-svelte@1.4.1`, `tailwind-variants@3.2.2`, `@fontsource-variable/inter@5.2.8`, Svelte `5.56.4`, `@xyflow/svelte@1.6.2` (unchanged).

## Static quality gates

| Gate | Command | Result |
|---|---|---|
| ESLint + Prettier | `npm run lint` | **pass** — "All matched files use Prettier code style!" (after a one-time `prettier --write .` to normalize CRLF the handoff introduced; no source-content changes) |
| Type check | `npm run check` | **pass** — svelte-check 0 errors, 0 warnings (4910 files) |
| Unit tests | `npx vitest run` | **pass** — 9 test files, 41/41 tests |
| Production build | `npm run build` | **pass** — adapter-node build succeeded |

## Redesign contract verification

| Check | Result |
|---|---|
| `window.confirm` / `alert` / `prompt` in `src/` | none (grep clean) |
| Legacy `Badge.svelte` / `Card.svelte` | deleted; no imports remain |
| UI primitives under `src/lib/components/ui/`, app components under `src/lib/ui/` | present as specified |
| Raw palette classes (`bg-slate-*`, `text-blue-*`) in `src/routes` | 0 occurrences |
| Playwright-referenced `data-testid`s present in `src/` | all present (`main-nav`, `decision-table`→`testId`, `audit-table`, `features-table`, `decision-summary`, `trace-steps`, `strategy-flow-canvas`, `kpi-cards`, `sim-result`, `run-simulation`, `readonly-note`, `node-open-table`, `node-rule-links`) |
| Routes, URLs, filter params, API payloads | unchanged by redesign |

## Docker (no volume removal)

- `docker compose config --services` → `postgres`, `backend`, `frontend`.
- `docker compose up -d --build` — rebuilt images; the in-container `npm ci` succeeded (lockfile fix carried in). **No `down -v`; existing postgres volume retained.**
- Service status: `postgres` healthy (up 19h, original volume), `backend` up, `frontend` up.
- Backend health: `GET /health` → **200**. Frontend `GET /login` → **200**.
- Alembic head in DB: **`f4b7c9d2e601`** (Phase 3 head; no new migration created for the frontend work).
- Logs: backend/frontend/postgres clean; no errors.

## Playwright end-to-end

Run against the rebuilt compose stack (`workers: 1`, shared acceptance DB). **11 scenarios across 5 spec files:**

| Spec file | Scenarios | Result |
|---|---|---|
| `e2e/shell.e2e.ts` | 1 | pass |
| `e2e/list-pattern.e2e.ts` | 1 | pass |
| `e2e/governance-ui.e2e.ts` | 2 | pass |
| `e2e/phase3-authoring.e2e.ts` | 1 | pass |
| `e2e/phase3-flow-governance.e2e.ts` | 1 | pass |
| `e2e/phase3-expression-permissions.e2e.ts` | 1 | pass |
| `e2e/workbench.e2e.ts` | 4 | pass |
| **Total** | **11** | **11 passed**, run 4× consecutively (stability) — all green |

### E2E adjustments made (test selectors only — no product behavior changed, no bug masked)

These specs asserted against pre-redesign DOM. Each was updated to match the intended redesigned
UI while asserting the **same behavior**; none were weakened or deleted:

1. `phase3-flow-governance.e2e.ts` — status text `ACTIVE`/`DRAFT` → `Active`/`Draft` (StatusBadge now renders humanized labels, as designed in `03_design_system.md` §3.2).
2. `shell.e2e.ts` — scoped the `Monitor` group-label assertion to the nav (the word also legitimately appears in the topbar breadcrumb).
3. `list-pattern.e2e.ts` — added a `main-nav` visible wait after login (removes a login race).
4. `phase3-authoring.e2e.ts` — feature create form is now a Sheet (`[data-slot="sheet-content"]`); SQL preview and the test form are now tabs (`SQL preview`, `Test`) per the FR2/FR4 redesign. Selectors updated accordingly; the journey (create feature → author expression → preview → run test → 403 for analyst) is unchanged.

Config: added `trace: 'retain-on-failure'` to `playwright.config.ts` for future diagnosability.

## Visual acceptance (19 routes + responsive)

Captured at 1600×900 (desktop), 56px collapsed rail, and 400×800 (mobile). Screenshots in
`docs/frontend-redesign/shots/`. No page errors on any route; no unintended horizontal overflow
after fixes below.

| # | Route | Verdict |
|---|---|---|
| 1 | Login | pass — centered card, wordmark, collapsible demo accounts |
| 2 | Dashboard | pass — 4 KPI cards, decision-mix bar, top reason codes, volume trend, SLA snapshot, score distribution, recent decisions |
| 3 | Decisions list | pass — filter bar, sortable sticky table, mono IDs, StatusBadge |
| 4 | Decision detail + trace | pass — 3 summary cards, trace timeline (expandable steps), tabs, "View executed flow" preserved |
| 5 | Rules list | pass |
| 6 | Rule builder/detail | pass — Builder/SQL preview/Advanced JSON/Test tabs, version timeline, Used-by panel |
| 7 | Decision Tables list | pass |
| 8 | Decision Table grid | pass — toolbar, frozen header, wildcard cells, inline overlap warning |
| 9 | Strategies list | pass |
| 10 | Strategy canvas | pass — full-height canvas, collapsible palette/inspector, sticky action bar, typed node colors, read-only banner |
| 11 | Feature Catalog | pass — table + create/edit in Sheet |
| 12 | Model Registry | pass |
| 13 | Manual Review queue | pass |
| 14 | Manual Review detail | pass — two-column evidence/work layout, override reason inline warning, guardrails intact |
| 15 | Single Simulation | pass — tabs, result panel |
| 16 | Batch Simulation | pass — population input, run config, compare panel with empty state |
| 17 | Approvals (Admin) | pass — inbox with clean empty state |
| 18 | Audit Log | pass — filters, table; row → drawer with field-level diff + metadata + correlation id |
| 19 | Users & Roles (Admin) | pass — tabs, role dialog |

### Accessibility findings

- Vendored bits-ui primitives provide focus traps (dialog/sheet/dropdown), Escape-to-close, and ARIA wiring.
- Icon-only controls carry `aria-label` (e.g. Collapse/Expand navigation), verified by the shell e2e locating them by label.
- Tables use semantic `<thead>/<th>` with sticky headers; sortable columns are buttons.
- Focus-visible rings present via token styling. No contrast red flags on the light theme (dark mode intentionally deferred to FR7).

### Responsive findings

- Desktop and collapsed icon-rail: clean.
- Mobile 400px: sidebar collapses; content reflows. **Two overflow issues found and fixed** (see below).

## Bugs found and fixed on the workstation

All are small, verified, and committed as an app-fix commit separate from the acceptance docs.

1. **Dashboard decision-volume-trend bars invisible.** The bar column used `items-end` on a
   fixed-height flex row; percentage-height bars had no resolved parent height, so they rendered
   at ~0px. Changed to `items-stretch`. Verified bars now render (heights e.g. 6/142/29px).
2. **Mobile horizontal overflow on Dashboard (top reason codes).** Long monospace reason codes
   couldn't shrink. Added `min-w-0 break-all` + `shrink-0` on the count.
3. **Mobile horizontal overflow on Dashboard (recent decisions table).** The intrinsic table
   width widened its grid column. Added `min-w-0` to the column wrapper (the DataTable already
   scrolls internally via `overflow-auto`). Verified `scrollWidth == clientWidth` at 400px after fix.

Re-ran full gates after these fixes: lint/check/vitest/build green; Playwright 11/11 (×4).

## Outstanding / not done

- **Dark mode (FR7)** intentionally deferred; tokens are structured for it but not shipped.
- **Manual Review detail via direct `/manual-review/undefined`** shows the correct NOT_FOUND error
  state — expected; the working flow is row-click from the queue (validated).
- No push, no deploy, no merge into `integrate/phase3-20260711`, `feature/oscar-mvp`, or `main`
  (final merge left to the maintainer per handoff instructions).

## Commits created on `integrate/frontend-redesign-local`

1. app/build fixes (lockfile registry URL, dashboard trend + mobile overflow).
2. this acceptance record + e2e selector adjustments + playwright trace config —
   `test(e2e): validate frontend redesign workstation acceptance`.

# 05 — Task Breakdown (Execution Plan)

Phases run strictly in order. Every task card lists: files, steps, definition of done (DoD). **Gate suite** = `npm run lint && npm run check && npx vitest run && npm run build` in `frontend/`, then `docker compose up -d --build frontend` and `npx playwright test` from `frontend/` — all green. One commit per phase (message given), only after gates.

Golden rules (repeated from AGENT_EXECUTION_PROMPT): never edit `backend/`; never rename routes or existing `data-testid`s; never remove an existing filter, action, or field; when a task conflicts with reality, stop and record in `docs/frontend-redesign/EXECUTION_LOG.md` instead of improvising.

---

## FR0 — Foundation (no visible page changes yet)

### FR0.1 Dependencies & tokens
- Files: `frontend/package.json`, `src/routes/layout.css`, `src/lib/utils.ts` (cn helper), `components.json`.
- Steps: run shadcn-svelte init (per `03_design_system.md` §2); install deps table §2; replace `layout.css` with the token block §1 (keep existing two imports at top); verify fonts load in dev.
- DoD: gate suite green; app renders identically except font = Inter.

### FR0.2 Vendored ui primitives
- Files: `src/lib/components/ui/*` (curated list §3.1 only).
- Steps: `shadcn-svelte add` each; mount `<Toaster />` (sonner) and the `ConfirmDialog` host in `+layout.svelte` (host may be added in FR0.3).
- DoD: `npm run check` clean (vendored files must typecheck under strict).

### FR0.3 App-level components
- Files: `src/lib/ui/{status.ts, StatusBadge.svelte, DataTable.svelte, EmptyState.svelte, FilterBar.svelte, PageHeader.svelte, ConfirmDialog.svelte, KpiCard.svelte, VersionTimeline.svelte, TraceTimeline.svelte, DiffView.svelte, RelativeTime.svelte, diff.ts, time.ts}` + specs `status.spec.ts, diff.spec.ts, time.spec.ts, datatable-sort.spec.ts` (sort logic exported as pure fn).
- Steps: implement per `03_design_system.md` §3.2 exactly; write the four unit-spec files.
- DoD: Vitest ≥ 34 passing; gate suite green.
- Commit: `feat(ui): design tokens, vendored primitives, and app component kit`

## FR1 — App shell

### FR1.1 Shell components
- Files: `src/lib/ui/{AppShell.svelte, SideNav.svelte, TopBar.svelte, breadcrumb.svelte.ts}`; rewrite `src/routes/+layout.svelte` to use them (auth logic untouched).
- Notes: nav grouped per PRD §5, icons per §3.2; keep `data-testid="main-nav"` on the nav element; keep label texts exactly (`Dashboard, Decisions, Rules, Decision Tables, Feature Catalog, Strategies, Simulations, Model Registry, Manual Review, Audit Log, Admin`); collapse state persisted; user menu contains Sign out.
### FR1.2 Login redesign
- Files: `src/routes/login/+page.svelte`. Keep labels + button name.
### FR1.3 Shell e2e
- Files: `e2e/shell.e2e.ts` (new) per PRD §8.
- DoD: gate suite green; Playwright 8/8.
- Commit: `feat(ui): SaaS app shell with grouped navigation, topbar, and breadcrumbs`

## FR2 — List pages (two commits allowed: A = decisions, rules, decision-tables, strategies; B = features, simulations, models, manual-review, audit)

### FR2.A / FR2.B per-route conversion
- For each route in `04_screen_specs.md`: replace hand-rolled table with `PageHeader + FilterBar + DataTable (+ EmptyState, Pagination)`; set breadcrumb; mono/alignment rules §1; StatusBadge everywhere a status renders; skeleton while loading.
- Constraints: filter params and their query behavior unchanged; row-click targets unchanged; features page moves create/edit into `Sheet` but keeps identical fields + validation messages.
### FR2.C List-pattern e2e
- Files: `e2e/list-pattern.e2e.ts` (new) per PRD §8 against /decisions.
- DoD: gate suite green; Playwright 9/9; every list route manually screenshotted via smoke script.
- Commits: `feat(ui): data-table pattern for core list pages (A)` / `...(B) and list-pattern e2e`

## FR3 — Dashboard
- Files: `src/routes/dashboard/+page.svelte` (+ small local components if needed).
- Steps: per `04_screen_specs.md` /dashboard; charts hand-built (flex/grid bars, no lib); per-card skeleton/error.
- DoD: gate suite green (existing dashboard e2e still passes); numbers match previous implementation for same API data.
- Commit: `feat(ui): dashboard KPI cards, decision mix, and activity panels`

## FR4 — Editors & detail pages (one commit per task allowed)

### FR4.1 Decision detail + TraceTimeline (`/decisions/[id]`)
- Keep `decision-summary`, `trace-steps` testids and "View executed flow" text.
### FR4.2 Rules editor (`/rules/new`, `/rules/[id]`)
- Two-column + tabs per spec; restyle builder internals (props untouched).
### FR4.3 Decision-table grid (`/decision-tables/[id]`)
- Toolbar, frozen header/column, wildcard + overlap styling; grid logic file untouched except class changes.
### FR4.4 Strategy canvas layout (`/strategies/[id]`)
- Full-height layout, collapsible panels, sticky action bar, node colors; all behavior and testids from commit `1e60613` preserved.
### FR4.5 Manual-review workspace (`/manual-review/[id]`)
- Two-column workspace per spec; guardrail messaging inline.
### FR4.6 Simulations (`/simulations`, `/simulations/batch`)
- Tabs + compare view per spec.
- DoD (each): gate suite green; related Playwright specs untouched and passing.
- Commits: `feat(ui): <area> redesign` per task or grouped ≤2.

## FR5 — Governance

### FR5.1 Audit log + DiffView drawer (`/audit`)
### FR5.2 Approvals inbox + admin tabs (`/admin`)
- Approve/Reject via ConfirmDialog `requireReason`; self-approval API error surfaces as toast + inline note.
### FR5.3 e2e additions: audit drawer diff row; approval reason dialog (extend existing governance spec or new `e2e/governance-ui.e2e.ts`).
- DoD: gate suite green; Playwright ≥ 10.
- Commit: `feat(ui): governance surfaces — approvals inbox, audit diff drawer, admin`

## FR6 — Feedback, a11y, stability pass

### FR6.1 Toasts on all mutations
- Sweep every `await api(` mutation call in `src/routes/**`; add success/error toasts per §4 copy. Add `e2e` assertion (toast visible after a save) to an existing spec.
### FR6.2 ConfirmDialog rollout
- Replace the canvas `confirm()`; add confirms to reject/rollback/retire/deactivate/role-change flows listed in PRD E7.
### FR6.3 A11y sweep
- Focus-visible audit, `aria-label` on icon-only buttons, `<th scope="col">`, dialog focus check, contrast spot-check on tokens.
### FR6.4 Cleanup & docs sync
- Delete `Badge.svelte`/`Card.svelte` re-exports and dead classes; grep gate: `rg "window.confirm|bg-slate-|text-blue-" src/routes` returns nothing (raw palette allowed only under `src/lib`); update `docs/09_screen_spec.md`, `docs/IMPLEMENTATION_STATUS.md`, ADR in `docs/IMPLEMENTATION_DECISIONS.md` (D1–D10).
- DoD: full gate suite green; Playwright full count green; smoke screenshots of all 19 routes reviewed.
- Commit: `feat(ui): feedback layer, confirmations, a11y pass, and design-system cleanup`

## FR7 — Deferred (requires new approval)
Dark mode toggle (token overrides + `data-theme`), command palette (Ctrl+K), saved filters, table density toggle.

---

## Cross-phase progress tracking

Maintain `docs/frontend-redesign/EXECUTION_LOG.md`: one line per task (`FR2.A decisions — done, gates green, note: …`) plus any deviation with rationale. Update `docs/IMPLEMENTATION_STATUS.md` at each phase commit.

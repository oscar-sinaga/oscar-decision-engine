# 02 — PRD: OSCAR Workbench UI/UX Overhaul

## 1. Problem statement

The workbench's capabilities (generic rules, decision-table grid, DAG canvas, simulations, governance) now exceed its presentation. Pages are functional but hand-styled, feedback is silent, navigation is flat, and loading/empty/error states are undesigned. For a tool whose users stare at it all day and whose credibility depends on trust, the UI must reach contemporary SaaS standard without destabilizing a verified system (213 pytest, 30 Vitest, 7/7 Playwright).

## 2. Goals

| # | Goal | Measured by |
|---|---|---|
| G1 | A coherent design system: tokens, primitives, one visual grammar | 0 raw-palette color classes in routes (only semantic tokens/ui components); component inventory complete |
| G2 | SaaS-standard app shell: grouped sidebar, topbar, breadcrumbs, user menu, responsive | FR1 acceptance checklist |
| G3 | Every list page: sortable sticky-header table, filter bar, skeleton, empty state | FR2 checklist per route |
| G4 | Every mutation gives feedback; every destructive action confirms | grep gate: no `window.confirm`; toast called on all mutation paths |
| G5 | Editors feel like products: canvas hero layout, grid polish, trace timeline, review workspace | FR4 checklist per route |
| G6 | Stability preserved end-to-end | All gates green after every phase; Playwright grows, never shrinks |
| G7 | Accessibility floor | Keyboard operable dialogs/menus/tables; visible focus; WCAG AA contrast for text |

## 3. Non-goals

- New features, new API calls beyond those already exposed, backend changes of any kind.
- Dark mode shipping (FR7), i18n, mobile-first layouts, offline, real-time push.
- Rewriting domain editors' logic (builders, grid, canvas serializers stay).

## 4. Personas and primary journeys (from `docs/user-guide/12`)

| Persona | Journey the UI must make effortless |
|---|---|
| Risk Policy Analyst | Author rule → assemble table → wire strategy on canvas → simulate → submit; needs fast editors, clear validation, visible version state |
| Credit Risk Manager | Dashboard scan → approvals inbox → evidence (simulation) → approve/reject with reason; needs trust cues and low-friction review |
| Underwriter | Queue triage by SLA → case workspace (trace, docs, comments) → decide with guardrails; needs a single-screen workspace |
| Compliance/Auditor | Search decisions → read trace; filter audit log → read before/after diff; needs legibility and export-free evidence reading |
| Data Scientist | Model registry → scorecard bands → batch simulation compare; needs numbers presented for comparison |

## 5. Information architecture

```
Topbar: [☰] [Breadcrumb: Section / Page / Detail]              [DEMO badge] [User menu ▾]
Sidebar (collapsible):
  MONITOR   Dashboard · Decisions
  AUTHOR    Rules · Decision Tables · Strategies · Feature Catalog · Model Registry
  OPERATE   Simulations · Manual Review
  GOVERN    Audit Log · Admin
Footer of sidebar: version tag (git short sha or "local"), collapse toggle
```

- URLs unchanged. `Model Registry` keeps `/models`. Active item = active group expanded + item highlighted.
- Breadcrumb derives from route + loaded entity (e.g., `Author / Strategies / E2E_FLOW_MRGKQGUZ`).
- User menu: name, roles, sign out. DEMO badge is static (env-driven later).

## 6. Functional requirements by epic

### E1 Design system (FR0)
- Tailwind 4 `@theme` tokens per `03_design_system.md` §1; Inter + JetBrains Mono self-hosted.
- Vendored ui primitives per `03_design_system.md` §3 with stories exercised by unit tests where logic exists (DataTable sorting, ConfirmDialog promise API).
- `StatusBadge` maps every lifecycle/decision/severity status to token colors + icon (single source `src/lib/ui/status.ts`).

### E2 App shell (FR1)
- Grouped sidebar (collapsible to 56px icon rail; drawer under 768px), topbar with breadcrumbs and user menu, redesigned login page.
- `data-testid="main-nav"` preserved; every nav label text unchanged (Playwright depends on both).

### E3 List pages (FR2)
Applies to: decisions, rules, decision-tables, strategies, features, simulations, models, manual-review, audit.
- `PageHeader` with primary action (where permission allows), `FilterBar` (existing filters restyled, none removed), `DataTable` (sticky header, hover, sortable columns where data is client-side, skeleton rows while loading, `EmptyState` with CTA, `Pagination` preserved).
- Codes/IDs in mono; numerics right-aligned tabular; statuses via `StatusBadge`; timestamps humanized with exact value in `title`.

### E4 Dashboard (FR3)
- KPI strip (Decisions today, Approval rate, Manual review rate, Error rate + deltas), decision-mix stacked bar, top reason codes, score distribution, recent decisions table, review SLA snapshot. All from existing monitoring endpoints; skeleton per card; per-card error state.

### E5 Editors (FR4)
- **Rules**: builder cards with clear WHEN/THEN hierarchy, sticky summary/action rail, tabs (Builder / SQL preview / JSON advanced / Test), inline validation messages.
- **Decision-table grid**: toolbar (add row/column, hit policy indicator), frozen header + first column, wildcard cells visually distinct, overlap warnings inline on rows, cell edit affordance.
- **Strategy canvas**: full-height layout, collapsible palette/inspector, sticky lifecycle action bar, node color-per-type + icons, read-only banner (kept), zoom controls styled.
- **Decision detail/trace**: summary header cards; trace as vertical timeline of steps (status icon, duration, expandable payload); link to executed flow (kept).
- **Manual review case**: two-column workspace — left evidence (summary, trace link, documents checklist), right actions (status, comments timeline, decision form with inline guardrail messaging).
- **Simulations**: single vs batch tabs; batch compare as side-by-side aggregate cards + shifts table with directional coloring.

### E6 Governance (FR5)
- Approvals inbox: card list with object type icon, requester, note, evidence link, approve/reject inline with reason dialog.
- Audit log: row click opens `Drawer` with structured before/after **field-level diff** (added/removed/changed rows highlighted; fall back to JSON blocks for unstructured payloads).
- Admin: users table with role chips and edit dialog; role→permission matrix in a scrollable card.

### E7 Feedback, a11y, stability pass (FR6)
- `svelte-sonner` toasts on every mutation success/failure (standard copy defined in `03_design_system.md` §4).
- `ConfirmDialog` for: reject version, rollback, retire, delete node/edge replacement, deactivate feature, role changes. Remove the one `window.confirm`.
- Focus-visible everywhere; dialogs trap focus (bits-ui); tables get proper `<th scope>`; icon-only buttons get `aria-label`; contrast audit.
- New Playwright specs per §8. Docs sync (screen spec + status).

## 7. Stability requirements (hard constraints)

| # | Constraint |
|---|---|
| S1 | No route path, query param, or `data-testid` used by existing tests may change; grep the e2e specs before renaming anything |
| S2 | All existing Playwright tests pass unmodified **except** where a spec asserts styling incidentally; such edits must be listed in the phase commit message |
| S3 | Full gate suite green before every commit: `npm run lint`, `npm run check`, `npx vitest run`, `npm run build`, `npx playwright test` against rebuilt compose stack |
| S4 | New dependencies: only those named in this pack, exact versions committed to the lockfile; nothing else without a written decision in `docs/IMPLEMENTATION_DECISIONS.md` |
| S5 | One commit per phase; a phase that cannot reach green is reverted (`git restore`/`git checkout`) rather than committed broken |
| S6 | Backend containers untouched; only the frontend image rebuilds |
| S7 | Visual checkpoints: the smoke-screenshot script (`AGENT_EXECUTION_PROMPT.md` §5) runs at each phase end; screenshots reviewed for obvious breakage (blank areas, overflow, unreadable contrast) |

## 8. Test plan additions

| Spec | Asserts |
|---|---|
| `e2e/shell.e2e.ts` (new, FR1) | Grouped nav renders, collapse toggle works, breadcrumb shows on a detail page, user menu opens and signs out |
| `e2e/list-pattern.e2e.ts` (new, FR2) | Decisions list: skeleton→rows, sort toggles order, empty state on impossible filter, pagination |
| FR4/FR5 additions in existing specs | Trace timeline steps expand; audit drawer shows a changed-field row; approvals inbox approve requires reason dialog |
| FR6 | Confirm dialog blocks reject until reason; toast visible after save (`data-sonner-toast`) |
| Unit (Vitest) | DataTable sort logic, status map completeness (every enum in `types.ts` has a StatusBadge entry), diff util (audit before/after), date humanizer |

## 9. Rollout & sequencing

FR0 → FR1 → FR2 → FR3 → FR4 → FR5 → FR6 sequentially (each depends on the previous). FR2 may be split into two commits (list pages A/B) if the diff grows past ~1.5k lines. FR7 (dark mode, command palette, saved filters, density toggle) is explicitly deferred and requires a new go-ahead.

## 10. Acceptance (definition of done for the whole program)

1. Every FR0–FR6 task card checked off; gates green; commits per protocol.
2. `docs/09_screen_spec.md` updated to describe the new UI; `docs/IMPLEMENTATION_STATUS.md` and `docs/IMPLEMENTATION_DECISIONS.md` (ADR for D1–D10) updated.
3. Playwright count strictly greater than 7, all green on the rebuilt stack.
4. A reviewer can walk user-guide chapters 01–12 against the new UI without hitting a renamed menu, missing button, or dead flow.

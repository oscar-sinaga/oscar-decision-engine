# OSCAR Frontend Redesign — Specification Pack

> Status: **Approved for execution**. Owner: Oscar Sinaga. Written: 2026-07-12.
> Execution model: same delegation pattern as `docs/phase3/` — an executing agent (small model allowed) works through `05_task_breakdown.md` phase by phase under the rules in `AGENT_EXECUTION_PROMPT.md`.

## What this is

A complete plan to overhaul the OSCAR workbench UI/UX to modern SaaS standard: a real design system, a proper app shell, consistent list/detail/editor patterns, first-class feedback (toasts, dialogs, skeletons, empty states), and an interaction layer worthy of the decision-domain features that already work underneath.

**This is a re-skin and interaction upgrade, not a rewrite.** All backend APIs, routes, URLs, permissions, and domain components' behavior stay exactly as they are. Stability is a hard requirement: every phase ends with the full gate suite green (svelte-check, eslint/prettier, Vitest, production build, 7/7+ Playwright).

## Reading order

| File | Contents |
|---|---|
| `01_ux_research.md` | Benchmarks (SaaS standards, rules-engine products), findings from the current UI audit, and the resulting design decisions with rationale |
| `02_prd.md` | Goals, non-goals, personas, information architecture, requirements per epic, acceptance criteria, stability/rollback policy |
| `03_design_system.md` | Design tokens (Tailwind 4 `@theme`), typography, color/status semantics, and the exact component inventory with props/APIs |
| `04_screen_specs.md` | Page-by-page redesign spec: current state → target state for all 19 routes |
| `05_task_breakdown.md` | Phased, atomic task cards (FR0–FR6 + deferred FR7) with files, steps, definition of done, and gates |
| `AGENT_EXECUTION_PROMPT.md` | Operating rules for the executing agent: what it may and may not touch, gate commands, commit protocol, stop conditions |

## Current state (audited 2026-07-12)

- SvelteKit 2 / Svelte 5 runes / TypeScript strict / Tailwind 4 (`@import 'tailwindcss'` + forms plugin only — **no custom tokens**), Vitest 30, Playwright 7/7.
- 19 routes; largest pages: `decision-tables/[id]` (692 lines), `strategies/[id]` (689), `manual-review/[id]` (373), `rules/[id]` (354), `features` (331).
- 11 shared components only (`Badge`, `Card`, `ErrorNote`, `JsonBlock`, `Pagination`, `SqlPreview`, `FeaturePicker`, `ConditionBuilder`, `BranchEditor`, `ActionListEditor`, `ExpressionEditor`). No Button/Input/Select/Dialog/Toast/Table/Skeleton/EmptyState primitives — every page hand-rolls Tailwind classes.
- App shell: fixed 208px dark sidebar with a flat list of 11 items, no topbar, no breadcrumbs, no user menu (sign-out is a text link at the sidebar bottom), not responsive.
- Feedback: no toasts; success is usually a silent reload. One native `confirm()` (strategy canvas edge replacement). Errors via `ErrorNote` only. No loading skeletons; "Loading…" text. No empty states.
- Strategy canvas (`@xyflow/svelte` 1.6.2) works and is interactive after the 2026-07-12 fix (`1e60613`).

## Decisions already made (do not relitigate during execution)

1. **Keep the stack.** SvelteKit + Svelte 5 + Tailwind 4 + @xyflow/svelte. No framework or router changes.
2. **Adopt shadcn-svelte components (bits-ui + tailwind-variants) via the CLI**, vendored into `src/lib/components/ui/`. Rationale: runes-native, accessible primitives whose source lives in-repo (no runtime lock-in), the de-facto SaaS baseline in 2026. Curated set only (listed in `03_design_system.md`).
3. **Icons: `@lucide/svelte`.** Feedback toasts: `svelte-sonner`. Both pinned in the lockfile.
4. **Typography: Inter via `@fontsource-variable/inter`** (self-hosted; no CDN).
5. **Light theme ships; dark mode is token-ready but deferred** to FR7.
6. **Domain components are restyled, never rewritten**: `ConditionBuilder`, `BranchEditor`, `ActionListEditor`, `ExpressionEditor`, `SqlPreview`, decision-table grid, strategy canvas keep their logic and public props.
7. **No route renames, no `data-testid` removals, no API/backend changes.** New testids may be added.
8. **Navigation is grouped** (Monitor / Author / Operate / Govern) in a collapsible sidebar with a topbar (breadcrumbs, DEMO badge, user menu).

## Execution at a glance

```
FR0 Foundation   → tokens, fonts, deps, ui primitives (no page changes)
FR1 App shell    → sidebar groups, topbar, breadcrumbs, responsive nav
FR2 List pages   → DataTable pattern on 9 list routes
FR3 Dashboard    → KPI cards, trends, activity
FR4 Editors      → rules, decision-table grid, strategy canvas layout, trace, review workspace, simulations
FR5 Governance   → approvals inbox, audit drawer + before/after diff, admin
FR6 Feedback & stability pass → toasts, confirm dialogs, a11y, e2e additions, docs sync
FR7 (deferred)   → dark mode, command palette, saved filters, density toggle
```

One local commit per phase (conventional message), full gates before each commit, never push.

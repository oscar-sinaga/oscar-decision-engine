# 01 — UI/UX Research and Design Decisions

## 1. What we benchmarked

### 1.1 SaaS application standards (2026)

Sources: FlowmazeUX SaaS dashboard practices, Pencil & Paper dashboard UX patterns, Setproduct data-table reference, Hashbyt enterprise UI principles, sixtythirtyten color-system guidance, Mavik Labs / OneMinuteBranding Tailwind v4 token architecture. Key convergent findings:

- **Density lost, clarity won.** The "cram everything above the fold" era is over; the winning pattern is a small KPI strip (4–6 metrics), progressive disclosure for detail, and generous whitespace. OSCAR's audience (risk analysts, managers, underwriters) reads numbers all day — scannability beats spectacle.
- **The canonical shell**: persistent sidebar 240–280px with grouped items, slim topbar carrying context (breadcrumbs, environment, user), content area with a consistent page header. Sidebar groups matter once nav exceeds ~7 items — OSCAR has 11.
- **Data tables are the product** in enterprise tools: sticky headers, 40–48px rows, right-aligned numerics, monospace for codes/IDs, row hover, skeleton loading, designed empty states, and filters as a persistent bar rather than hidden panels.
- **Token architecture**: three layers (primitives → semantic roles → components) expressed as CSS variables; Tailwind 4's `@theme` makes this native. Semantic status colors must be consistent app-wide (one green means one thing).
- **Feedback is non-negotiable**: every state-changing action confirms via toast; destructive actions get an in-app confirm dialog (never `window.confirm`); every async view has skeleton → content → empty → error states designed.

### 1.2 Decision/rules-engine products

Sources: GoRules decision-table editor, DecisionRules, Camunda DMN modeler, plus the IDX iDecision screenshots already analyzed in `docs/04_idx_idecision_analysis.md`.

- **Spreadsheet-feeling decision tables win business users**: visible column typing, inline cell editing, row hover actions, wildcard cells visually distinct, validation warnings inline at the offending row — OSCAR's grid already does most of the logic; the presentation must catch up.
- **Canvas products treat the graph as the hero**: the canvas gets maximum real estate, palettes and inspectors are collapsible side panels, nodes are color-coded by type with icons, and read-only vs draft states are visually unmistakable. Execution results can be replayed onto the graph (OSCAR already links traces to the flow — surfacing this is cheap and differentiating).
- **Versioning UX**: version pickers as timeline/stepper (draft → pending → active → retired), not plain lists; status is color + icon + label, never color alone.
- **Rule editors read as sentences**: "WHEN … THEN …" cards with human preview beat raw JSON. OSCAR already has builder-first editing and SQL-style preview; the redesign only elevates hierarchy and spacing.

### 1.3 Svelte 5 ecosystem status (verified July 2026)

- **shadcn-svelte** is runes-native and Tailwind-4-current; components are copied into the repo (full ownership, no runtime dependency on the generator). Built on **bits-ui** headless primitives (focus management, ARIA, keyboard handled for us).
- **svelte-sonner** is the standard toast layer; **@lucide/svelte** the standard icon set; **tailwind-variants + clsx + tailwind-merge** the standard styling utilities — all Svelte-5 compatible and stable.

Sources: [shadcn-svelte docs](https://www.shadcn-svelte.com/docs), [shadcn-svelte Svelte 5 migration](https://www.shadcn-svelte.com/docs/migration/svelte-5), [GoRules decision table](https://gorules.io/components/decision-table), [DecisionRules](https://www.decisionrules.io/en/), [Camunda decision tables](https://camunda.com/blog/2025/02/decision-tables-for-automating-business-rules/), [Setproduct data-table guide](https://www.setproduct.com/blog/data-table-ui-design), [Pencil & Paper dashboard patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards), [Mavik Labs Tailwind v4 tokens](https://www.maviklabs.com/blog/design-tokens-tailwind-v4-2026/), [sixtythirtyten SaaS palette](https://www.sixtythirtyten.co/blog/saas-dashboard-color-palette-css-tailwind).

## 2. Current-UI audit findings

| # | Finding | Severity | Addressed in |
|---|---|---|---|
| A1 | No design tokens; raw Tailwind palette classes hand-picked per page → drift (3 different blues in buttons already) | High | FR0 |
| A2 | No primitive components (Button/Input/Dialog/Toast/Table/Skeleton); every page re-implements | High | FR0 |
| A3 | Flat 11-item sidebar, no grouping, no topbar, no breadcrumbs, sign-out buried, not responsive | High | FR1 |
| A4 | List pages: unstyled tables, no sticky header, no sort, no skeletons, "Loading…" text, no empty states | High | FR2 |
| A5 | Silent success on most mutations; user cannot tell whether save happened without watching data | High | FR6 |
| A6 | One native `confirm()` (canvas edge replace); destructive actions (reject, rollback, retire) have no confirmation at all | High | FR6 |
| A7 | Dashboard is a wall of numbers, no hierarchy or trend context | Medium | FR3 |
| A8 | Giant editor pages (692/689 lines) with cramped 3-column layouts; panels can't collapse; canvas viewport small | Medium | FR4 |
| A9 | Audit log before/after shown as raw JSON blocks side-by-side; hard to spot the change | Medium | FR5 |
| A10 | Status badges: single `Badge` maps some statuses; colors inconsistent with severity semantics | Medium | FR0/FR2 |
| A11 | Forms lack inline validation states; errors only appear post-submit at page level | Medium | FR4/FR6 |
| A12 | No keyboard/a11y pass: missing focus rings on custom controls, dialogs absent so no focus traps needed yet, canvas has aria but tables don't | Medium | FR6 |
| A13 | Login page bare | Low | FR1 |
| A14 | Monospace not used for codes/IDs, numerics not right-aligned | Low | FR2 |

## 3. Design decisions and rationale

| Decision | Choice | Why (and what was rejected) |
|---|---|---|
| D1 Component strategy | shadcn-svelte vendored set on bits-ui | In-repo source keeps small-model execution deterministic (components are files it can read, not APIs it must guess). Rejected: full hand-rolled system (re-invents focus/ARIA, slower, buggier); Skeleton/Flowbite (runtime lib lock-in, theming friction). |
| D2 Visual language | Neutral slate surfaces, **indigo-600 primary**, semantic status set (emerald/amber/red/sky/violet), radius 8px cards / 6px controls, subtle borders over shadows | Enterprise-neutral, high contrast for numbers; indigo distinguishes actions from the status greens/reds that saturate a decisioning UI. |
| D3 Typography | Inter Variable; 13px base UI, 12px tables, tabular-nums for figures, JetBrains Mono for codes/JSON | Risk users compare numbers; tabular figures and monospace codes are functional, not cosmetic. |
| D4 Navigation IA | 4 groups: **Monitor** (Dashboard, Decisions), **Author** (Rules, Decision Tables, Strategies, Feature Catalog, Scorecards/Models), **Operate** (Simulations, Manual Review), **Govern** (Audit Log, Admin) | Mirrors the role workflows in `docs/user-guide/12`; each persona lives in one group. |
| D5 Page patterns | Every route composed from: `PageHeader` (+actions), optional `FilterBar`, `DataTable`/content, `Drawer` for quick detail, `Dialog` for confirm/forms, toast on every mutation | One grammar app-wide; small agents implement per-page by filling a known template. |
| D6 Lifecycle UX | `VersionTimeline` stepper (Draft → Pending → Active → Retired/Rejected) + `StatusBadge` with icon+label | The version lifecycle is OSCAR's core mental model (user-guide ch. 01); it deserves a first-class visual. |
| D7 Canvas layout | Full-height hero canvas; palette and inspector as collapsible panels; sticky action bar; visible read-only banner | Matches Camunda/GoRules convention; fixes A8. |
| D8 Dark mode | Tokens structured for it; shipping deferred (FR7) | Halves QA surface now; token discipline makes it a small later step. |
| D9 Charts | CSS/SVG bars + sparklines built in-house for FR3; no chart library | Dashboard needs are simple (counts, rates, distributions); a charting dep is not worth the stability risk. Revisit only if FR3 acceptance fails. |
| D10 Responsiveness | Desktop-first; sidebar collapses to icon rail ≤1280px and drawer ≤768px; editors clamp to min-width with horizontal scroll inside panels | Internal tool used on laptops; mobile is read-only convenience, not a target. |

## 4. Anti-goals

- No AI-assistant UI, no theme builder, no per-user layout customization.
- No visual redesign of the decision *logic* semantics (operators, hit policies, node types render as specified in phase-3 docs).
- No migration off @xyflow/svelte, no SSR changes, no route or URL changes.

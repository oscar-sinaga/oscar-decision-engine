# 03 — Design System Specification

Everything here is normative. The executing agent copies values verbatim.

## 1. Tokens (Tailwind 4, in `src/routes/layout.css`)

```css
@import 'tailwindcss';
@plugin '@tailwindcss/forms';
@import '@fontsource-variable/inter';
@import '@fontsource/jetbrains-mono/400.css';
@import '@fontsource/jetbrains-mono/600.css';

@theme {
	/* Brand + neutrals (primitives) */
	--color-primary-50: #eef2ff;
	--color-primary-100: #e0e7ff;
	--color-primary-500: #6366f1;
	--color-primary-600: #4f46e5; /* primary action */
	--color-primary-700: #4338ca;

	/* Semantic surfaces & text (light theme values; dark theme = FR7 override) */
	--color-surface: #ffffff;
	--color-surface-muted: #f8fafc;   /* page background */
	--color-surface-sunken: #f1f5f9;  /* wells, table header */
	--color-border: #e2e8f0;
	--color-border-strong: #cbd5e1;
	--color-text: #0f172a;
	--color-text-muted: #64748b;
	--color-text-faint: #94a3b8;

	/* Status */
	--color-success: #059669;  --color-success-bg: #ecfdf5;
	--color-warning: #d97706;  --color-warning-bg: #fffbeb;
	--color-danger: #dc2626;   --color-danger-bg: #fef2f2;
	--color-info: #0284c7;     --color-info-bg: #f0f9ff;
	--color-special: #7c3aed;  --color-special-bg: #f5f3ff; /* fraud / override-level */
	--color-neutral: #475569;  --color-neutral-bg: #f1f5f9;

	/* Typography */
	--font-sans: 'Inter Variable', ui-sans-serif, system-ui, sans-serif;
	--font-mono: 'JetBrains Mono', ui-monospace, monospace;

	/* Shape & elevation */
	--radius-card: 0.5rem;      /* 8px cards, dialogs, drawers */
	--radius-control: 0.375rem; /* 6px buttons, inputs, badges */
	--shadow-card: 0 1px 2px 0 rgb(15 23 42 / 0.05);
	--shadow-overlay: 0 10px 30px -5px rgb(15 23 42 / 0.25);
}
```

Rules:
- Routes and components use **semantic classes only** (`bg-surface`, `text-text-muted`, `border-border`, `bg-primary-600`, `text-danger`…). Raw palette classes (`bg-slate-*`, `text-blue-*`, etc.) are allowed **only inside `src/lib/ui/` and `src/lib/components/ui/`** where a token doesn't exist yet — and should be rare.
- Numbers in tables/KPIs: `tabular-nums`. Codes/IDs/JSON: `font-mono`.
- Type scale: page title 18/semibold, card title 14/semibold, body 13, table 12.5, caption 11. Line-height 1.4–1.5.

## 2. Dependencies (exact additions, pinned by lockfile)

| Package | Purpose |
|---|---|
| `bits-ui` | Headless primitives under shadcn-svelte components |
| `tailwind-variants`, `clsx`, `tailwind-merge` | Component variants + class merging (`cn()` util) |
| `@lucide/svelte` | Icons |
| `svelte-sonner` | Toasts |
| `@fontsource-variable/inter`, `@fontsource/jetbrains-mono` | Fonts |

Install via `npx shadcn-svelte@latest init` (style: default, base color: slate, css: `src/routes/layout.css`, alias `$lib/components/ui`) then `npx shadcn-svelte@latest add <component>` for the curated set below. If the CLI is unavailable offline, vendor the components manually from the docs — same file layout.

## 3. Component inventory

### 3.1 Vendored via shadcn-svelte → `src/lib/components/ui/`

`button`, `input`, `textarea`, `select`, `checkbox`, `switch`, `label`, `badge`, `card`, `tabs`, `dialog`, `alert-dialog`, `dropdown-menu`, `tooltip`, `separator`, `skeleton`, `table`, `sheet` (drawer), `breadcrumb`, `sonner` (toaster mount), `scroll-area`, `collapsible`.

Do not add others without a decision entry. Variants used: button `default | secondary | outline | ghost | destructive`, sizes `sm | default`; badge variants replaced by StatusBadge below for statuses.

### 3.2 App-level components → `src/lib/ui/`

| Component | API (props) | Behavior spec |
|---|---|---|
| `AppShell.svelte` | `children` snippet | Grid: sidebar + (topbar / main). Sidebar state in `localStorage('oscar.sidebar')`. |
| `SideNav.svelte` | — | Groups per PRD §5; icons: LayoutDashboard, FileSearch (Decisions), SquareFunction (Rules), Table2, GitBranch (Strategies), BookOpen (Features), Boxes (Models), FlaskConical (Simulations), Inbox (Manual Review), ScrollText (Audit), Settings2 (Admin). Active = `bg-primary-50 text-primary-700` left-border 2px. Keeps `data-testid="main-nav"`. |
| `TopBar.svelte` | — | Breadcrumbs (from `breadcrumbs` store set by pages via `setBreadcrumb(entityLabel)`), DEMO badge, user `DropdownMenu` (name, roles, Sign out). |
| `PageHeader.svelte` | `title, description?, actions?` snippet | H1 18/semibold + muted description; actions right-aligned; bottom margin 16px. |
| `StatusBadge.svelte` | `value: string` | Looks up `status.ts` map → `{label, tone, icon}`. Tones: success (ACTIVE, APPROVE, APPROVED*, RECEIVED), warning (PENDING_APPROVAL, MANUAL_REVIEW, IN_REVIEW, PENDING_DOCUMENTS, APPROVE_WITH_CONDITION), danger (REJECT, REJECTED*, BREACHED, FAIL, ERROR), info (DRAFT, NEW, ASSIGNED, SIMULATION), special (FRAUD_INVESTIGATION, ESCALATED, OVERRIDE), neutral (RETIRED, SKIP, everything unknown). Unknown values render neutral with raw text — never throw. Unit test asserts every enum string in `types.ts` statuses resolves. |
| `DataTable.svelte` | `columns: Column[]`, `rows: T[]`, `loading?`, `empty?: {title, hint?, actionLabel?, onAction?}`, `onRowClick?`, `rowKey` | `Column = {key, header, sortable?, align?: 'left'\|'right', width?, cell?: Snippet}`. Client-side sort only on `sortable` columns (toggle asc/desc, ChevronUp/Down indicator). Sticky header (`bg-surface-sunken`), row hover `bg-surface-muted`, 40px rows. `loading` renders 8 skeleton rows. Empty renders `EmptyState`. |
| `EmptyState.svelte` | `icon?, title, hint?, actionLabel?, onAction?` | Centered, 48px icon in muted circle, CTA button optional. |
| `FilterBar.svelte` | `children` snippet, `onReset?` | Horizontal wrap of controls in a `bg-surface` card; Reset ghost button right. |
| `ConfirmDialog.svelte` | exported `confirmAction({title, body?, confirmLabel, tone?: 'danger'\|'default', requireReason?: boolean}) : Promise<{ok: boolean, reason?: string}>` | Singleton mounted in layout; wraps `alert-dialog`; when `requireReason`, confirm disabled until textarea non-empty. Replaces every `window.confirm`. |
| `VersionTimeline.svelte` | `versions: {id, version, status, note?}[]`, `selectedId`, `onSelect` | Vertical list; each row: `v{n}` mono, StatusBadge, note truncated; selected ring-primary. |
| `KpiCard.svelte` | `label, value, delta?, deltaDirectionGood?: 'up'\|'down', loading?` | Value 24/semibold tabular; delta arrow colored by whether direction is good. |
| `TraceTimeline.svelte` | `steps: TraceStep[]` | Vertical timeline: status dot (success/danger/warning), step name, duration right-aligned mono, chevron expands raw detail (`JsonBlock`). Keeps/absorbs `data-testid="trace-steps"`. |
| `DiffView.svelte` | `before: unknown, after: unknown` | Flatten both to dot-path map; render table of Field / Before / After for changed+added+removed only, colored `danger-bg`/`success-bg`; if either side isn't a plain object, fall back to two `JsonBlock`s. Pure util `flattenDiff()` in `src/lib/ui/diff.ts` + unit tests. |
| `RelativeTime.svelte` | `value: string` | "3m ago / 2h ago / Jul 12, 14:03"; full ISO in `title`. Util + unit test. |

### 3.3 Existing components: disposition

| Component | Action |
|---|---|
| `Badge` | Replaced by `StatusBadge` (keep file as thin re-export during FR2, delete in FR6) |
| `Card` | Replaced by ui/card; migrate call sites per page as touched |
| `ErrorNote` | Restyle with danger tokens + AlertTriangle icon; API unchanged |
| `JsonBlock`, `SqlPreview`, `Pagination`, `FeaturePicker` | Restyle only |
| `ConditionBuilder`, `BranchEditor`, `ActionListEditor`, `ExpressionEditor` | Restyle internals with ui primitives; props unchanged; logic untouched |

## 4. Interaction standards

- **Toasts** (svelte-sonner, top-right): success `"<Object> saved"` / `"Submitted for approval"` / `"Version activated"`; error toast carries `ApiError.message`. Every `await api(...)` mutation path in routes ends with a toast.
- **Buttons**: one primary per view region; destructive actions use `destructive` variant and `ConfirmDialog`; in-flight actions disable + `Loader2` spin icon.
- **Forms**: labels always visible (no placeholder-as-label); inline error text `text-danger text-xs` under field; submit disabled while invalid where cheap.
- **Loading**: route-level skeletons (cards/table) — never a bare "Loading…" string.
- **Focus**: `focus-visible:ring-2 ring-primary-500 ring-offset-1` on all interactive elements (comes with vendored components; custom controls must match).
- **Canvas node colors** (StrategyNode): START/END neutral, VALIDATION info, CALCULATION special, RULE_SET primary, SCORECARD warning, DECISION_TABLE success, CONDITION amber diamond — 3px left accent + icon, tokens only.

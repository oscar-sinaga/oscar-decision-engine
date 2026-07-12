# 04 — Screen-by-Screen Redesign Spec

Format per route: **Keep** (must not change) / **Target** (what to build). All data sources and API calls stay identical. "PH" = PageHeader, "FB" = FilterBar, "DT" = DataTable, "ES" = EmptyState.

## /login
- Keep: form labels `Username`/`Password`, button `Sign in` (Playwright).
- Target: centered card on `surface-muted`, OSCAR wordmark, subtle description, error via restyled ErrorNote, demo-accounts hint collapsible.

## Shell (all authenticated routes)
- Keep: `data-testid="main-nav"`, nav label texts, sign-out capability.
- Target: PRD §5 IA. Sidebar 240px (icon rail 56px collapsed; drawer <768px). Topbar: breadcrumbs via `setBreadcrumb()`, DEMO badge, user dropdown. Content `max-w-[1440px] mx-auto p-6`.

## /dashboard (FR3)
- Keep: KPI figures' data sources; any testids present.
- Target: PH "Dashboard" + date-range filter (existing param). Row 1: 4 KpiCards (Decisions, Approval rate, Manual review rate, Error rate). Row 2: decision-mix stacked bar + top-5 reason codes list (count + % bar). Row 3: score-distribution bars + recent decisions mini-DT (5 rows, link to /decisions). Manual-review SLA snapshot card if data available. Per-card skeleton + per-card ErrorNote.

## /decisions (FR2)
- Target: PH "Decisions"; FB: existing filters (application id, decision, dates) restyled; DT columns: Application (mono, sortable), Decision (StatusBadge), Reason codes (first + `+n` tooltip), Strategy version (mono), Latency ms (right, tabular), Created (RelativeTime, sortable). Row click → detail. ES: "No decisions match these filters".

## /decisions/[id] (FR4)
- Keep: `data-testid="decision-summary"`, `trace-steps` content contract, "View executed flow" link.
- Target: PH = application id + StatusBadge; summary as 3 cards (Decision & reasons / Application snapshot / Runtime: strategy version, latency, correlation id — all mono). Trace via `TraceTimeline` (expandable steps). Tab or section for raw trace JSON (JsonBlock) for auditors.

## /rules (FR2)
- Target: PH "Rules" + `New rule` primary (permission-gated as today); FB: category select + search input (client filter on code/name); DT: Code (mono), Name, Kind, Category, Active version, Status (StatusBadge), Updated. Row click → detail. ES CTA → /rules/new.

## /rules/new + /rules/[id] (FR4)
- Keep: all builder/editor component props and flows; test form; usage panel; SQL preview; JSON advanced; expression gating.
- Target: two-column: left = editor (Tabs: Builder / SQL preview / Advanced JSON / Test); right sticky rail: metadata card (code, name, kind, category), `VersionTimeline`, lifecycle actions, "Used by" panel. Branch cards: WHEN header strip (`surface-sunken`), THEN actions as chips/rows, ELSE card visually distinct. Inline validation text under invalid inputs.

## /decision-tables (FR2)
- Target: PH + New table; DT: Code, Name, Hit policy, Active version, Status, Updated. ES CTA.

## /decision-tables/[id] (FR4)
- Keep: `data-testid="decision-table-grid"`, all grid editing logic, overlap warnings, lifecycle.
- Target: PH = code + StatusBadge + version picker (VersionTimeline in right rail or dropdown). Toolbar above grid: Add row, Add column, hit-policy chip, Validate, Save. Grid: frozen header + first column, 36px rows, wildcard cells show `∗` mono on `surface-sunken`, invalid/overlap rows tinted `warning-bg` with inline message row. Lifecycle actions in sticky footer bar.

## /features (FR2, light FR4)
- Target: PH "Feature Catalog" + New feature; FB: category/type/writable filters; DT: Path (mono), Label, Type, Source, Writable (Check icon), Status, Updated. Create/edit in `Sheet` (drawer) instead of inline block — same fields/validation.

## /strategies (FR2)
- Target: PH + New strategy; DT: Code (mono), Name, Product/Segment, Active vN, Latest status (StatusBadge), Updated.

## /strategies/[id] (FR4)
- Keep: everything from commit `1e60613` — canvas behavior, node panel deep-links, edge inspector, draft flow, all testids (`strategy-flow-canvas`, `graph-issues`, `node-rule-links`, `node-open-table`, `edge-config`, `readonly-note`).
- Target layout: PH = strategy code + StatusBadge + version dropdown (replaces Versions card); lifecycle actions in a sticky action bar under PH (Save draft / Save as new version / Validate / Auto-layout / Submit; approve/reject/rollback per status). Canvas fills remaining viewport height (`calc(100vh - shell - header)`, min 560px). Palette = left collapsible panel (icons + labels); inspector = right 320px collapsible panel. Node styling per design-system §4 canvas colors. Issues panel renders as dismissible banner over canvas bottom.

## /simulations + /simulations/batch (FR2/FR4)
- Keep: forms, payload textarea flows, batch compare data.
- Target: PH "Simulations" + Tabs (Single / Batch). Single: form card left (payload JSON with mono textarea + validate hint), result right: decision StatusBadge hero, reason codes, TraceTimeline. Batch: setup card, then results: two aggregate cards side-by-side (target vs baseline) with rate deltas colored, shifts DT (From → To with arrow, count, right-aligned), segment impact DT. ES for "no simulations yet".

## /models (FR2)
- Target: PH "Model Registry" + Register model; DT: Name (mono), Version, Status, Owner, Registered (RelativeTime). Detail stays inline/drawer as today, restyled.

## /manual-review (FR2)
- Target: PH "Manual Review"; FB: status/priority/assignee; DT: Case (mono), Application, Priority (StatusBadge special/warning), Status, SLA deadline (RelativeTime; `text-danger` + AlarmClock icon when breached, sortable), Assigned to. Row click → case.

## /manual-review/[id] (FR4)
- Keep: all actions (assign, comment, request documents, checklist toggle, escalate, decide), guardrails, decided lock.
- Target: PH = case id + StatusBadge + SLA countdown chip. Two columns: **left (evidence)** — application summary card (masked values as today), system decision card (StatusBadge + reasons + trace link), documents checklist card (received/waived toggles); **right (work)** — actions row (Assign to me / Escalate / Request documents via Dialog), comments timeline (newest last, author + RelativeTime), decision form card (selects, limit/tenor inputs, reason-code select, override-reason textarea that appears with inline explanation when decision ≠ system decision). Decided case: form replaced by verdict summary card (side-by-side system vs analyst).

## /audit (FR5)
- Target: PH "Audit Log"; FB: event type, entity type, entity id, actor, date range; DT: Time (RelativeTime, sortable), Event (mono), Entity (type + id mono), Actor, Reason (truncated). Row click → `Sheet` with full metadata + `DiffView(before, after)` + correlation id (mono, copy button).

## /admin (FR5)
- Keep: approve/reject flows, self-approval error surfaced, role editing.
- Target: PH "Admin"; Tabs: **Approvals** (inbox cards: type icon, object code mono, vN, requester, note, evidence link if simulation attached, Approve primary + Reject destructive — both via ConfirmDialog with `requireReason`), **Users** (DT: username mono, name, role chips, Edit → Dialog with checkboxes), **Roles** (permission matrix in scroll-area card, Check icons).

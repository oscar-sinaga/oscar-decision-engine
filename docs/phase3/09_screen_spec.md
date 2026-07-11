# Phase 3 Screen Specification

Design language unchanged (Tailwind, dense internal workbench, existing `Card`/`Badge`/`ErrorNote` components). Frontend permission checks remain UX-only; the backend is the security boundary. **Success bar for every screen: the target persona completes the task without seeing JSON.**

## 1. Rule Editor v2 (`/rules/new` and builder-first `/rules/[id]`)

Layout: two columns — left = authoring, right = live previews.

### 1.1 General information
Code, name, description, **category (from meta `rule_categories`)**, **rule kind** (POLICY_OUTCOME/STATEMENT/CLASSIFICATION; EXPRESSION visible only with `rule.author_expression`), version note.

### 1.2 Condition builder v2 (shared component; also used by CONDITION nodes and the grid editor)
- **Nested groups**: a group = ALL/ANY toggle + rows + "Add condition" + "Add group" (recursion; indented card per depth, `NOT` toggle per group). Max depth 5 (UI); server accepts deeper.
- **Feature picker**: searchable combobox (filter by path/label/category as user types; sections: Payload / Derived / Score / Outputs; shows `data_type` chip). Data from `/v1/meta` `features[]`.
- **Typed operators**: options = `operators_by_type[feature.data_type]`.
- **Typed value input**: NUMBER→`<input type=number>`; STRING→text (`in`/`not_in`→tag-list input); BOOLEAN→true/false select; DATE→date picker; `exists`/`is_null`→no input. No more "JSON value" free-text.

### 1.3 Branch editor (CASE WHEN)
- Ordered branch cards: "WHEN [condition builder] THEN [action list]"; add/remove/reorder (up/down buttons); collapse header shows human-readable summary.
- **Action list** per branch: rows of action type dropdown + typed fields — `SET_OUTPUT`: output picker (meta `writable_outputs`) + typed value input (or expression textarea if permitted); `SET_DECISION`: decision + reason-code selects; `ADD_REASON_CODE`; `STOP_EXECUTION`; etc.
- **ELSE section** (optional toggle) with its own action list.
- Simple mode: rule kind POLICY_OUTCOME defaults to 1 branch + decision action — the current UX remains the easy path.

### 1.4 Previews (right column, always visible, live)
- **Human-readable**: `WHEN saving_account_balance > 50.000.000 → vehicle_price_band = 20.000` … `ELSE → vehicle_price_band = 0`.
- **SQL-style** (tab): rendered per `05_expression_language.md` §6 with banner "Preview only — OSCAR never executes SQL".
- **Advanced (JSON)** (tab): read-only pretty JSON + "Edit as JSON" escape hatch (existing behavior, demoted).

### 1.5 Builder-first detail page (`/rules/[id]`)
- Stored definition **parses into builder state** for DRAFT editing and read-only display of any version (parser in `frontend/src/lib/rule-format.ts`: JSON↔builder-state, round-trip tested).
- If a stored shape exceeds builder capability (deep nesting, expression rule without permission): read-only previews + JSON tab; edit disabled with explanation.
- **Generated test form** replaces the raw JSON textarea: one typed input per feature referenced by the rule (prefilled from a sample), Run → shows matched branch, per-condition ✓/✗ (existing display), actions applied, outputs_after.
- **Used by** panel: from `GET /v1/rules/{id}/usage` — rule sets, strategies (+versions, active badge); warning banner on retire when `active_version_uses`.
- Lifecycle buttons unchanged (submit/approve/reject/retire/new draft).

### 1.6 Expression editor (rule kind EXPRESSION; admin-gated)
Monospace textarea; debounced `POST /v1/expressions/validate` → inline status (✓ inferred type / ✗ line:col message); "Insert feature" opens the feature picker (inserts path at cursor); output target picker (writable outputs); previews as §1.4.

## 2. Strategy Flow Canvas (`/strategies/[id]` replaces the step list; new dependency `@xyflow/svelte`, pinned)

- **Canvas**: Svelte Flow; custom node component per `node_type` (icon + name + reference badge + on_error chip; CONDITION = diamond styling; START/END = pills). Edges: smoothstep arrows; TRUE edge green label, FALSE red.
- **Palette** (left rail): drag node types onto canvas (START/END auto-managed: START placed on new draft, END addable).
- **Node config drawer** (right, on select): VALIDATION→required-fields multi-select (catalog); CALCULATION→derived-calcs multi-select; RULE_SET/SCORECARD/DECISION_TABLE→searchable reference select + on_error; CONDITION→**condition builder v2** (§1.2); name field for all.
- **Connect rules enforced in-UI** (and revalidated server-side): CONDITION exposes two source handles (TRUE/FALSE); other nodes one; connecting an occupied handle replaces its edge after confirm.
- **Validation**: on Save (and on demand) run client pre-checks + server errors mapped back → offending nodes/edges outlined red + issue list panel.
- **Read-only mode** for PENDING/ACTIVE/RETIRED versions (pan/zoom only) — also used by the trace screen link "view flow".
- **Auto-layout** button (simple layered left-to-right; migrated linear flows already carry positions).
- Lifecycle bar unchanged: version list, submit (with simulation attach — existing flow), activate/reject/rollback.
- Empty draft starts with START node; "Start from active version" copies the active graph.

## 3. Decision Table Grid Editor (`/decision-tables` + `/decision-tables/[id]`, replacing JSON editing)

- **List page**: code, name, active/latest version, status (mirrors rules list).
- **Grid editor** (draft versions): columns = condition inputs (add column → feature picker incl. `outputs.*`; per-column operator default `=`, editable per cell) + output columns (decision, risk_grade, approved_limit, approved_tenor_months, pricing_rate, reason_code — shown as typed cells); rows = add/duplicate/delete/reorder; cell inputs typed as §1.2; blank condition cell = "any" (renders `*`).
- **Hit policy** selector (FIRST_MATCH / PRIORITY; PRIORITY shows a priority column).
- **Overlap warnings** from the version response render as row badges + banner (non-blocking, matching backend behavior).
- Human-readable row summary on hover; JSON tab demoted as in rules; lifecycle buttons unchanged.

## 4. Catalog screens (extend existing)

- **Feature Catalog** (`/features`): + `writable` toggle chip + column; create form gains writable + source RULE_OUTPUT; filter "Outputs only".
- **Rule categories**: small management section (list/add/deactivate) — **placed on the `/features` page as a second card** (decided; do not put it on `/admin`).

## 5. Trace screen additions (`/decisions/[id]`)

- Timeline entries show `node_key`; CONDITION entries render "Condition: <human-readable> → TRUE/FALSE".
- Rule results show matched branch ("branch 2 of 3" / "ELSE") and `actions_applied` list incl. outputs written.
- New "Outputs" card (trace `outputs` snapshot).
- "View flow" link → read-only canvas of the executed version.

## 6. Vitest / Playwright expectations (detail in `10_test_plan.md`)

Vitest: rule-format round-trip (JSON↔builder), sql-preview renderer parity cases, graph serialization helpers. Playwright: the PRD §6 journey (catalog → statement rule → classification rules → grid table → canvas with condition → govern → decide → trace), plus expression-permission denial.

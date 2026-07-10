# Phase 3 Scope & Sub-phase Breakdown

## 1. Scope decisions (product owner, 2026-07-11)

| Decision | Choice |
|---|---|
| Old docs/05 Phase 3 roadmap | **Removed entirely** (fraud monitoring, champion/challenger, model monitoring, drift, portfolio/vintage, collection integration). Recorded in ADR-012; not carried as backlog. |
| Flow canvas ambition | **Option C — Full DAG** with condition nodes and labeled branches (iDecision-style), single-token deterministic traversal |
| "Free SQL" | **Option B — Safe expression language + SQL-style preview**, admin-gated. Raw SQL execution stays forbidden |
| Decision-table grid editor | **In scope this phase** |

## 2. In scope — sub-phases

Execute strictly in this order (each = one coherent local commit with tests, migrations, docs sync):

| Sub-phase | Title | Depends on | Summary |
|---|---|---|---|
| **P3.1** | Rule Model v2 (engine) | — | CASE WHEN `branches[]` + `default` (ELSE), multi-action `then[]`, `SET_OUTPUT` with catalog enforcement, typed-operator validation, `rule_kind`, full back-compat with legacy `{condition, action}` |
| **P3.2** | Catalogs & metadata | P3.1 | `features.writable` (output catalog) + seeds, `rule_categories` table, meta additions (operators-by-type, kinds, node types, outputs, categories), `GET /v1/rules/{id}/usage` |
| **P3.3** | Rule authoring UX overhaul | P3.1–2 | Builder v2: nested AND/OR groups, searchable typed feature picker, typed operators/value inputs, branch/ELSE editor, multi-action editor, human-readable preview, **builder-first detail page** (JSON → "Advanced" tab), generated typed test form, usage panel |
| **P3.4** | DAG execution engine | P3.1 | `strategy_nodes`/`strategy_edges` model + validator + graph executor + path trace; Alembic **data migration** converting existing linear strategies; legacy `steps[]` API accepted and converted; plan-builder/simulation/activation checks updated; golden reproducibility tests |
| **P3.5** | Visual flow canvas | P3.4 | Svelte Flow (`@xyflow/svelte`) canvas: palette, node config drawer, condition-node editing, validation surfacing, draft editing + read-only active view, auto-layout for migrated flows |
| **P3.6** | Expression language + SQL-style preview | P3.1–2 | Tokenizer/parser → whitelisted AST, interpreter, limits, `rule.author_expression` permission, `POST /v1/expressions/validate`, expression editor UI, SQL-style preview renderer for **all** rules |
| **P3.7** | Decision-table grid editor | P3.2 | Typed grid editor over existing table API; inline overlap warnings; catalog-driven columns incl. rule outputs |
| **P3.8** | Hardening, E2E, docs sync | all | Full-stack rebuild, new Playwright flows (PRD §6), security fuzz suite green, update `docs/05/06/07/09/10`, ADRs, final report; `IMPLEMENTATION_STATUS.md` complete |

Rationale for order: engine foundations (P3.1) unblock everything; catalogs (P3.2) unblock typed UX; the authoring UX (P3.3) is independent of the graph work so it lands before the riskier P3.4; canvas (P3.5) needs the graph API; expression (P3.6) and grid (P3.7) are additive; P3.8 closes.

## 3. Stretch backlog (only after P3.1–P3.8 are complete and green; otherwise defer to Phase 4)

From the review's "Phase 2C" list, explicitly **not** required for Phase 3 completion:
- Rule templates / rule library (clone-from-template).
- Bulk rule import/export (file-based) — note: export is permission- and audit-bound per docs/18.
- Dependency **graph visualization** (usage endpoint ships in P3.2; the visual graph is stretch).
- Reusable named formulas (expression fragments shared across rules).
- Nested sub-flow nodes (a strategy node that invokes another strategy graph, like iDecision's "Decision Flow" component).

## 4. Out of scope (hard)

- Executing raw SQL (or any analyst-supplied string) against any database, in any environment.
- Parallel branches, joins-with-wait, loops, timers in flows.
- Changing governance semantics (maker-checker, simulation attachment, immutability, audit) — Phase 3 artifacts plug into them unchanged.
- External integrations, deployment promotion, and everything listed in PRD §3.

## 5. Compatibility guarantees (non-negotiable)

1. Legacy rule JSON `{condition, action}` validates and executes forever (normalized internally to v2).
2. Legacy strategy `steps[]` create/update payloads keep working (server-side conversion to a linear graph).
3. Existing decision traces remain readable in the UI; new traces add fields (`node_key`, `taken_edge`, `matched_branch`) without removing existing ones.
4. Seeded demo policy continues to produce identical decisions for the golden payload set (`10_test_plan.md` §5) after every migration.
5. The pre-existing 114 backend tests, 12 Vitest tests, and 4 Playwright tests keep passing (adapt assertions only where a spec change is documented in this pack).

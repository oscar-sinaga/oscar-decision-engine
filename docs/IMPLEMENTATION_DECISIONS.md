# Implementation Decisions

> Record material architectural, security, product-scope, and data-contract decisions. Do not record trivial coding choices.

## Decision Template

### ADR-XXX — Title

- **Date:** YYYY-MM-DD
- **Status:** Proposed / Accepted / Superseded
- **Context:**
- **Options considered:**
- **Decision:**
- **Reasoning:**
- **Consequences:**
- **Related documents/files:**

---

### ADR-001 — Backend toolchain: uv + Python 3.13

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** Spec requires Python `>=3.12,<3.15`; the system Python is 3.11. `docs/16` allows `uv` (preferred) or pip/venv.
- **Options considered:** (a) pip/venv with a manually installed 3.12+, (b) `uv` managing interpreter + lockfile.
- **Decision:** `uv` with CPython 3.13.12 pinned via `.python-version`; dependencies locked in `uv.lock`.
- **Reasoning:** `uv` provides the required interpreter without touching the system Python and produces a committed lockfile, satisfying the reproducibility policy.
- **Consequences:** All backend commands run through `uv run`; Docker image uses the same lockfile via `uv sync --frozen`.
- **Related documents/files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/Dockerfile`, `docs/16_dependency_version_policy.md`.

### ADR-002 — Auth/crypto dependencies: PyJWT + bcrypt instead of python-jose + passlib

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** `docs/15` lists `python-jose[cryptography]` and `passlib[bcrypt]` as _optional_ suggestions for later. JWT + password hashing are needed for RBAC.
- **Options considered:** (a) python-jose + passlib as suggested, (b) PyJWT + bcrypt directly.
- **Decision:** `pyjwt>=2,<3` and `bcrypt>=4,<6`. Also added `pydantic-settings>=2,<3` for typed env configuration (the pydantic-v2 companion package).
- **Reasoning:** passlib is unmaintained and incompatible with modern bcrypt releases; python-jose has a history of CVEs and slow maintenance. PyJWT and bcrypt are the actively maintained, minimal equivalents. The docs marked their suggestions optional, so this is an allowed deliberate choice, documented per the dependency policy.
- **Consequences:** Token encode/decode uses PyJWT API; password hashing uses `bcrypt` directly.
- **Related documents/files:** `backend/pyproject.toml`, `docs/15_tech_stack.md`, `docs/16_dependency_version_policy.md`.

### ADR-003 — Compose PostgreSQL exposed on host port 5455

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** Host port 5432 is already occupied by a pre-existing local PostgreSQL service on the development machine.
- **Decision:** The project's PostgreSQL 16 container maps `5455:5432`; all local defaults (`settings.py`, `alembic.ini`, `.env.example`) use 5455. Inside the compose network the backend still uses 5432.
- **Reasoning:** Avoids colliding with (or accidentally using) an unrelated local database — decisive for the "never touch non-project data" rule.
- **Consequences:** Developers connecting with external tools must use port 5455.
- **Related documents/files:** `docker-compose.yml`, `backend/app/shared/config/settings.py`, `backend/alembic.ini`.

### ADR-004 — Observability implementation: stdlib JSON logging + pure-ASGI correlation middleware

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** `docs/18` requires structured sanitized logs, request/correlation IDs on every response, and safe error envelopes. `docs/15`/`docs/16` prefer the standard library over new observability dependencies.
- **Options considered:** (a) `structlog`, (b) stdlib `logging` with a JSON formatter and `contextvars`.
- **Decision:** Stdlib logging with a custom `JsonLogFormatter` that redacts sensitive keys, plus a pure-ASGI `CorrelationMiddleware` that generates/propagates IDs, times requests, emits one structured log per request, and converts unhandled exceptions into the documented error envelope (exception _type_ only — never stack traces or messages) before they can leak.
- **Reasoning:** Meets every docs/18 requirement with zero added dependencies; pure ASGI avoids `BaseHTTPMiddleware` streaming pitfalls; redaction at the formatter guarantees no code path can log prohibited values unredacted.
- **Consequences:** All structured log fields pass through `app/shared/utils/masking.redact`; masking is deny-list based on key names and intentionally over-redacts (e.g. a `documents` key is masked entirely).
- **Related documents/files:** `backend/app/shared/logging/`, `backend/app/shared/utils/masking.py`, `docs/18_observability_and_audit_logging.md`.

### ADR-005 — Severity-based decision aggregation with conservative fallback

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** docs/10 defines rule actions and docs/03 §9 ordered steps, but not how multiple triggered actions combine into one final decision.
- **Options considered:** (a) last action wins, (b) explicit priority per rule, (c) fixed severity ordering over candidate decisions.
- **Decision:** Every triggered action contributes a candidate decision; the most severe candidate wins (ERROR > FRAUD_INVESTIGATION > REJECT > MANUAL_REVIEW > REQUEST_ADDITIONAL_DOCUMENT > APPROVE_WITH_CONDITION > APPROVE). If a strategy produces no candidate at all, the engine returns MANUAL_REVIEW with reason `NO_DECISION_PRODUCED`. Approval outputs (limit/tenor/pricing) attach only when the final decision is approve-like.
- **Reasoning:** Deterministic, explainable, order-independent within a step, and conservative: a fraud hit can never be silently out-voted by a downstream approval row. The fallback is engine mechanics, not credit policy — it only fires on misconfigured strategies.
- **Consequences:** Rules express _escalations_; a decision table (or rule) must still produce the approve path explicitly.
- **Related documents/files:** `backend/app/engine/executor.py`, `docs/10_rule_engine_design.md`.

### ADR-006 — Missing-required-field handling: structured 422, application recorded, no decision row

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** docs/02 §6.1 requires "structured validation error" for missing required data; required fields are configurable via VALIDATION strategy steps, not the API schema.
- **Decision:** The API envelope validates only shape (`application_id`, `product_type`); configurable VALIDATION steps check required feature paths. On failure the application row is stored with status ERROR, a `DECISION_VALIDATION_FAILED` audit event is committed, and the API returns the 422 `VALIDATION_ERROR` envelope listing missing fields. No decision/trace row is created.
- **Reasoning:** Keeps required-field policy configurable per strategy while satisfying the contract; the audit trail still shows the failed attempt.
- **Consequences:** Retrying with complete data creates a new application row (no dedup on external application_id by design in MVP).
- **Related documents/files:** `backend/app/modules/decisions/service.py`, `docs/07_api_contract.md`.

### ADR-007 — Trace immutability and audit-write guarantees enforced at the application layer

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** docs/11/§14 require immutable traces and no silent unaudited state changes.
- **Options considered:** (a) PostgreSQL triggers/rules blocking UPDATE/DELETE, (b) application-layer enforcement (no mutation paths + same-transaction audit writes) with tests.
- **Decision:** Application-layer enforcement for MVP: traces and audit logs have no update/delete code paths; audit events are staged in the same transaction as the state change, so either both commit or neither does (`AuditPersistenceError` semantics come free from transactional atomicity). DB-level triggers are deferred.
- **Reasoning:** Simplest implementation satisfying the MVP DoD; a DB-privilege/trigger hardening pass is an operational concern for deployment, noted for Phase 2 backlog.
- **Consequences:** Direct DB access could still mutate evidence; deployment must restrict DB credentials.
- **Related documents/files:** `backend/app/modules/audit/service.py`, `backend/app/modules/decisions/service.py`, `docs/18_observability_and_audit_logging.md`.

### ADR-008 — Manual review override semantics

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** docs/13 requires override reasons when the analyst decision differs from the system decision, and docs/14 grants `manual_review.override` to senior roles — but for a case created from a MANUAL_REVIEW system decision, _any_ analyst resolution differs from the system decision, which would make ordinary case work impossible for underwriters if override permission were always required.
- **Options considered:** (a) require `manual_review.override` for every differing decision, (b) treat resolving a MANUAL_REVIEW case as normal `manual_review.decide` work with a mandatory override reason, reserving `manual_review.override` for contradicting definitive system routing.
- **Decision:** (b): `manual_review.decide` resolves cases; whenever the analyst decision differs from the system decision an override reason is mandatory and a `MANUAL_REVIEW_OVERRIDDEN` audit event records before/after; approving a case whose system decision is FRAUD_INVESTIGATION additionally requires `manual_review.override`. Rejects always require a reason code.
- **Reasoning:** Preserves the documented separation of decide vs override permissions while keeping the underwriter queue workable; fraud contradiction is the genuinely high-risk override in MVP scope.
- **Consequences:** Underwriters resolve ordinary borderline cases; only RISK_MANAGER/ADMIN can approve fraud-routed cases. Supervisor approval flows remain Phase 2.
- **Related documents/files:** `backend/app/modules/manual_review/service.py`, `docs/13_manual_review_design.md`, `docs/14_audit_governance.md`.

### ADR-009 — Workbench runs as a client-side SPA against the FastAPI backend

- **Date:** 2026-07-04
- **Status:** Accepted
- **Context:** The workbench is an internal tool authenticated with bearer tokens; docs/15 allows SSR/SPA options via SvelteKit.
- **Options considered:** (a) SSR with server-side session handling and an API proxy, (b) SPA (`ssr = false`) calling the API directly with CORS.
- **Decision:** SPA mode. The token lives in localStorage, every request carries `Authorization: Bearer`, the backend allows the workbench dev/preview origins via CORS, and authorization remains enforced server-side (frontend permission checks are UX only). Node adapter retained for containerized serving.
- **Reasoning:** Removes duplicated auth plumbing for an internal tool, keeps the OpenAPI-backed FastAPI service the single security boundary, and simplifies Docker deployment.
- **Consequences:** No SSR data loading; a `/v1/meta` endpoint supplies registry/enum metadata for dropdowns and the condition builder.
- **Related documents/files:** `frontend/src/routes/+layout.ts`, `frontend/src/lib/api/client.ts`, `backend/app/main.py` (CORS), `backend/app/api/v1/meta.py`.

### ADR-010 — Feature catalog is the governed vocabulary; engine keeps computation

- **Date:** 2026-07-05
- **Status:** Accepted
- **Context:** MVP validated rule/strategy feature references against a static in-code registry (`app/engine/features.py`). Phase 2 (docs/05) calls for a Feature Catalog / Data Dictionary so risk users can govern the variable vocabulary without code changes.
- **Options considered:** (a) keep the static registry, (b) move everything (including derived-feature computation) into config, (c) DB-backed catalog for the _vocabulary_ while derived-feature _computation_ stays in code.
- **Decision:** (c). A `features` table governs which feature paths are valid plus their data type/source/description; rule and strategy (required-field) validation and `/v1/meta` query the active catalog. Derived-feature arithmetic (`compute_derived_feature`) remains engine mechanics in code, and CALCULATION steps still validate against `DERIVED_FEATURES` (the engine can only compute what it implements). The catalog is seeded to mirror the engine registry so existing seeded policy keeps validating.
- **Reasoning:** Keeps credit-policy vocabulary configurable and auditable (create/update emit audit events) without letting business users define arbitrary executable computation — consistent with the "no hardcoded policy, but engine mechanics in code" principle.
- **Consequences:** Adding a genuinely new _payload_ feature is now a no-code catalog entry; adding a new _derived_ feature still requires an engine change plus a catalog entry. Deactivating a feature blocks new/edited rules from using it but preserves historical rule versions.
- **Related documents/files:** `backend/app/modules/features/`, `backend/app/modules/rules/service.py`, `backend/app/modules/strategies/service.py`, `backend/app/api/v1/meta.py`, `docs/06_data_model.md`.

### ADR-011 — Full maker-checker requires attached simulation evidence for strategy activation

- **Date:** 2026-07-05
- **Status:** Accepted
- **Context:** docs/14 §6 lists "simulation result attached" among the pre-activation approval requirements. MVP maker-checker (ADR, Phase 9) enforced approver≠maker but not simulation evidence.
- **Decision:** A strategy version's submit-for-approval accepts a `simulation_id`; the service verifies that simulation targeted the exact version and stores its display id as `approval_requests.simulation_ref`. Activation checks (after permission, maker-checker, and reference-activatable checks) that the pending approval request carries a `simulation_ref`, else returns 409. Enforcement is on strategies only (you simulate strategies, not individual rules/tables) and is toggleable via `OSCAR_REQUIRE_STRATEGY_SIMULATION_BEFORE_ACTIVATION` (default true).
- **Reasoning:** Gives approvers concrete impact evidence before a policy goes live, matching the documented governance flow, without over-constraining rule/table/scorecard versioning. Ordering activation checks so reference-activatability is validated first keeps existing "inactive reference" behavior and error codes stable.
- **Consequences:** Activating a strategy now requires a prior simulation of that version; the workbench submit flow auto-runs one when the analyst does not paste an existing SIM id.
- **Related documents/files:** `backend/app/modules/strategies/service.py`, `backend/app/modules/governance/service.py`, `backend/app/modules/governance/models.py`, `docs/14_audit_governance.md`.

### ADR-012 — Phase 3 scope replaced: Generic Rule Authoring & Visual Decision Flow

- **Date:** 2026-07-11
- **Status:** Accepted (product owner decision)
- **Context:** Benchmarking against IDX iDecision showed OSCAR's rule model is outcome-bound (rule → decision + reason code), authoring is JSON-first, and strategies are linear — while iDecision rules generically produce values/classifications consumed by later steps, and flows are designed on a branching node canvas. An external review confirmed the gaps. The original Phase 3 roadmap (fraud monitoring, champion/challenger, model/drift monitoring, portfolio/vintage, collection integration) no longer matched product priorities.
- **Options considered:** (a) keep old Phase 3 roadmap; (b) incremental UX-only fixes; (c) full re-scope to a generic rule engine: rule model v2, catalogs, builder-first UX, DAG flows + canvas, safe expression language, decision-table grid.
- **Decision:** (c). Old Phase 3 items are **removed** (not backlogged). Three explicit design choices by the product owner: flow canvas = **full DAG with condition branching** (single-token deterministic traversal, no parallelism/loops); "free SQL" = **safe expression language + display-only SQL-style preview, admin-gated** (raw SQL execution remains forbidden — complies with AGENTS.md "safe structured expressions"); decision-table **grid editor included**. Two AGENTS.md scope amendments recorded: the visual drag-and-drop canvas is now in scope; expression language supersedes the "no free SQL" product gap without violating the engineering rule.
- **Reasoning:** Verified code facts show the engine already carries the seeds of the generic model (nested condition trees; `SET_ATTRIBUTE` writing to the feature context at `engine/executor.py:252`), so the re-scope formalizes and exposes existing capability rather than rebuilding; determinism/audit guarantees are preserved by validated-acyclic graphs and a whitelist-parsed expression AST.
- **Consequences:** Authoritative spec pack created at `docs/phase3/` (PRD, scope, architecture, DSL v2, expression spec, data model incl. `strategy_steps` → nodes/edges data migration, API contract, screens, test plan incl. golden reproducibility + security fuzz gates, execution plan P3.1–P3.8, agent execution prompt, status tracker). ADR-013 (canvas dependency) and ADR-014 (expression implementation) to be recorded during implementation.
- **Related documents/files:** `docs/phase3/*`, `docs/05_mvp_scope.md` (Phase 3 section replaced), `AGENTS.md`, `backend/app/engine/{dsl,executor}.py`.

### ADR-013 — Visual decision-flow canvas uses pinned Svelte Flow

- **Date:** 2026-07-11
- **Status:** Accepted
- **Context:** P3.5 requires a maintained Svelte-native node canvas with custom nodes, handles, pan/zoom, edge routing, and controlled serialization. Building these interaction primitives in-house would add substantial accessibility and geometry risk.
- **Options considered:** (a) bespoke SVG/HTML canvas, (b) generic diagram library, (c) `@xyflow/svelte`.
- **Decision:** Use `@xyflow/svelte` pinned exactly at `1.6.2`; persist only OSCAR's own graph DTO, never library-internal state.
- **Reasoning:** Svelte Flow provides the required interaction primitives while the serializer boundary keeps the backend contract independent from a UI library. Exact pinning prevents an unreviewed canvas API change from entering through a floating range.
- **Consequences:** Flow nodes/edges are converted through `frontend/src/lib/flow/serializers.ts`; upgrade work must include serializer and canvas regression tests. Non-draft versions disable mutation but retain pan/zoom.
- **Related documents/files:** `frontend/package.json`, `frontend/src/lib/flow/`, `frontend/src/routes/strategies/[id]/+page.svelte`, `docs/phase3/09_screen_spec.md`.

### ADR-014 — OSCAR Expressions use a hand-written parser and interpreted AST

- **Date:** 2026-07-11
- **Status:** Accepted
- **Context:** P3.6 requires expression-level authoring comparable to familiar SQL-style policy tools, while OSCAR's security constraints permanently prohibit raw SQL execution, Python `eval`/`exec`, and unrestricted code execution.
- **Options considered:** (a) execute user-authored SQL, (b) translate expressions into Python and evaluate them, (c) define a small whitelisted language parsed into a persisted JSON AST and interpreted in-process.
- **Decision:** Use option (c). `backend/app/engine/expression.py` implements a tokenizer, recursive-descent parser, static type/feature validation, hard complexity limits, JSON AST serialization, revalidation at execution, and a pure tree-walking interpreter. Expression authoring is gated by `rule.author_expression` (ADMIN); already-approved expressions execute without an extra runtime permission. SQL output is a display-only renderer and is never parsed or executed.
- **Reasoning:** The AST boundary makes the executable surface explicit and auditable, preserves original text plus a reproducible compiled form, supports deterministic NULL semantics, and provides useful power without ambient access to Python, the database, filesystem, network, time, or randomness.
- **Consequences:** Only catalog identifiers and the documented operators/functions are available. New language features require parser, validator, interpreter, renderer, fuzz, and compatibility tests. Runtime expression failures follow the existing strategy-node `on_error` path and store safe error classes rather than payload values.
- **Related documents/files:** `backend/app/engine/expression.py`, `backend/app/engine/preview.py`, `backend/app/api/v1/expressions.py`, `frontend/src/lib/components/ExpressionEditor.svelte`, `docs/phase3/05_expression_language.md`.

### ADR-015 — Frontend redesign system choices D1–D10

- **Date:** 2026-07-12
- **Status:** Accepted and implemented
- **Context:** Phase 3 made the Workbench substantially more capable, but its hand-styled presentation, flat navigation, silent mutations, and inconsistent loading/empty/governance states no longer matched the trust and productivity needs of risk analysts, managers, underwriters, auditors, and data scientists. The redesign had to improve interaction quality without changing backend behavior, routes, filters, query parameters, or test contracts.
- **Decision:** Adopt the ten decisions from `docs/frontend-redesign/01_ux_research.md` as one coherent frontend architecture:
  1. **D1 Component strategy:** vendor the curated official shadcn-svelte source set on bits-ui; keep OSCAR application components separately readable in-repo.
  2. **D2 Visual language:** neutral semantic surfaces, indigo primary actions, status-specific tone tokens, 8px cards, 6px controls, and border-led elevation.
  3. **D3 Typography:** Inter Variable for UI, JetBrains Mono for codes/JSON, compact enterprise type scale, and tabular figures.
  4. **D4 Navigation IA:** group unchanged routes into Monitor, Author, Operate, and Govern, with responsive sidebar behavior.
  5. **D5 Page patterns:** compose routes from PageHeader, FilterBar, DataTable/content, Drawer/Sheet, Dialog/ConfirmDialog, skeleton/empty/error states, and mutation toasts.
  6. **D6 Lifecycle UX:** render versions and outcomes through VersionTimeline and the icon-plus-label StatusBadge map rather than color alone.
  7. **D7 Canvas layout:** make the strategy canvas the full-height primary workspace, with collapsible palette/inspector and sticky governance actions.
  8. **D8 Dark mode:** structure tokens for a future override but defer the mode toggle to FR7.
  9. **D9 Charts:** use lightweight CSS/SVG presentation for current monitoring needs and avoid a chart dependency.
  10. **D10 Responsiveness:** optimize for desktop/laptop work, collapse navigation progressively, and contain editor overflow within panels rather than redesign domain tools for mobile.
- **Reasoning:** The selected approach establishes one visual and interaction grammar while keeping the verified Svelte 5 domain logic intact. Vendored primitives make accessibility behavior inspectable and stable; semantic tokens prevent page-level palette drift; shared application components reduce repeated implementation; and retaining all route/API/test contracts limits regression risk.
- **Consequences:** `frontend/src/lib/components/ui` is registry-owned source and should be reconciled through the shadcn-svelte CLI in reviewed batches. OSCAR-specific behavior belongs in `frontend/src/lib/ui` or route/domain components. New routes should use semantic tokens and shared page patterns. Every mutation needs feedback, destructive/governance actions require controlled confirmation, and browser validation remains a required workstation gate before integration. Dark mode, command palette, saved filters, and density controls remain deferred under FR7.
- **Related documents/files:** `docs/frontend-redesign/*`, `frontend/components.json`, `frontend/src/routes/layout.css`, `frontend/src/lib/components/ui/*`, `frontend/src/lib/ui/*`, `frontend/src/routes/**`, `frontend/e2e/*`.

## Tencent HTTPS workspace — 2026-11-09

Operator explicitly authorized deployment to the existing 2-vCPU/4-GB VPS. Preserve its PostgreSQL and protected services; add a dedicated database/role, pool 3+1, API 192 MiB and web 96 MiB. Serve under /workspaces/decision-engine with ACC owner gating plus application JWT/RBAC. Patch devalue 5.9.4 without framework major changes. Generate secrets on the server and override the public development seed password. See [TENCENT_VPS.md](TENCENT_VPS.md). Local commits only; no GitHub push authorized by this exception.

## Authorized GitHub synchronization (2026-11-09)

The operator explicitly requested all new application/VPS changes be committed and pushed to GitHub. This authorizes a normal fast-forward push of the tested deployment changes plus this documentation update to main, overriding the earlier local-only restriction for this task. Verify GitHub, local and VPS source HEADs match after synchronization. The running application image remains based on code revision 7cccd6f; this follow-up changes documentation only. No service restart or database change is required.

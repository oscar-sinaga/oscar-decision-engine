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
- **Context:** `docs/15` lists `python-jose[cryptography]` and `passlib[bcrypt]` as *optional* suggestions for later. JWT + password hashing are needed for RBAC.
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
- **Decision:** Stdlib logging with a custom `JsonLogFormatter` that redacts sensitive keys, plus a pure-ASGI `CorrelationMiddleware` that generates/propagates IDs, times requests, emits one structured log per request, and converts unhandled exceptions into the documented error envelope (exception *type* only — never stack traces or messages) before they can leak.
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
- **Consequences:** Rules express *escalations*; a decision table (or rule) must still produce the approve path explicitly.
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
- **Context:** docs/13 requires override reasons when the analyst decision differs from the system decision, and docs/14 grants `manual_review.override` to senior roles — but for a case created from a MANUAL_REVIEW system decision, *any* analyst resolution differs from the system decision, which would make ordinary case work impossible for underwriters if override permission were always required.
- **Options considered:** (a) require `manual_review.override` for every differing decision, (b) treat resolving a MANUAL_REVIEW case as normal `manual_review.decide` work with a mandatory override reason, reserving `manual_review.override` for contradicting definitive system routing.
- **Decision:** (b): `manual_review.decide` resolves cases; whenever the analyst decision differs from the system decision an override reason is mandatory and a `MANUAL_REVIEW_OVERRIDDEN` audit event records before/after; approving a case whose system decision is FRAUD_INVESTIGATION additionally requires `manual_review.override`. Rejects always require a reason code.
- **Reasoning:** Preserves the documented separation of decide vs override permissions while keeping the underwriter queue workable; fraud contradiction is the genuinely high-risk override in MVP scope.
- **Consequences:** Underwriters resolve ordinary borderline cases; only RISK_MANAGER/ADMIN can approve fraud-routed cases. Supervisor approval flows remain Phase 2.
- **Related documents/files:** `backend/app/modules/manual_review/service.py`, `docs/13_manual_review_design.md`, `docs/14_audit_governance.md`.

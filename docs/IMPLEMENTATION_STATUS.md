# Implementation Status

> This file is maintained by the implementation agent and updated before each phase commit.

## Overall Status

- Completion: ~30%
- Current phase: Phase 3 complete — decision runtime vertical slice
- Latest local commit: (this commit) `feat(decision): implement runtime decision vertical slice`
- Last updated: 2026-07-04

## Completed Phases

1. **Repository audit and implementation plan** — specs read, toolchain verified, phase plan defined.
2. **Backend foundation** — FastAPI 0.139.0 workspace, structured logging + correlation middleware, error contract, async SQLAlchemy/Alembic, Docker Compose (Postgres on host port 5455), quality gates.
3. **Decision runtime vertical slice** —
   - **Data model + first migration** (`45ac3e82696b`): users/roles/permissions, applications, decisions, decision_traces, rules(+versions), rule_sets(+members), strategies(+versions/steps), decision_tables(+versions), scorecards(+versions), reason_codes, manual_review_cases, audit_logs, simulations(+results), approval_requests. Downgrade/upgrade cycle verified on clean DB.
   - **Auth/RBAC**: JWT login (`/v1/auth/login`, `/v1/auth/me`), bcrypt hashing, server-side `require_permission` dependency, roles per docs/14 §7 seeded with permission matrix.
   - **Engine** (`app/engine`, framework-independent): validated JSON condition-tree DSL (all/any/not, 10 operators, unknown operators/malformed values rejected), evaluator with per-condition evidence, decision tables (FIRST_MATCH/PRIORITY + overlap detection), scorecard banding, ordered strategy executor with severity aggregation, STOP_EXECUTION, on_error fallback paths, and conservative MANUAL_REVIEW fallback when no decision is produced.
   - **Runtime API**: `POST /v1/decisions` (idempotent via `Idempotency-Key`, race-safe partial unique index), `GET /v1/decisions/{id}`, `GET /v1/decisions/{id}/trace`. Contract per docs/07 incl. correlation IDs in body/headers.
   - **Evidence layers**: immutable decision trace (masked input snapshot, features, pinned rule/table/scorecard versions, ordered step results, score, errors, latency, request/correlation IDs); business audit events (`DECISION_EXECUTED`, `MANUAL_REVIEW_CASE_CREATED`, `DECISION_VALIDATION_FAILED`) written in the same transaction as the state change; structured technical logs.
   - **Manual review case creation** for MANUAL_REVIEW / FRAUD_INVESTIGATION outcomes.
   - **Synthetic seed** (`app/seed.py`, idempotent): 9 demo users, 15 reason codes, 8 rules, 3 rule sets, MOTOR_SCORECARD v1, FINAL_DECISION_MOTOR v1, active LEASEBACK_MOTOR v1 strategy (7 steps).

## Current Phase

- Phase 4: Versioned rule and decision table management APIs.

## Acceptance Criteria Status

| Area | Status | Evidence |
|---|---|---|
| Backend checks | Passing | ruff format+check, mypy strict (74 files), pytest 52 passed |
| Frontend checks | Not started | Scaffold planned after backend core |
| Clean DB migrations | Passing | Test session drops/recreates `oscar_test` + `alembic upgrade head`; downgrade cycle verified |
| OpenAPI generation | Passing | 6 paths generated |
| Authorization tests | Passing | 401/403 tests: anonymous, underwriter execute, API-client trace access |
| Audit/trace tests | Passing | audit event content, trace reconstruction, PII masking, idempotency |
| End-to-end flows | Partial | Synthetic lease-back motor decision flow passes through API; full compose E2E in Phase 12 |
| Documentation synchronization | Current | ADR-005..007 added |

## Known Limitations

- Rule/strategy/reason-code management is seed-only (no CRUD APIs yet) — Phase 4/5.
- Simulation, manual-review decisioning, governance, monitoring endpoints not yet implemented (Phases 7–10).
- PII masking of traces is deny-list-of-key-names based; `pii.view` permission does not yet unlock unmasked views (masking is applied at persistence).

## Blockers

- None.

## Next Work

1. Phase 4: rule CRUD + versioning + validation against the feature registry, decision-table and scorecard management, reason-code CRUD.
2. Phase 5: strategy CRUD, activation with single-active constraint, rollback.

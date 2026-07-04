# 08 — MVP Backlog

## Priority Definition

| Priority | Meaning |
|---|---|
| P0 | Required for first usable MVP |
| P1 | Important after core flow works |
| P2 | Nice to have / Phase 2 candidate |
| P3 | Advanced / not MVP |

## Epic 1 — Foundation

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Project setup | As engineering, I need a clean app structure so modules can be built safely | Repo has FastAPI `0.139.0`, DB migration, test setup, linting, env config | P0 | Medium | Tech stack decision |
| Backend dependency pin | As engineering, I need reproducible builds | Backend pins `fastapi[standard]==0.139.0` and commits lockfile | P0 | Low | Project setup |
| Frontend scaffold | As frontend engineer, I need app shell | SvelteKit + TypeScript + Tailwind scaffold created and lockfile committed | P1 | Medium | API shell |
| Auth skeleton | As admin, I need users to authenticate | Login/token validation available | P0 | Medium | User table |
| RBAC base | As admin, I need role permissions | Routes/actions check permission | P0 | Medium | Auth |
| Audit log base | As compliance, I need actions logged | Create audit event utility; logs user/system actions | P0 | Medium | Users |

## Epic 2 — Decision Runtime API

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Submit application | As LOS, I need to submit application payload | POST `/v1/decisions` accepts payload and returns decision | P0 | Medium | Strategy, rules |
| Idempotency | As LOS, I need safe retries | Same idempotency key returns same decision | P0 | Medium | Decision table |
| Active strategy resolver | As runtime, I need correct strategy | Loads active strategy by product/segment | P0 | Medium | Strategy version |
| Decision persistence | As compliance, I need stored decisions | Decisions saved with strategy version | P0 | Medium | DB |
| Error handling | As engineering, I need clear errors | Validation and runtime errors structured | P0 | Low | API base |

## Epic 3 — Rule Management

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Rule list | As risk analyst, I need to see rules | List with category/status/version | P0 | Low | Rule model |
| Create draft rule | As risk analyst, I need to create rules | Draft rule can be created with condition/action | P0 | Medium | Feature/operator registry |
| Rule evaluator | As runtime, I need to evaluate rules | Condition tree evaluates correctly with tests | P0 | High | Rule DSL |
| Rule versioning | As compliance, I need immutable active rules | Active rule cannot be edited directly | P0 | Medium | Audit |
| Rule validation | As risk analyst, I need safe rules | Unknown fields/operators rejected | P0 | Medium | Feature registry |

## Epic 4 — Strategy Builder

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Strategy list | As risk analyst, I need strategies by product | List shows product, segment, active version | P0 | Low | Strategy model |
| Create strategy version | As risk analyst, I need draft strategy | Draft version with ordered steps can be created | P0 | Medium | Rule sets |
| Activate strategy | As risk manager, I need one active version | Only one active per product/segment | P0 | Medium | Permission |
| Step execution | As runtime, I need ordered execution | Trace records each step result | P0 | High | Runtime |

## Epic 5 — Decision Trace

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Trace persistence | As auditor, I need reconstructability | Trace stores input, features, steps, rules, score, output | P0 | High | Runtime |
| Trace detail API | As UI, I need to display trace | GET trace endpoint returns structured result | P0 | Medium | Trace model |
| Trace screen | As risk analyst, I need to understand decision | UI shows system decision, rules hit, reason codes | P1 | Medium | API |

## Epic 6 — Reason Codes

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Reason code management | As risk analyst, I need standard reasons | CRUD reason codes with category/severity/messages | P0 | Low | RBAC |
| Reason mapping | As runtime, I need output reasons | Triggered rules add mapped reason codes | P0 | Medium | Rule evaluator |

## Epic 7 — Simulation

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Single simulation | As risk analyst, I need test decision | Simulation runs without production decision | P0 | Medium | Runtime |
| Active vs draft comparison | As risk manager, I need policy impact | Shows decision difference and rule hit difference | P1 | Medium | Strategy version |

## Epic 8 — Manual Review

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Create case from decision | As runtime, I need route review cases | Manual review decision creates case | P0 | Medium | Runtime |
| Manual review queue | As underwriter, I need queue | List cases by status/priority/assigned user | P1 | Medium | Case model |
| Case detail | As underwriter, I need evidence | Shows system decision, trace, applicant summary, reason codes | P1 | Medium | Trace API |
| Analyst decision | As underwriter, I need final decision | Approve/reject/condition with notes and override reason | P1 | Medium | Audit |

## Epic 9 — Monitoring

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Decision summary metrics | As risk manager, I need volume and rates | Approval/reject/manual review rates by date/product/channel | P1 | Medium | Decisions data |
| Top reason codes | As risk analyst, I need reject drivers | Shows top reason codes and trend | P1 | Low | Reason codes |
| Operational metrics | As engineering, I need health view | Latency, error rate, decision volume | P1 | Medium | Logging |

## Epic 10 — Governance

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Basic maker-checker | As risk manager, I need approve changes | Draft can be submitted and approved before activation | P1 | Medium | RBAC |
| Config diff | As approver, I need see changes | Shows before/after rule/strategy config | P1 | Medium | Versioning |
| Rollback | As risk manager, I need recover quickly | Previous active strategy can be reactivated | P1 | Medium | Strategy version |

## Suggested First Vertical Slice

Build this first:

1. DB tables: applications, decisions, decision_traces, rules, rule_versions, strategies, strategy_versions, strategy_steps, reason_codes, audit_logs.
2. POST `/v1/decisions`.
3. Rule evaluator for condition tree.
4. Strategy executor for ordered steps.
5. Persist decision and trace.
6. Basic tests.

Definition of Done:

- One sample lease back motor payload produces decision.
- Decision trace shows every step.
- Reason code exists for manual review/reject.
- Audit log records decision executed.
- Response and trace share a correlation ID.
- Structured technical logs contain no prohibited PII/secrets.
- Relevant docs and implementation status are synchronized in the local commit.

## Epic 11 — Observability & Delivery Controls

| Feature | User Story | Acceptance Criteria | Priority | Complexity | Dependencies |
|---|---|---|---|---|---|
| Correlation middleware | As engineering, I need end-to-end request correlation | Every response has request/correlation headers; context propagates to runtime/trace/audit | P0 | Medium | API base |
| Structured sanitized logs | As operations, I need diagnosable runtime events | JSON-compatible logs include event/status/duration and automated tests reject prohibited PII/secrets | P0 | Medium | Correlation middleware |
| Audit/log separation | As compliance, I need reliable governance evidence | Technical logs, decision trace, and audit events are separate and independently queryable | P0 | Medium | Trace and audit stores |
| Audit persistence guard | As compliance, I need no silent unaudited changes | Critical state-changing operation fails explicitly if mandatory audit event cannot persist | P0 | High | Transactions |
| Implementation status | As project owner, I need autonomous progress visibility | Status doc updated before every phase commit | P0 | Low | Git repo |
| ADR decision log | As architect, I need rationale retained | Material deviations documented with context/options/consequences | P1 | Low | Docs |
| Local phase commits | As reviewer, I need safe rollback checkpoints | Coherent local commit after relevant quality gates; no push/deploy | P0 | Low | Git repo |

# 18 — Observability, Decision Trace & Audit Logging

## 1. Purpose

OSCAR must support engineering operations, credit-decision explainability, compliance review, and historical reconstruction without exposing sensitive customer data.

## 2. Three Separate Evidence Layers

| Layer | Primary User | Purpose | Mutable? |
|---|---|---|---|
| Technical application log | Engineering/Ops | Diagnose runtime health and failures | Retention-managed |
| Decision trace | Risk/Underwriting/Audit | Explain and reproduce one decision | Immutable after execution |
| Business audit event | Compliance/Internal Audit | Prove who changed/approved/overrode what and why | Append-only |

Do not combine them into one generic log record.

## 3. Technical Application Logging

Use structured JSON-compatible logs with at least:

- timestamp,
- level,
- service/module,
- event name,
- request ID,
- correlation ID,
- endpoint or operation,
- status/outcome,
- duration in milliseconds,
- sanitized application/decision identifier,
- exception type and safe error code when applicable.

Prohibited log content:

- full application payload,
- NIK, full phone, address, bank account,
- passwords, tokens, cookies, API keys,
- raw identity documents,
- raw bureau/eKYC/fraud responses,
- unrestricted SQL or internal secrets.

## 4. Correlation and Request IDs

- Accept an optional `X-Correlation-ID` from trusted callers.
- Generate a safe correlation ID when absent.
- Generate a request ID for each API request.
- Return the correlation ID in response headers and structured errors.
- Propagate correlation ID through runtime execution, adapters, trace metadata, and audit events.
- Do not use raw PII as an identifier.

## 5. Decision Trace

A production trace must include:

- trace and decision IDs,
- execution mode,
- sanitized immutable input snapshot,
- normalized/calculated features,
- exact strategy, rule, decision-table, scorecard/model versions,
- ordered step and rule outcomes,
- external adapter result summaries and fallback path,
- decision aggregation,
- reason codes,
- limit/tenor/pricing outputs where applicable,
- safe error/warning data,
- request/correlation IDs,
- execution timestamps and latency.

The trace must be sufficient for deterministic reconstruction without depending on current active configurations.

## 6. Business Audit Events

Audit events must record:

- event ID and event type,
- actor type and actor/user/API-client ID,
- role or authorization context,
- entity type, entity ID, and version,
- action,
- reason/comment where required,
- before and after state or a safe diff,
- approval request/context,
- request and correlation IDs,
- source IP/user-agent only when allowed and necessary,
- timestamp.

Audit events are append-only from the application perspective. Corrections are represented by new events, not by editing history.

## 7. Mandatory Audit Events

At minimum:

- decision executed/failed/fallback,
- rule/strategy/decision-table/scorecard version created, submitted, approved, rejected, activated, retired, or rolled back,
- simulation executed or exported,
- manual-review case created, assigned, decided, overridden, escalated, or closed,
- sensitive decision/trace viewed,
- data exported,
- role/permission changed,
- authentication and authorization failure where appropriate.

## 8. PII Masking and Access Control

- Mask PII by default in UI, API, logs, traces, and exports.
- Reveal sensitive fields only with explicit permission and a documented use case.
- Audit access to unmasked sensitive information.
- Use synthetic data in development/test.
- Implement automated tests that verify prohibited values do not appear in logs.

## 9. Error Handling

- Client errors return stable safe codes and a correlation ID.
- Internal stack traces remain in restricted technical logs only.
- Do not return database details, secrets, policy internals, or raw third-party errors to clients.
- A fallback or timeout must appear in the decision trace and applicable audit event.

## 10. Metrics

Minimum operational metrics:

- request count and error rate,
- latency percentiles,
- decision volume and outcome distribution,
- rule/strategy execution failure,
- external-adapter timeout/fallback,
- manual-review queue size and SLA breach,
- audit-event persistence failure.

Do not use high-cardinality PII values as metric labels.

## 11. Retention and Export

Retention periods are company/regulatory decisions and must remain configurable. Export must be permission-controlled, masked by default, and audited.

## 12. Acceptance Criteria

- Every API response has a correlation ID.
- Every production decision has a trace linked to the same correlation ID.
- Every state-changing action produces an audit event.
- Logs contain no prohibited PII/secrets in automated tests.
- Audit persistence failure is visible and cannot silently pass for critical state changes.
- Technical logs, trace records, and audit events can be queried independently.

## Hardening Addendum — 2026-11-04

- New decision traces sanitize `input_snapshot`, `feature_values`, evaluated step details,
  score details, and errors before persistence; read APIs redact again for older records.
- New simulation traces also redact dynamic values, and trace reads apply defensive redaction.
- Logging redaction handles scalar `extra` fields in addition to nested dictionaries/lists.
- PostgreSQL revision `c1e5f09a64d2` installs BEFORE UPDATE/DELETE and BEFORE TRUNCATE
  triggers on `audit_logs` and `decision_traces`; ordinary application SQL cannot modify them.
  Privileged database owners/superusers may still disable triggers: use separate least-privilege
  runtime credentials, operational controls, audited backups, and retention procedures.
- Key-name redaction is a defense-in-depth mechanism, NOT a complete privacy classification
  guarantee. Whitelist feature schemas and privacy-test new external adapters before production.

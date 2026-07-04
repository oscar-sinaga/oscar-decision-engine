# 02 — PRD MVP: OSCAR Decision Engine

## 1. Product Overview

OSCAR Decision Engine adalah aplikasi internal untuk menjalankan dan mengelola keputusan kredit secara configurable, explainable, auditable, dan versioned. MVP fokus pada core decision engine untuk multifinance, khususnya pembiayaan motor/mobil dan lease back.

## 2. Problem Statement

Proses keputusan kredit yang bergantung pada rule hardcoded, Excel, atau manual underwriting memiliki masalah:

- policy sulit diubah tanpa engineering,
- keputusan sulit dijelaskan,
- versi rule/model tidak terlacak,
- tidak ada simulation sebelum policy live,
- manual override tidak selalu terdokumentasi,
- monitoring approval/reject/manual review/rule hit terbatas,
- audit/compliance sulit melakukan decision reconstruction.

## 3. Goals

- Menyediakan Runtime Decision API untuk menerima application payload dan menghasilkan decision.
- Memungkinkan risk team mengelola rule dan strategy secara aman.
- Menyimpan decision trace lengkap untuk menjawab “kenapa aplikasi ini approve/reject/manual review?”.
- Mendukung simulation terhadap application single case.
- Menyediakan manual review dasar dengan `Decision by System` vs `Decision by Analyst`.
- Menyediakan audit log untuk semua decision dan policy changes.
- Menyediakan structured technical logging, request/correlation ID, PII masking, dan monitoring tanpa mencampurkan technical log dengan decision trace atau business audit event.

## 4. Non-Goals MVP

- Tidak membangun full LOS.
- Tidak membangun full LMS.
- Tidak membangun collection system.
- Tidak membangun full AML/KYC/RegTech platform.
- Tidak membangun full visual drag-and-drop flow builder.
- Tidak membangun AI assistance.
- Tidak menghubungkan langsung ke production SLIK/eKYC tanpa integration plan.

## 5. Target Users

| Role | Kebutuhan |
|---|---|
| Risk Policy Analyst | Membuat rule, test rule, melihat simulation, membaca rule hit |
| Credit Decision Analyst | Mengevaluasi application decision, reason code, score, trace |
| Credit Risk Manager | Approve scope/policy, lihat impact, monitoring approval/reject/manual review |
| Underwriter | Review case, lihat evidence, override decision, catat notes |
| Fraud Analyst | Melihat fraud flags, mismatch indicators, route to investigation |
| Compliance/Internal Audit | Melihat audit log, policy version, decision reconstruction |
| Data Scientist/Credit Risk Modeler | Integrasi score/model, membaca score distribution, validate model output |
| Engineering | Menjaga API, integration, performance, audit, observability |

## 6. MVP Modules

### 6.1 Runtime Decision API

**Description:** API untuk menerima application payload dan mengembalikan decision.

**Functional Requirements:**

- Accept application payload.
- Validate required fields.
- Load active strategy version.
- Execute strategy steps in order.
- Execute rules/decision tables/scorecard integration.
- Generate final decision.
- Generate reason codes.
- Persist decision result.
- Persist decision trace.
- Persist audit event.

**Acceptance Criteria:**

- Given valid payload, API returns `decision_id`, `decision`, `reason_codes`, `strategy_version`.
- Given missing required data, API returns structured validation error.
- Every successful decision has trace and audit log.
- Same idempotency key does not create duplicate decision.

### 6.2 Rule Management

**Description:** UI/API untuk membuat dan mengelola policy rules.

**Functional Requirements:**

- Create rule in draft.
- Edit draft rule.
- Clone rule.
- Retire rule.
- Assign rule to rule set or strategy step.
- Support condition builder using approved fields/operators.
- Support output: pass/fail/reject/manual review/attribute assignment.
- Store rule version.

**Acceptance Criteria:**

- User can create rule `VEHICLE_AGE_MAX_MOTOR`.
- Rule cannot use unknown feature.
- Active rule cannot be edited directly; must create new version.
- Rule execution result appears in decision trace.

### 6.3 Basic Strategy Builder

**Description:** Step-based strategy configuration for MVP.

**Functional Requirements:**

- Create strategy.
- Create strategy version.
- Add ordered steps.
- Step types: validation, rule set, decision table, scorecard/model call, calculation, final decision.
- Activate one strategy version per product/segment.

**Acceptance Criteria:**

- Only one active strategy for product+segment.
- Draft strategy can be simulated before activation.
- Decision trace records each strategy step.

### 6.4 Decision Table

**Description:** Table-based decision rules for risk team.

**Functional Requirements:**

- Define conditions per row.
- Define outputs per row.
- Configure hit policy: first match / priority.
- Use for final decision, limit band, tenor band, pricing band.

**Acceptance Criteria:**

- Decision table returns deterministic output.
- Ambiguous overlapping rows are flagged during validation.

### 6.5 Scorecard/Model Integration

**Description:** MVP supports simple scorecard or external model score input.

**Functional Requirements:**

- Accept score from payload or model service adapter.
- Map score to score band/risk grade.
- Store score/model version in trace.

**Acceptance Criteria:**

- Decision trace shows score, risk grade, model version/source.

### 6.6 Decision History & Trace

**Description:** Search and inspect historical decisions.

**Functional Requirements:**

- Search by application ID, decision ID, product, decision status, date.
- View detail: input snapshot, feature values, rules executed, score result, final decision, reason codes.

**Acceptance Criteria:**

- A compliance user can reconstruct a past decision using stored trace.

### 6.7 Reason Codes

**Description:** Manage reason codes for reject/manual review/conditional approval.

**Functional Requirements:**

- Create reason code.
- Map reason code to rule/model/decision table output.
- Support internal and customer-friendly messages.

**Acceptance Criteria:**

- Reject decision must include at least one reason code.

### 6.8 Basic Simulation

**Description:** Test draft strategy/rule using single application payload.

**Functional Requirements:**

- Run simulation without persisting as production decision.
- Compare active vs draft strategy.
- Show rule hits and decision trace.

**Acceptance Criteria:**

- Simulation result is clearly marked non-production.

### 6.9 Basic Manual Review

**Description:** Queue and case detail for applications requiring analyst review.

**Functional Requirements:**

- Create manual review case from decision result.
- Show system decision and reason.
- Allow analyst decision: approve/reject/approve with condition/request document/escalate.
- Capture notes and override reason.

**Acceptance Criteria:**

- Analyst decision is stored separately from system decision.
- Override requires reason.

### 6.10 Audit Trail & Versioning

**Description:** Track all changes and decisions.

**Functional Requirements:**

- Log policy/rule/strategy changes.
- Log decision execution.
- Log user actions.
- Store before/after for config changes.

**Acceptance Criteria:**

- Every policy change has actor, timestamp, old value, new value.

### 6.11 RBAC

**Description:** Role-based permission.

**Functional Requirements:**

- Roles: Admin, Risk Analyst, Risk Manager, Underwriter, Compliance, Data Scientist, Engineer, Auditor.
- Permission checks for create/edit/activate/override/export.

**Acceptance Criteria:**

- Underwriter cannot activate strategy.
- Auditor is read-only.

### 6.12 Basic Monitoring

**Description:** Operational and risk metrics.

**Functional Requirements:**

- Approval rate.
- Reject rate.
- Manual review rate.
- Top reason codes.
- API latency.
- Error rate.
- Decision volume.

**Acceptance Criteria:**

- Dashboard can show metrics by date/product/channel.

### 6.13 Structured Logging & Correlation

**Description:** Technical observability for runtime and workbench APIs, kept separate from decision trace and business audit events.

**Functional Requirements:**

- Generate/propagate request ID and correlation ID.
- Emit structured technical logs with sanitized identifiers, operation, status, and duration.
- Return correlation ID in response headers and structured errors.
- Mask PII, secrets, raw application payloads, and third-party responses.
- Link relevant trace and audit records through correlation ID without duplicating sensitive data.

**Acceptance Criteria:**

- Every API response exposes a correlation ID.
- Automated tests confirm prohibited PII/secrets are absent from logs.
- Technical logs, decision traces, and business audit events are stored and queried as separate concerns.

## 7. MVP Success Metrics

- 100% production decisions have decision trace.
- 100% reject/manual review decisions have reason code.
- Policy config is versioned.
- Single application simulation is available.
- Manual review override stores reason and actor.
- API P95 latency target is defined and measured.
- 100% API responses carry a correlation ID.
- 100% state-changing actions produce an auditable event or fail explicitly.
- Automated tests verify that technical logs contain no prohibited PII or secrets.

## 8. Open Questions

- Produk pertama: lease back motor, lease back mobil, atau pembiayaan mobil dealer?
- Apakah LOS existing sudah menyediakan application payload lengkap?
- Apakah score/model sudah tersedia sebagai service?
- Apakah DTI/FOIR calculation akan dihitung OSCAR atau dikirim dari upstream?
- Apakah bureau/SLIK-like data tersedia saat decisioning?
- Siapa role final approver untuk strategy activation?
- Apa policy exception yang diizinkan?

## 9. Technology Constraint

MVP implementation must use the finalized stack:

- Backend: FastAPI `0.139.0` via `fastapi[standard]==0.139.0`.
- Backend language: Python `>=3.12,<3.15`.
- Frontend: SvelteKit + TypeScript.
- Styling: Tailwind CSS.
- Database: PostgreSQL.
- Migrations: Alembic.
- Tests: pytest + httpx for backend.

The first implementation milestone should be backend vertical slice, not the full frontend workbench.

## 10. Delivery and Documentation Controls

- Autonomous implementation uses local Git commits per coherent vertical slice or completed phase.
- No autonomous push, merge, remote deployment, force-push, or history rewriting.
- Each phase commit must include relevant tests and synchronized documentation.
- `docs/IMPLEMENTATION_STATUS.md` is updated before each phase commit.
- Material decisions are recorded in `docs/IMPLEMENTATION_DECISIONS.md`.
- Technical logs, decision traces, and business audit events follow `docs/18_observability_and_audit_logging.md`.

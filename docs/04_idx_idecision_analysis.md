# 04 — IDX iDecision Analysis

## Purpose

IDX iDecision dipakai sebagai **benchmark lokal dan visual anchor** karena pernah demo di konteks Sinarmas Multifinance. Namun OSCAR tidak boleh meniru seluruh scope iDecision, karena iDecision tampak mencakup area yang lebih luas daripada core decision engine.

OSCAR harus mengambil prinsip produk yang relevan, lalu tetap dibandingkan dengan standar decision engine enterprise global.

## High-Level Interpretation

Berdasarkan website dan screenshot, iDecision terlihat mencakup beberapa area:

- Rule Management
- Decision Flow / Flow Management
- Scorecard / Decision Tree / Condition / Web Service node
- KYC Monitoring
- AML Monitoring
- Financial Crime Management
- Application Fraud / Transaction Fraud
- Digital Lending Platform
- Loan Origination / Loan Management / Collection
- Monitoring & Reporting
- Modular architecture

## Core vs Adjacent Classification

| Area | Observed in iDecision | Classification for OSCAR | Recommendation |
|---|---|---|---|
| Rule Management | Edit Rule Management, Formatted SQL, Free SQL, CASE WHEN, THEN, ELSE | Core Decision Engine / Risk Policy Workbench | Build MVP with guided DSL, not raw Free SQL |
| Decision Flow | Visual canvas with Rule, Scorecard, Condition, Decision Tree, Web Service | Strategy Builder / Decision Orchestration | MVP use step-based builder; visual canvas Phase 2/3 |
| KYC Monitoring | Watchlist, profile, related parties, document reference, decision by system/user | KYC/AML/RegTech + Case Management pattern | Do not build full KYC; reuse case pattern for manual review |
| AML Monitoring | Transaction info, geo map, alert, hold process, blacklist/high risk | AML/Fraud Monitoring/RegTech | Not MVP; integrate if needed |
| AI Assistance | Seen in KYC/AML monitoring | Advanced Assistive Feature | Not MVP |
| Geo Location Map | AML Monitoring | RegTech/Fraud advanced | Not MVP |
| Decision by System vs Decision by User | KYC/AML detail | Manual Review / Override Pattern | Build in MVP for manual review |
| Document Reference | KYC/AML detail | Evidence Panel | Basic document reference Phase 2; metadata only in MVP |

## Rule Management Screen Analysis

The Rule Management screenshot suggests:

- low-code rule authoring,
- expression builder,
- generated SQL preview,
- structured condition grouping,
- technical fallback via Free SQL.

For OSCAR, the principle is useful: risk team needs to configure policy without waiting for backend release. However, giving Free SQL directly to business users is risky because:

- it may bypass validation,
- it may expose data security issues,
- it may break determinism,
- it is hard to simulate safely,
- it complicates audit and rollback.

### OSCAR Recommendation

MVP Rule Editor should support:

- rule name/description,
- product/segment applicability,
- condition builder using allowed features,
- operator validation,
- action definition,
- reason code mapping,
- status: draft/pending/active/retired,
- versioning,
- simulation before activation,
- audit trail.

Avoid Free SQL in MVP. If required later, expose it only to technical/admin roles with strict review.

## Decision Flow Screen Analysis

The Decision Flow screenshot suggests:

- visual strategy builder,
- reusable node/component library,
- branching condition,
- API/web service call,
- scorecard step,
- logging/notification step,
- run/test functionality,
- parameters.

### OSCAR Recommendation

For MVP, use **ordered step-based strategy** rather than full visual canvas:

1. Validate input
2. Enrich data or read provided enrichment fields
3. Run eligibility rules
4. Run fraud/basic mismatch rules
5. Calculate affordability
6. Execute scorecard/model
7. Execute limit/tenor/pricing rules
8. Generate final decision and reason codes
9. Persist decision trace and audit log

Visual flow builder can be Phase 2/3 after runtime model stabilizes.

## KYC/AML Monitoring Screen Analysis

The KYC and AML screens are not core credit decision engine screens, but they reveal useful enterprise patterns:

- alert list,
- risk indicators,
- profile summary,
- evidence/document panel,
- system recommendation,
- user decision,
- analyst comments,
- hold/continue/reject workflow,
- auditability.

### OSCAR Reuse Pattern

Translate KYC/AML case pattern into credit underwriting:

| iDecision pattern | OSCAR equivalent |
|---|---|
| Decision by System | Engine decision |
| Decision by User | Analyst/underwriter decision |
| Alert list | Reason codes / rule hits / fraud signals |
| Document reference | Application documents / appraisal documents |
| Analyst comment | Underwriter notes |
| Hold process | Pending additional document / fraud investigation |
| Risk indicator | Risk grade / score band / flags |

## What to Copy vs Not Copy

### Copy / Adapt

- Rule authoring concept
- Strategy flow concept
- System decision vs user decision
- Alert/reason/evidence layout
- Audit-friendly case detail
- Componentized decision execution

### Do Not Copy Yet

- Full visual flow canvas
- Full KYC platform
- Full AML transaction monitoring
- AI assistance
- Geolocation monitoring
- Regulatory reporting
- Full LOS/LMS/collection modules

## Critical Scope Risk

IDX iDecision appears to be broader than a decision engine. If OSCAR tries to build all visible modules, it will become a full lending platform and lose focus. MVP must focus on core decisioning and integrate with existing systems where possible.

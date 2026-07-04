# 01 — Research Summary

## Purpose

Dokumen ini adalah ringkasan riset implementasi untuk **OSCAR Decision Engine**, aplikasi internal enterprise untuk mengotomasi dan mengelola keputusan kredit di konteks multifinance.

OSCAR tidak dimaksudkan menjadi full Digital Lending Platform. Scope awalnya adalah **core decision engine + risk policy workbench** yang dapat diintegrasikan dengan LOS, LMS/core system, collection system, fraud/KYC provider, DWH/data lake, dan model serving platform yang sudah ada.

## Product Context

Target use case utama:

- pembiayaan kendaraan motor,
- pembiayaan kendaraan mobil,
- jual beli kendaraan,
- lease back motor,
- lease back mobil,
- pembiayaan melalui dealer/channel partner,
- existing customer/top-up jika relevan.

Target user internal:

- Risk Policy Analyst,
- Credit Decision Analyst,
- Credit Risk Manager / Head of Risk,
- Underwriter,
- Fraud Analyst,
- Compliance / Internal Audit,
- Data Scientist / Credit Risk Modeler,
- Operations,
- Engineering / Platform,
- Product Manager.

## Decision Outcomes

Decision engine harus mendukung output keputusan yang lebih kaya daripada approve/reject:

- `APPROVE`
- `REJECT`
- `MANUAL_REVIEW`
- `APPROVE_WITH_LOWER_LIMIT`
- `APPROVE_WITH_SHORTER_TENOR`
- `APPROVE_WITH_HIGHER_PRICING`
- `REQUEST_ADDITIONAL_DOCUMENT`
- `FRAUD_INVESTIGATION`
- `POLICY_EXCEPTION`

## Two Core Product Layers

| Layer | Function | Primary users |
|---|---|---|
| Runtime Decision API | Menerima data aplikasi, menjalankan strategy/rules/scorecard/model, menghasilkan keputusan dan trace | LOS, channel/dealer app, backend services, engineering |
| Risk Policy Workbench | UI internal untuk mengelola rule, strategy, reason code, simulation, decision history, manual review, audit, governance | Risk, underwriting, fraud, compliance, data science |

## Key Enterprise Decision Engine Capabilities

Fitur yang berulang dari benchmark decision engine enterprise:

1. Runtime decision API
2. Rule management
3. Strategy/decision flow orchestration
4. Decision table
5. Scorecard/model integration
6. Feature catalog/data dictionary
7. Data source integration
8. Reason code management
9. Decision history
10. Decision trace/explainability
11. Simulation/testing
12. Manual review/case management
13. Audit trail/versioning
14. Approval workflow/maker-checker
15. Monitoring/analytics
16. RBAC/security

## Critical Research Conclusion

OSCAR MVP harus fokus pada fondasi yang membuat decision engine benar-benar aman untuk credit risk:

- logic configurable,
- strategy/rule versioned,
- decision trace lengkap,
- reason code jelas,
- simulation sebelum live,
- audit trail untuk semua perubahan,
- manual review dengan system decision vs analyst decision,
- pemisahan scope dari LOS/LMS/collection/KYC/AML.

Jangan mulai dari UI visual flow builder. Mulai dari execution engine, trace, rule configurability, dan versioning.

## Implementation Guardrails

1. Jangan hardcode credit policy di backend.
2. Semua rule/strategy/model config harus versioned.
3. Setiap decision harus punya trace.
4. Setiap perubahan config harus auditable.
5. IDX iDecision adalah benchmark lokal, bukan scope yang harus dijiplak.
6. Visual flow builder ditunda; MVP cukup step-based strategy builder.
7. Free SQL tidak diberikan ke business user pada MVP.
8. Manual override wajib memiliki reason dan actor.
9. Reason code wajib tersedia untuk reject/manual review/approve with condition.
10. Simulation wajib untuk policy change yang akan diaktifkan.

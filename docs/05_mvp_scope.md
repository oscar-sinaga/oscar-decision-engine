# 05 — MVP Scope

## Scope Principle

OSCAR MVP is a **core credit decision engine**, not a full digital lending platform.

The MVP must prove that the company can:

1. submit an application to a runtime API,
2. execute configurable rules/strategy/score logic,
3. return a credit decision,
4. generate reason codes,
5. persist decision trace,
6. run simulation,
7. support basic manual review,
8. audit and version every policy change.

## In Scope — MVP / Phase 1

| Capability | Reason |
|---|---|
| Runtime Decision API | Core execution layer called by LOS/channel |
| Rule Management | Risk policy must be configurable, not hardcoded |
| Basic Strategy Builder | Ordered decision steps per product/segment |
| Decision Table | Business-readable decision matrix |
| Simple Scorecard/Model Integration | Connect model output to policy decision |
| Decision History | Search and review past decisions |
| Decision Trace | Explain why a decision happened |
| Reason Code Management | Support explainability and operational review |
| Basic Simulation | Test draft policy before activation |
| Basic Manual Review | Handle borderline/exception cases |
| Audit Trail | Compliance and reconstruction |
| Versioning | Reconstruct historical decisions |
| RBAC | Control who can view/edit/approve |
| Basic Monitoring | Approval/reject/manual review/error/rule-hit metrics |
| Structured Logging & Correlation | Operational diagnosis with request/correlation IDs and PII masking |

## Phase 2

| Capability | Reason |
|---|---|
| Feature Catalog / Data Dictionary | Remove ambiguity in variable definitions |
| Data Source Integration | Integrate LOS, bureau/SLIK-like, eKYC, DWH, model service |
| Advanced Manual Review | SLA, assignment, escalation, documents, notes |
| Approval Workflow / Maker-checker | Safe policy governance |
| Policy Impact Analysis | Batch simulation with approval/reject impact |
| Limit/Tenor/Pricing Engine | More realistic decision outcomes |
| Model Registry | Manage model/scorecard versions |
| Deployment Management | Promote config from dev/staging/prod |
| Advanced Dashboard | Risk and operational monitoring |

## Phase 3 — REVISED 2026-07-11 (product-owner decision, ADR-012)

The original Phase 3 roadmap (fraud monitoring, champion/challenger, model/drift
monitoring, portfolio/vintage dashboards, collection integration) was **removed
entirely** and replaced by **Generic Rule Authoring & Visual Decision Flow**,
specified authoritatively in **`docs/phase3/`** (PRD, scope, architecture, DSL v2,
expression language, data model, API, screens, test plan, execution plan, agent
prompt).

| Capability | Summary |
|---|---|
| Rule Model v2 | Multi-branch CASE WHEN/ELSE rules, multiple actions, value/classification outputs (`SET_OUTPUT`) |
| Output & category catalogs | Governed writable outputs; configurable rule categories; typed operator metadata |
| Builder-first authoring UX | Nested groups, searchable typed pickers, human-readable + SQL-style previews, generated test form, usage info |
| DAG decision flows | Strategy versions become validated acyclic graphs with CONDITION branching; deterministic single-token execution; auto-migration of existing linear strategies |
| Visual flow canvas | Node-canvas designer (draft edit, read-only active) |
| Safe expression language | Admin-gated text authoring (CASE WHEN/formula) compiled to whitelisted AST; **no SQL/eval execution ever** |
| Decision-table grid editor | Typed spreadsheet-style editing with inline overlap warnings |

## Advanced / Do Not Build Yet

| Capability | Reason to defer |
|---|---|
| Full Digital Lending Platform | Too broad; use existing LOS/channel systems |
| Full Loan Origination System | Separate product domain |
| Full Loan Management System | Separate servicing/core system domain |
| Full Collection System | Separate operational platform |
| Full AML Transaction Monitoring | RegTech-specific, not core credit decisioning |
| Full Regulatory Reporting | Compliance platform scope |
| Full Supply Chain Financing | Product-specific business platform |
| Full Channeling/Joint Financing Platform | Strategic product layer, not MVP engine |
| AI Assistance | Advanced assistive feature; needs strong governance |
| Advanced Geolocation Monitoring | Fraud/AML-specific; not MVP |

## MVP Success Criteria

The MVP is successful if it can answer these questions reliably:

1. Data apa yang masuk?
2. Rule apa yang dijalankan?
3. Score/model apa yang dipakai?
4. Kenapa hasilnya approve/reject/manual review?
5. Versi policy mana yang dipakai?
6. Apa dampaknya jika policy diubah?
7. Siapa yang mengubah, menyetujui, dan mengaktifkan policy?

## First Vertical Slice

Implementasi pertama yang disarankan:

```text
Application payload
  → active strategy version
  → rule execution
  → score/risk grade input
  → final decision
  → reason code
  → decision trace
  → audit log
```

Do not build UI first. Build a working, testable runtime first.

## Engineering Delivery Controls

The autonomous implementation process must:

- use local Git commits per coherent phase,
- pass applicable quality gates before commit,
- update implementation status and affected docs in the same commit,
- never push, deploy, or rewrite human history,
- keep technical logs, decision traces, and business audit events separate,
- use synthetic data only.

# 09 — Screen Specification

## 1. Dashboard

**User:** Risk Manager, Risk Analyst, Operations, Engineering

**Business Questions:**

- Berapa approval/reject/manual review rate?
- Reason code apa yang paling banyak muncul?
- Apakah ada spike error/latency?
- Produk/channel mana yang berubah signifikan?

**Components:**

- KPI cards: total applications, approval rate, reject rate, manual review rate, error rate, API P95 latency.
- Charts: decision trend by date, reason code distribution, product/channel breakdown.
- Filters: date range, product type, channel, strategy version.

## 2. Decision History

**User:** Risk Analyst, Underwriter, Compliance, Audit

**Table Columns:**

- Decision ID
- Application ID
- Product
- Channel
- Decision
- Risk Grade
- Score
- Approved Limit
- Strategy Version
- Reason Codes
- Created At

**Actions:**

- View decision trace
- View application snapshot
- Create/reopen manual review case
- Export selected records (permission required)

## 3. Application Detail / Decision Trace

**User:** Risk Analyst, Underwriter, Compliance

**Sections:**

1. Application summary
2. Applicant summary
3. Vehicle/collateral summary
4. System decision
5. Score/risk grade
6. Limit/tenor/pricing
7. Reason codes
8. Strategy execution timeline
9. Rule results
10. Input snapshot JSON
11. Audit events

**UX Pattern:** follow iDecision-like case detail idea: show `Decision by System` and, if any, `Decision by User` separately.

## 4. Rule List

**User:** Risk Policy Analyst, Risk Manager

**Columns:**

- Rule Code
- Name
- Category
- Status
- Version
- Owner
- Effective Date
- Last Modified

**Actions:**

- Create rule
- Clone rule
- View versions
- Submit for approval
- Retire rule

## 5. Rule Editor

**User:** Risk Policy Analyst

**Sections:**

- General Information: code, name, description, category, product, owner.
- Condition Builder: field/operator/value groups with ALL/ANY logic.
- Action: decision/action output, reason code, severity.
- Preview: generated DSL/JSON; SQL preview not recommended for MVP.
- Test: run sample payload.
- Versioning: draft/active/history.

**Important UX:**

- MVP should use guided condition builder, not Free SQL.
- Free SQL can be admin-only/advanced later.
- Validate unknown fields/operators before save.

## 6. Strategy Builder

**User:** Risk Policy Analyst, Risk Manager

**MVP Pattern:** step-based builder.

**Fields:**

- Strategy code
- Product type
- Segment
- Version
- Status
- Ordered steps

**Step Types:**

- Validation
- Rule Set
- Decision Table
- Scorecard/Model
- Calculation
- Output

**Actions:**

- Add step
- Reorder step
- Simulate
- Submit for approval
- Activate
- Rollback

## 7. Reason Code Management

**User:** Risk Policy Analyst, Compliance

**Fields:**

- Code
- Category
- Internal message
- Customer-friendly message
- Severity
- Product applicability
- Active/inactive

## 8. Single Application Simulator

**User:** Risk Policy Analyst, Data Scientist

**Components:**

- Payload editor/form
- Strategy selector: active or draft
- Run simulation button
- Result panel
- Trace panel
- Compare active vs draft panel

**Empty State:** Provide sample lease back motor payload.

## 9. Manual Review Queue

**User:** Underwriter, Supervisor

**Columns:**

- Case ID
- Application ID
- Product
- System Decision
- Reason Codes
- Priority
- Assigned To
- SLA Age
- Status

**Actions:**

- Assign
- Open case
- Escalate

## 10. Manual Review Case Detail

**User:** Underwriter

**Sections:**

- Case summary
- Applicant profile
- Vehicle/collateral summary
- System decision and reason
- Decision trace link
- Evidence/documents panel
- Analyst notes
- Analyst decision form
- Supervisor escalation

**Decision Actions:**

- Approve
- Reject
- Approve with lower limit
- Approve with shorter tenor
- Request document
- Escalate

## 11. Audit Log

**User:** Compliance, Internal Audit, Admin

**Columns:**

- Timestamp
- Actor
- Event Type
- Entity Type
- Entity ID
- Before/After diff
- Correlation ID

**Filters:**

- Date range
- Actor
- Entity type
- Event type
- Application ID / Rule code / Strategy code

## 12. Admin & RBAC

**User:** Admin

**Features:**

- User list
- Role assignment
- Permission matrix
- API client management
- PII access flag

## 13. Technical Observability Boundary

The Workbench Audit Log screen is for **business audit events**, not raw infrastructure logs.

Audit Log filters should include:

- event type,
- actor,
- entity type/ID/version,
- date range,
- correlation ID,
- decision/application reference,
- approval/override context.

Raw technical logs remain restricted to engineering/operations tooling and must not expose customer PII. The decision detail screen may show safe runtime metadata such as correlation ID, request ID, duration, fallback, and safe error code.

## 14. Phase 3 Workbench Addendum (2026-07-11)

### Feature Catalog and rule categories

- Feature creation includes source `RULE_OUTPUT` and a governed `writable` flag.
- Filters include source and outputs-only views.
- Authorized users can toggle active/writable state and manage active rule-category codes and labels.

### Builder-first rule authoring

- `/rules/new` and `/rules/{id}` use typed feature/operator/value pickers, nested groups, ordered CASE WHEN branches, ELSE actions, and multiple actions.
- Human-readable, SQL-style, and generated JSON tabs are available; JSON is read-only for supported shapes and is not required for the primary journey.
- The detail page generates a typed dry-run form from referenced features and shows rule-set/strategy usage.
- EXPRESSION is visible only to users with `rule.author_expression`; the editor validates with debounce and chooses a writable output target.

### Visual decision-flow canvas

- `/strategies/{id}` renders the persisted OSCAR graph using custom nodes and edges.
- Drafts support palette insertion, configuration drawer, TRUE/FALSE CONDITION handles, validation, save/new version, and auto-layout.
- Non-draft versions are read-only but retain navigation and zoom.
- Decision trace shows node keys, branch taken, output snapshot, and a link to the executed read-only flow.

### Decision-table grid

- `/decision-tables` lists versioned tables; `/decision-tables/{id}` provides typed condition columns and output cells.
- Users can add/copy/delete/reorder rows, reorder/remove columns, use wildcard `*`, select FIRST_MATCH or PRIORITY, and see overlap warnings inline.
- Lifecycle actions remain maker-checker controlled; Advanced JSON is available only as a secondary escape hatch.

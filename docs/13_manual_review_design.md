# 13 — Manual Review Design

## 1. Purpose

Manual review handles applications that cannot be safely auto-approved or auto-rejected. It provides a human underwriting workflow while preserving decision trace and auditability.

Inspired by IDX iDecision KYC/AML screens, OSCAR should separate:

- `Decision by System`
- `Decision by Analyst/User`

## 2. When Manual Review is Created

Manual review can be triggered by:

- DTI/FOIR near threshold.
- LTV above threshold but not severe enough to reject.
- Vehicle appraisal mismatch.
- Income unverified.
- Bureau data unavailable.
- Thin-file applicant.
- Document mismatch requiring investigation.
- Fraud risk medium.
- Existing exposure high but potentially acceptable with lower limit.

## 3. Case Status

```text
NEW
ASSIGNED
IN_REVIEW
PENDING_DOCUMENTS
ESCALATED
APPROVED_BY_ANALYST
REJECTED_BY_ANALYST
CLOSED
```

## 4. Case Detail Sections

1. Case summary.
2. Application summary.
3. Applicant summary.
4. Vehicle/collateral summary.
5. System decision.
6. Reason codes.
7. Decision trace link.
8. Documents/evidence panel.
9. Analyst notes.
10. Analyst decision form.
11. Audit timeline.

## 5. Analyst Decision Actions

| Action | Required Fields |
|---|---|
| Approve | notes optional |
| Reject | reason code, notes |
| Approve with lower limit | approved limit, reason |
| Approve with shorter tenor | approved tenor, reason |
| Request document | requested document list, message |
| Escalate | supervisor/team, reason |
| Fraud investigation | fraud reason, evidence |

## 6. Override Rules

If analyst decision differs from system decision:

- override reason is mandatory,
- user and timestamp are logged,
- before/after decision stored,
- permission required,
- optional supervisor approval for high-risk override.

## 7. Manual Review API Output Example

```json
{
  "case_id": "CASE-001",
  "system_decision": "MANUAL_REVIEW",
  "system_reason_codes": ["DTI_NEAR_THRESHOLD", "LTV_ABOVE_THRESHOLD"],
  "analyst_decision": "APPROVE_WITH_CONDITION",
  "approved_limit": 10000000,
  "approved_tenor_months": 12,
  "override_reason": "Verified income document and reduced limit to acceptable LTV",
  "notes": "Customer provided updated salary slip."
}
```

## 8. Not MVP

- Full document management system.
- Full fraud investigation system.
- SLA automation and supervisor workload balancing.
- AI recommendation.
- Geolocation map.
- Full KYC/AML case workflow.

## 9. Phase 2 Enhancements

- Assignment rules.
- SLA tracking.
- Supervisor approval.
- Document checklist.
- Case comments thread.
- Escalation matrix.
- Underwriter performance dashboard.

## 10. Audit and Correlation Requirements

Every assignment, note, evidence reference, request for documents, analyst decision, override, escalation, and closure must create an audit event.

An override must include:

- actor and permission context,
- system decision and analyst decision,
- reason code and mandatory comment,
- approved limit/tenor/pricing changes where applicable,
- timestamp,
- request/correlation ID,
- supervisor approval reference when required.

Technical logs must contain only sanitized case identifiers and operational metadata.

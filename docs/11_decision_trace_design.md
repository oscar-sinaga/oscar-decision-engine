# 11 — Decision Trace Design

## 1. Purpose

Decision trace answers:

> Kenapa aplikasi ini approve, reject, manual review, atau approve with condition?

Trace is mandatory for auditability, explainability, debugging, risk review, and manual underwriting.

## 2. Trace Content

| Section | Purpose |
|---|---|
| Input Snapshot | Exact payload used for decision |
| Feature Values | Normalized and calculated values |
| Data Source Results | Bureau/eKYC/fraud/model responses if any |
| Strategy Version | Strategy executed |
| Step Results | Ordered execution timeline |
| Rule Results | Rules passed/failed/triggered |
| Score Results | Model/scorecard output |
| Limit/Tenor/Pricing | Calculated offer |
| Final Decision | Final output |
| Reason Codes | Explain decision |
| Errors/Warnings | Timeout, missing data, fallback |
| Runtime Metadata | latency, request ID, correlation ID, execution timestamp, safe error code |

## 3. Trace JSON Structure

```json
{
  "trace_id": "TRC-001",
  "decision_id": "DEC-001",
  "application_id": "APP-001",
  "execution_mode": "PRODUCTION",
  "strategy": {
    "strategy_code": "LEASEBACK_MOTOR",
    "version": 3
  },
  "input_snapshot": {},
  "feature_values": {
    "vehicle.age_years": 6,
    "loan.ltv": 0.83,
    "affordability.dti": 0.38,
    "bureau.max_dpd_12m": 0
  },
  "steps": [
    {
      "order": 1,
      "type": "RULE_SET",
      "name": "Eligibility Rules",
      "status": "PASSED",
      "duration_ms": 12,
      "rule_results": [
        {
          "rule_code": "MIN_AGE",
          "matched": false,
          "status": "PASSED"
        }
      ]
    },
    {
      "order": 2,
      "type": "RULE_SET",
      "name": "Affordability Rules",
      "status": "TRIGGERED",
      "rule_results": [
        {
          "rule_code": "DTI_NEAR_THRESHOLD",
          "matched": true,
          "action_applied": {
            "decision": "MANUAL_REVIEW",
            "reason_code": "DTI_NEAR_THRESHOLD"
          }
        }
      ]
    }
  ],
  "score_result": {
    "score": 684,
    "risk_grade": "B",
    "model_version": "MOTOR_SCORE_V1"
  },
  "final_decision": {
    "decision": "MANUAL_REVIEW",
    "reason_codes": ["DTI_NEAR_THRESHOLD"]
  },
  "metadata": {
    "latency_ms": 132,
    "request_id": "req-001",
    "correlation_id": "corr-001",
    "executed_at": "2026-07-04T10:30:00+07:00"
  }
}
```

## 4. UI Presentation

Decision trace screen should show:

1. **Final Decision Card**: decision, risk grade, score, approved limit/tenor/pricing.
2. **Reason Code Panel**: codes and messages.
3. **Strategy Timeline**: steps in order with pass/fail/triggered.
4. **Rule Detail Drawer**: actual field values vs thresholds.
5. **Input Snapshot**: raw JSON, permission controlled.
6. **System vs User Decision**: if manual review happened.

## 5. Trace Requirements

- Trace must be immutable after decision.
- Simulation trace must be marked as simulation.
- PII must be masked according to permission.
- Trace must include versions of strategy/rules/model.
- Rule conditions should show actual values used.
- If external data is unavailable, trace should show fallback path.

## 6. Example Human Explanation

System can generate an internal explanation:

```text
Decision: MANUAL_REVIEW
Main reason: DTI near threshold.
The applicant's DTI is 43%, close to the maximum allowed threshold of 45%.
Vehicle age and LTV passed policy. Bureau history is clean.
Manual underwriter should verify income and existing obligation before final approval.
```

Customer-facing reason should be controlled by reason code governance, not generated freely.

## 7. Separation from Technical Logs and Audit Events

- A decision trace explains one decision; it is not a generic application log.
- Technical logs diagnose runtime operations and must not duplicate raw trace payloads.
- Business audit events prove user/system state changes and governance actions.
- The three layers are linked by request/correlation IDs and entity identifiers.
- Trace access is permission-controlled and masked by default.
- Automated tests must verify trace immutability and reproducibility after new policy versions become active.

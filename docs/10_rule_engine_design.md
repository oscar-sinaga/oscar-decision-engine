# 10 — Rule Engine Design

## 1. Goal

MVP rule engine should allow credit policy rules to be configured, versioned, tested, executed, and audited without hardcoding in backend code.

## 2. IDX iDecision Inspiration

IDX iDecision screenshot shows a rule editor with `Formatted SQL`, `Free SQL`, `CASE WHEN`, grouped conditions, and generated SQL preview. This is powerful but risky if copied directly.

OSCAR MVP should take the safer principle:

- business-friendly condition builder,
- controlled feature/operator registry,
- generated JSON/DSL,
- no raw SQL for normal business user,
- simulation before activation,
- versioning and audit.

## 3. MVP Rule DSL

```json
{
  "condition": {
    "all": [
      {"field": "vehicle.age_years", "operator": ">", "value": 8},
      {"field": "vehicle.type", "operator": "=", "value": "MOTOR"}
    ]
  },
  "action": {
    "decision": "MANUAL_REVIEW",
    "reason_code": "VEHICLE_AGE_ABOVE_POLICY"
  }
}
```

## 4. Supported Logical Operators

| Operator | Meaning |
|---|---|
| `all` | AND group |
| `any` | OR group |
| `not` | Negation, optional for MVP |

## 5. Supported Comparison Operators

| Operator | Example |
|---|---|
| `=` | employment_type = EMPLOYEE |
| `!=` | collectability != CURRENT |
| `>` | dti > 0.4 |
| `>=` | age >= 21 |
| `<` | ltv < 0.85 |
| `<=` | vehicle_age <= 8 |
| `in` | product_type in [MOTOR_LEASEBACK, CAR_LEASEBACK] |
| `not_in` | area not_in [BLACKLISTED_AREA] |
| `exists` | bureau.max_dpd_12m exists |
| `is_null` | income_verified is_null |

## 6. Action Types

| Action Type | Purpose |
|---|---|
| `SET_DECISION` | Set final/recommended decision |
| `ADD_REASON_CODE` | Add reason code |
| `SET_ATTRIBUTE` | Assign derived value |
| `ROUTE_MANUAL_REVIEW` | Create review case |
| `STOP_EXECUTION` | Stop strategy execution |
| `CONTINUE` | Continue after flagging |

## 7. Rule Examples for Multifinance

### Vehicle age rule

```json
{
  "rule_code": "VEHICLE_AGE_MAX_MOTOR",
  "condition": {
    "all": [
      {"field": "vehicle.type", "operator": "=", "value": "MOTOR"},
      {"field": "vehicle.age_years", "operator": ">", "value": 8}
    ]
  },
  "action": {
    "decision": "MANUAL_REVIEW",
    "reason_code": "VEHICLE_AGE_ABOVE_POLICY"
  }
}
```

### LTV rule

```json
{
  "rule_code": "LTV_MAX_MOTOR",
  "condition": {
    "all": [
      {"field": "loan.ltv", "operator": ">", "value": 0.85}
    ]
  },
  "action": {
    "decision": "MANUAL_REVIEW",
    "reason_code": "LTV_ABOVE_THRESHOLD"
  }
}
```

### Affordability rule

```json
{
  "rule_code": "DTI_MAX_STANDARD",
  "condition": {
    "all": [
      {"field": "affordability.dti", "operator": ">", "value": 0.45}
    ]
  },
  "action": {
    "decision": "REJECT",
    "reason_code": "HIGH_DTI"
  }
}
```

### Fraud mismatch rule

```json
{
  "rule_code": "DOCUMENT_IDENTITY_MISMATCH",
  "condition": {
    "any": [
      {"field": "fraud.identity_match", "operator": "=", "value": false},
      {"field": "fraud.document_match", "operator": "=", "value": false}
    ]
  },
  "action": {
    "decision": "FRAUD_INVESTIGATION",
    "reason_code": "APPLICATION_DATA_MISMATCH"
  }
}
```

## 8. Rule Evaluation Output

```json
{
  "rule_code": "DTI_MAX_STANDARD",
  "version": 3,
  "matched": true,
  "evaluated_conditions": [
    {
      "field": "affordability.dti",
      "operator": ">",
      "expected": 0.45,
      "actual": 0.51,
      "result": true
    }
  ],
  "action_applied": {
    "decision": "REJECT",
    "reason_code": "HIGH_DTI"
  }
}
```

## 9. Rule Governance

- Active rule is immutable.
- Editing active rule creates new draft version.
- Draft must be simulated before activation.
- Activation should require approval in Phase 2.
- All rule changes produce audit log with before/after diff.
- Rule must have owner and reason code mapping.

## 10. Why Avoid Free SQL in MVP

Risks:

- SQL injection or data leakage.
- Business user writes non-deterministic or slow queries.
- Hard to validate feature usage.
- Hard to audit business meaning.
- Hard to run safely across environments.
- Hard to port to non-SQL runtime later.

Recommended approach:

- Guided condition builder for risk users.
- Advanced expression/SQL only for admin/engineering in later phase.
- Strong validation and sandbox execution if ever allowed.

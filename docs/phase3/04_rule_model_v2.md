# Rule Model v2 — CASE WHEN Branches, Multi-Action, Typed Operators

## 1. Shapes

### Legacy shape (valid forever, unchanged semantics)
```json
{ "condition": { "all": [ {"field": "affordability.dti", "operator": ">", "value": 0.45} ] },
  "action":    { "decision": "REJECT", "reason_code": "HIGH_DTI" } }
```
Internally normalized to v2: `branches=[{when: condition, then: [action]}], default=null`.

### V2 shape
```json
{
  "branches": [
    { "when": { "all": [ {"field": "applicant.saving_account_balance", "operator": ">", "value": 50000000} ] },
      "then": [ { "type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 20000 } ] },
    { "when": { "all": [ {"field": "applicant.saving_account_balance", "operator": ">", "value": 10000000} ] },
      "then": [ { "type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 15000 } ] },
    { "when": { "all": [ {"field": "applicant.saving_account_balance", "operator": ">", "value": 5000000} ] },
      "then": [ { "type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 10000 } ] }
  ],
  "default": [ { "type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 0 } ]
}
```
(This is the iDecision "AR balance" example verbatim.)

Storage: `rule_versions.condition_json` stores `{branches, default}` for v2 (or the legacy condition object); `action_json` stays for legacy rows and is `null` for v2 rows. Pydantic models live in `backend/app/engine/dsl.py`.

## 2. Semantics

1. Branches evaluate **top-down, first match wins** (CASE WHEN). Evaluation uses the existing evaluator (`engine/evaluator.py`) against `context.features` — including features written earlier in the same execution.
2. On match: apply the branch's `then` actions **in order** (reuse `_apply_action`). Trace records `matched_branch` (0-based index) and each `action_applied`.
3. No branch matches → apply `default` actions if present (`matched_branch: "default"`); else the rule is `PASSED` (non-event), exactly like today's unmatched rule.
4. `STOP_EXECUTION` anywhere in `then` stops the whole strategy after finishing that action list (existing semantics).
5. A rule may both set outputs and add reason codes / decisions in the same branch (e.g., set `outputs.affordability_risk = "HIGH"` **and** `ADD_REASON_CODE`).

## 3. Actions

| type | fields | notes |
|---|---|---|
| `SET_OUTPUT` | `target`, `value` (JSON literal) or `expression` (string, P3.6) | `target` must be an **active, writable** catalog feature; written into `context.features[target]`; `value` type must match the feature `data_type`. Replaces alias `SET_ATTRIBUTE` (kept accepted, normalized to `SET_OUTPUT`; existing executor mechanism at `executor.py:252` is reused) |
| `SET_DECISION` | `decision`, `reason_code?` | unchanged |
| `ADD_REASON_CODE` | `reason_code` | unchanged; reason code must exist |
| `ROUTE_MANUAL_REVIEW` | `reason_code?` | unchanged |
| `STOP_EXECUTION` | `decision?`, `reason_code?` | unchanged |
| `CONTINUE` | `reason_code?` | unchanged |

Validation: ≤ 20 branches/rule, ≤ 10 actions/branch; at least one branch; `then` non-empty; reason codes must exist (existing check); every referenced field must be an active catalog feature (existing check — now including readable `outputs.*`).

## 4. `rule_kind`

New column `rule_versions.rule_kind` (varchar, default `POLICY_OUTCOME`): `POLICY_OUTCOME` | `STATEMENT` (value-producing) | `CLASSIFICATION` (banding/labels) | `EXPRESSION` (text-authored, P3.6). Purely descriptive for listing/filtering/UI defaults; the executor derives behavior from content only. The create/update API accepts it; service may auto-suggest (`STATEMENT` when all actions are SET_OUTPUT).

## 5. Typed operator matrix (enforced server-side at create/update; drives UI filtering via `/v1/meta`)

| data_type | allowed operators | value form |
|---|---|---|
| NUMBER | `=` `!=` `>` `>=` `<` `<=` `in` `not_in` `exists` `is_null` | number; list of numbers for in/not_in |
| STRING | `=` `!=` `in` `not_in` `exists` `is_null` | string; list of strings |
| BOOLEAN | `=` `!=` `exists` `is_null` | true/false |
| DATE | `=` `!=` `>` `>=` `<` `<=` `exists` `is_null` | ISO date string |

Violation ⇒ 422 with per-condition detail (`field`, `issue: "operator '>' not allowed for STRING feature"`). Implemented in `modules/rules/service.validate_rule_definition` (which already loads the catalog); the pure shape checks stay in `engine/dsl.py`.

## 6. Trace output (rule result entry — superset of today's)

```json
{ "rule_code": "VEHICLE_PRICE_BAND", "version": 2, "rule_kind": "STATEMENT",
  "matched": true, "matched_branch": 1,
  "evaluated_conditions": [ {"field": "...", "operator": ">", "expected": 10000000, "actual": 12000000, "result": true} ],
  "actions_applied": [ {"type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 15000} ],
  "status": "TRIGGERED" }
```
Legacy single-action key `action_applied` remains for legacy rules (do not break trace UI); v2 uses `actions_applied` (list) and the UI renders both.

## 7. Worked patterns (must exist as tests)

1. **Statement**: the §1 example — output consumed by a later DECISION_TABLE row `outputs.vehicle_price_band >= 15000 → APPROVE`.
2. **Classification pair → table combine**: rule A sets `outputs.collateral_risk`, rule B sets `outputs.affordability_risk`, table maps `(HIGH, HIGH) → MANUAL_REVIEW` — the modular pattern from the review, end-to-end.
3. **Policy outcome (legacy)**: existing seeds untouched and still passing.
4. **Mixed branch**: branch sets output *and* adds reason code; ELSE sets default output.

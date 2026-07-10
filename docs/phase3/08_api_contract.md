# Phase 3 API Contract Changes

All endpoints keep the existing conventions: `/v1` prefix, bearer auth, permission checks server-side, safe error envelope `{error:{code,message,details[]},correlation_id}`, audit events on every state change, OpenAPI as machine truth.

## 1. Rules

### `POST /v1/rules`, `POST /v1/rules/{id}/versions`, `PUT /v1/rules/{id}/versions/{vid}` — body extended
```json
{
  "rule_code": "VEHICLE_PRICE_BAND", "name": "Vehicle price band", "category": "LIMIT",
  "rule_kind": "STATEMENT",                     // optional; default POLICY_OUTCOME
  "branches": [ { "when": {"all": [...]}, "then": [ {"type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 20000} ] } ],
  "default":  [ {"type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 0} ],
  // legacy alternative (still accepted): "condition": {...}, "action": {...}
  // EXPRESSION alternative (rule.author_expression): "expression": "CASE WHEN ... END", "output_target": "outputs.vehicle_price_band"
  "version_note": "..."
}
```
Exactly one authoring form per request (legacy | branches | expression) — 422 otherwise. Responses now include `rule_kind`, normalized `branches/default`, `expression_text?`, and `sql_preview` (string, display-only).

### `POST /v1/rules/{id}/versions/{vid}/test` — response extended
```json
{ "matched": true, "matched_branch": 1,
  "evaluated_conditions": [...],
  "actions_applied": [ {"type": "SET_OUTPUT", "target": "outputs.vehicle_price_band", "value": 15000} ],
  "outputs_after": {"outputs.vehicle_price_band": 15000} }
```

### `GET /v1/rules/{id}/usage` — NEW (see `06_catalogs_and_metadata.md` §4 for shape). Auth `rule.view`.

## 2. Expressions

### `POST /v1/expressions/validate` — NEW. Auth `rule.author_expression`.
Request `{expression, expects: "value"|"boolean"}` → 200 `{valid: true, inferred_type, referenced_features[], normalized_preview, ast_node_count}` | 422 `{error.details: [{line, col, message}]}`.

## 3. Strategies (graph)

### `POST /v1/strategies/{id}/versions`, `PUT .../versions/{vid}` — accepts graph OR legacy steps
```json
{ "version_note": "fraud branch",
  "graph": {
    "nodes": [
      {"node_key": "start", "node_type": "START", "position": {"x": 0,   "y": 80}},
      {"node_key": "calc",  "node_type": "CALCULATION", "name": "Derived", "config": {"calculations": ["loan.ltv","affordability.dti"]}, "position": {"x": 240, "y": 80}},
      {"node_key": "risk?", "node_type": "CONDITION", "name": "High device risk?", "config": {"condition": {"all": [{"field": "fraud.device_risk_score", "operator": ">", "value": 0.5}]}}, "position": {"x": 480, "y": 80}},
      {"node_key": "deep",  "node_type": "RULE_SET", "reference_code": "FRAUD_DEEP",  "position": {"x": 720, "y": 0}},
      {"node_key": "basic", "node_type": "RULE_SET", "reference_code": "FRAUD_BASIC", "position": {"x": 720, "y": 160}},
      {"node_key": "score", "node_type": "SCORECARD", "reference_code": "MOTOR_SCORECARD", "position": {"x": 960, "y": 80}},
      {"node_key": "final", "node_type": "DECISION_TABLE", "reference_code": "FINAL_DECISION_MOTOR", "position": {"x": 1200, "y": 80}},
      {"node_key": "end",   "node_type": "END", "position": {"x": 1440, "y": 80}}
    ],
    "edges": [
      {"from": "start", "to": "calc"}, {"from": "calc", "to": "risk?"},
      {"from": "risk?", "to": "deep",  "label": "TRUE"},
      {"from": "risk?", "to": "basic", "label": "FALSE"},
      {"from": "deep",  "to": "score"}, {"from": "basic", "to": "score"},
      {"from": "score", "to": "final"}, {"from": "final", "to": "end"}
    ]
  }
}
```
- Legacy `{"steps": [...]}` still accepted → converted server-side to a linear graph (`start → n1..nN → end`).
- Validation failures return every violation: `{"field": "graph.edges", "issue": "cycle detected: risk? -> deep -> risk?"}`, `{"field": "graph.nodes[risk?]", "issue": "CONDITION requires exactly TRUE and FALSE edges"}`, etc.
- Version detail responses always include `graph` (nodes with positions, edges) and include derived `steps[]` **only when linear** (transition aid for the existing screen until the canvas lands).

### Lifecycle endpoints — UNCHANGED
`submit-approval` (with `simulation_id`), `activate`, `reject`, `rollback` keep paths/permissions/semantics; activation re-runs graph validation + active-reference checks.

## 4. Decision trace — response additions (`GET /v1/decisions/{id}/trace`)
```json
{ "strategy": {"strategy_code": "LEASEBACK_MOTOR", "version": 4, "execution": "GRAPH"},
  "steps": [
    {"order": 1, "node_key": "calc",  "type": "CALCULATION", "status": "PASSED", ...},
    {"order": 2, "node_key": "risk?", "type": "CONDITION", "status": "EVALUATED",
     "condition_result": true, "taken_edge": "TRUE", "evaluated_conditions": [...]},
    {"order": 3, "node_key": "deep",  "type": "RULE_SET", "rule_results": [ {..., "matched_branch": 0, "actions_applied": [...]} ]}
  ],
  "outputs": {"outputs.fraud_flag": true} }        // final rule-written outputs snapshot (NEW, masked like features)
```
Existing fields keep their names; UI renders old traces (no `node_key`) and new ones.

## 5. Features & categories

- `/v1/features` (POST/PATCH/GET): + `writable` (and `source: RULE_OUTPUT`); list filter `writable`.
- `GET/POST /v1/rule-categories`, `PATCH /v1/rule-categories/{id}` — NEW (auth `rule.view`/`rule.create`), audited.
- `/v1/meta` — extended per `06_catalogs_and_metadata.md` §3.

## 6. Decision tables — no contract change
Grid editor (P3.7) uses existing `/v1/decision-tables` endpoints; overlap warnings already returned in version responses are surfaced inline by the UI.

## 7. New audit event types
`RULE_CATEGORY_CREATED/UPDATED`, `EXPRESSION_VALIDATED` (metadata only, no rule persisted — low-volume admin action). Everything else reuses existing event types (rule/strategy/feature lifecycles).

# Catalogs & Metadata — Output Catalog, Category Catalog, Meta, Usage

## 1. Output catalog = feature catalog + `writable`

The Phase-2 feature catalog (`features` table, `backend/app/modules/features/`) governs which paths rules may **read**. Phase 3 adds which paths rules may **write** — the iDecision "Output" selector equivalent — without inventing a second catalog:

- New column `features.writable` (bool, default false). A **writable + active** feature is a legal `SET_OUTPUT` target and a legal EXPRESSION-rule output.
- Everything written is also readable downstream (conditions, tables, condition nodes) — that is what makes outputs composable.
- Convention (not enforced): dedicated outputs live under `outputs.*`. Payload-shadowing writable features are rejected: `writable=true` requires `source ∈ {DERIVED, RULE_OUTPUT}` — a PAYLOAD feature can never be overwritten by a rule.
- New `FeatureSource.RULE_OUTPUT` value for catalog entries whose only producer is rules.
- Seeds (in `app/seed.py`, idempotent): `outputs.collateral_risk` (STRING, RULE_OUTPUT, writable), `outputs.affordability_risk` (STRING), `outputs.vehicle_price_band` (NUMBER), `outputs.eligible_limit` (NUMBER), `outputs.fraud_flag` (BOOLEAN).
- API: existing `/v1/features` CRUD gains the `writable` field (create + patch + list filter `writable=true`). Audit events unchanged (`FEATURE_CREATED/UPDATED` capture the new field in before/after).
- Enforcement points: `rules/service.validate_rule_definition` (SET_OUTPUT targets, expression outputs) and strategy CONDITION validation (read side, already catalog-checked).
- Value-type check: `SET_OUTPUT.value` literal must match the target's `data_type` (NUMBER/STRING/BOOLEAN/DATE), 422 otherwise.

## 2. Rule category catalog (replaces hardcoded enum)

- New table `rule_categories` (`id`, `code` unique, `label`, `active`, `created_at`), seeded from the current `RuleCategory` enum values (VALIDATION, ELIGIBILITY, AFFORDABILITY, BUREAU, FRAUD, COLLATERAL, LIMIT, TENOR, PRICING, ROUTING, FINAL_DECISION).
- `rules.category` becomes a plain string validated against **active** catalog rows at create time (existing rows untouched; the enum constant is removed from validation but kept for seed data).
- CRUD: `GET/POST /v1/rule-categories`, `PATCH /v1/rule-categories/{id}` (activate/deactivate) under `rule.view` / `rule.create`; audited (`RULE_CATEGORY_*`).
- Frontend rule builder loads categories from meta — no hardcoded list remains.

## 3. `/v1/meta` additions (single source for every frontend dropdown)

Extend `backend/app/api/v1/meta.py` response:

```json
{
  "features": [ {"path": "...", "description": "...", "derived": false, "data_type": "NUMBER", "writable": false, "category": "LOAN", "label": "..."} ],
  "operators_by_type": { "NUMBER": ["=","!=",">",">=","<","<=","in","not_in","exists","is_null"],
                          "STRING": ["=","!=","in","not_in","exists","is_null"],
                          "BOOLEAN": ["=","!=","exists","is_null"],
                          "DATE": ["=","!=",">",">=","<","<=","exists","is_null"] },
  "rule_kinds": ["POLICY_OUTCOME","STATEMENT","CLASSIFICATION","EXPRESSION"],
  "action_types": ["SET_OUTPUT","SET_DECISION","ADD_REASON_CODE","ROUTE_MANUAL_REVIEW","STOP_EXECUTION","CONTINUE"],
  "node_types": ["START","VALIDATION","CALCULATION","RULE_SET","SCORECARD","DECISION_TABLE","CONDITION","END"],
  "edge_labels": ["TRUE","FALSE"],
  "rule_categories": [ {"code": "AFFORDABILITY", "label": "Affordability"} ],
  "writable_outputs": [ {"path": "outputs.collateral_risk", "data_type": "STRING", "label": "..."} ]
  // ...existing keys unchanged
}
```
`features[]` items are widened with `data_type`, `writable`, `category`, `label` (the frontend `Meta` type in `frontend/src/lib/api/types.ts` updates accordingly).

## 4. Rule usage endpoint (dependency information)

`GET /v1/rules/{rule_id}/usage` (auth `rule.view`):
```json
{ "rule_code": "DTI_MAX_STANDARD",
  "rule_sets": [ {"id": "...", "code": "AFFORDABILITY_STANDARD", "name": "..."} ],
  "strategies": [ {"id": "...", "strategy_code": "LEASEBACK_MOTOR", "versions_using": [1, 3], "active_version_uses": true} ] }
```
Resolution: `rule_set_members` → rule sets; graph nodes (`node_type=RULE_SET`, `reference_code`) → strategy versions → strategies. Used by the detail-page "Used by" panel and shown as a warning before retiring a rule version.

## 5. Permission additions

| Permission | Grants | Roles (seed) |
|---|---|---|
| `rule.author_expression` | create/update EXPRESSION rules and `SET_OUTPUT.expression`; call `/v1/expressions/validate` | ADMIN (initially; extend later by role assignment UI) |

Everything else reuses existing permissions (`rule.view/create/approve`, `strategy.*`). Seed + `DEFAULT_ROLE_PERMISSIONS` in `backend/app/modules/auth/permissions.py` updated; role matrix screen picks it up automatically.

# Safe Expression Language ("OSCAR Expressions") + SQL-Style Preview

## 1. Purpose and stance

Give power users (admin/engineering first) the *authoring power* of iDecision's "Free SQL" **without executing SQL or arbitrary code**. iDecision compiles rules to SQL because its engine evaluates in-database; OSCAR evaluates rules in-process against an in-memory feature map, so the equivalent power tool is a **text expression language compiled to a whitelisted AST and interpreted by our engine**. This complies with AGENTS.md ("safe structured expressions; never eval/exec/unrestricted SQL"). Raw SQL execution is permanently out of scope (ADR-012).

## 2. Where expressions are used

1. **EXPRESSION rules** (`rule_kind = EXPRESSION`): the whole rule is authored as text — either a boolean expression (condition-style rule) or a `CASE WHEN` returning values for one declared output target.
2. **`SET_OUTPUT.expression`**: any v2 branch action may compute its value with an expression instead of a literal (e.g. `monthly_income * 0.3 - existing_monthly_obligation`).

## 3. Grammar (EBNF)

```
expression   := case_expr | or_expr
case_expr    := "CASE" when_clause+ [ "ELSE" or_expr ] "END"
when_clause  := "WHEN" or_expr "THEN" or_expr
or_expr      := and_expr ( "OR" and_expr )*
and_expr     := not_expr ( "AND" not_expr )*
not_expr     := "NOT" not_expr | comparison
comparison   := additive ( ( "=" | "!=" | ">" | ">=" | "<" | "<=" ) additive
              | "IN" "(" literal ("," literal)* ")"
              | "NOT" "IN" "(" literal ("," literal)* ")"
              | "IS" "NULL" | "IS" "NOT" "NULL" )?
additive     := multiplic ( ("+" | "-") multiplic )*
multiplic    := unary ( ("*" | "/") unary )*
unary        := "-" unary | primary
primary      := literal | identifier | func_call | "(" expression ")"
func_call    := ("MIN"|"MAX"|"ROUND"|"ABS"|"COALESCE") "(" expression ("," expression)* ")"
identifier   := feature path, dotted, e.g. loan.ltv, outputs.collateral_risk
literal      := number | single-quoted string | TRUE | FALSE | NULL
```
Keywords case-insensitive; identifiers case-sensitive (must match catalog paths exactly).

## 4. Security requirements (each one gets a test; see fuzz list in `10_test_plan.md` §6)

1. **Never** `eval`/`exec`/`compile`-and-run of user text; never string-built SQL. Implement a hand-written tokenizer + recursive-descent parser (~200 lines) in `backend/app/engine/expression.py` producing JSON-serializable AST nodes; a tree-walking interpreter evaluates against the feature dict. (Python's `ast` module is NOT used — dotted feature paths and SQL-style keywords don't map cleanly, and a hand parser has zero ambient capability.)
2. Whitelist only the grammar above. No attribute access, no indexing, no lambdas, no names beyond catalog features, no function beyond the five listed.
3. Identifiers must be **active catalog features**; for EXPRESSION rules, the declared output target must be **writable**. Unknown identifier ⇒ 422 naming it.
4. Hard limits (constants, tested): input ≤ 2,000 chars; AST depth ≤ 20; nodes ≤ 200; CASE branches ≤ 20; list literals ≤ 50 items.
5. Deterministic and side-effect-free: no time/random/environment access exists in the grammar; interpreter is a pure function `(ast, features) -> value`.
6. Runtime type errors (string + number, divide by zero, non-boolean WHEN) raise a safe engine error → follows the rule's existing on-error path and records `errors[]` in trace; message contains no payload values (PII).
7. NULL semantics: missing feature ⇒ NULL; comparisons/arithmetic with NULL ⇒ NULL (falsy in WHEN), `IS NULL`/`COALESCE` are the explicit tools — SQL-like tri-state kept minimal and documented.
8. Authoring gated by new permission `rule.author_expression` (granted: ADMIN only initially; seed updated). Regular analysts cannot create/update EXPRESSION rules or `SET_OUTPUT.expression` (403). Execution of an already-approved expression rule requires no extra permission.
9. Storage: `rule_versions.expression_text` (original text) + compiled AST cached in `condition_json` (`{"expression_ast": ...}`). At execution the stored AST is revalidated against limits; text is re-parseable ⇒ reproducibility.
10. Full audit as any rule version (create/update/submit/approve/activate events unchanged).

## 5. Validation endpoint

`POST /v1/expressions/validate` (auth: `rule.author_expression`)
```json
{ "expression": "CASE WHEN saving_account_balance > 50000000 THEN 20000 ELSE 0 END",
  "expects": "value" }            // "value" | "boolean"
```
→ `200 {valid, inferred_type, referenced_features[], normalized_preview, ast_node_count}` or `422` with position-annotated errors (`line`, `col`, `message`). The editor calls this live (debounced).

## 6. SQL-style preview (display-only, for ALL rules)

A pure renderer `dsl_to_sql_preview(rule_definition) -> str` (backend `engine/preview.py`, exposed in rule GET responses; mirrored in frontend for live builder preview) renders builder- and expression-authored rules as familiar SQL-style text:

```sql
CASE
  WHEN applicant.saving_account_balance > 50000000 THEN 20000
  WHEN applicant.saving_account_balance > 10000000 THEN 15000
  ELSE 0
END  -- writes outputs.vehicle_price_band
```
Rules: conditions → `AND`/`OR`/`NOT` with parentheses; actions → comment-style suffix for non-output actions (`-- REJECT (HIGH_DTI)`); banner in UI: **“Preview only — OSCAR never executes SQL.”** The preview is not parsed back and is not stored.

## 7. Examples that must round-trip in tests

| Text | expects | notes |
|---|---|---|
| `monthly_income * 0.3 - existing_monthly_obligation` | value | arithmetic on catalog features |
| `CASE WHEN vehicle.age_years > 10 THEN 'OLD' WHEN vehicle.age_years > 5 THEN 'MID' ELSE 'NEW' END` | value | string classification |
| `loan.ltv > 0.85 AND vehicle.type = 'MOTOR'` | boolean | condition rule |
| `COALESCE(bureau.max_dpd_12m, 999) <= 30` | boolean | NULL handling |
| `ROUND(MIN(loan.requested_amount, outputs.eligible_limit) / 12)` | value | funcs + rule-output input |

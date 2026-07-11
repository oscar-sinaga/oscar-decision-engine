# Verified Code Reference (Ground Truth for the Implementing Agent)

Everything below was extracted from the actual codebase on 2026-07-11. **Trust this file over your assumptions.** If code on disk disagrees with this file, the code wins — note the drift in `IMPLEMENTATION_STATUS.md`.

## 1. Engine (`backend/app/engine/`) — framework/DB-free, keep it that way

### `dsl.py` public surface
```python
class Operator(StrEnum): EQ="="; NEQ="!="; GT=">"; GTE=">="; LT="<"; LTE="<="
                         IN="in"; NOT_IN="not_in"; EXISTS="exists"; IS_NULL="is_null"

class Condition(BaseModel):      # extra="forbid"
    field: str; operator: Operator; value: Any = None

class AllGroup(BaseModel):  all: list["ConditionNode"]          # min 1 item
class AnyGroup(BaseModel):  any: list["ConditionNode"]
class NotGroup(BaseModel):  not_: "ConditionNode" = Field(alias="not")
ConditionNode = AllGroup | AnyGroup | NotGroup | Condition       # NESTING ALREADY SUPPORTED

class ActionType(StrEnum): SET_DECISION; ADD_REASON_CODE; SET_ATTRIBUTE;
                           ROUTE_MANUAL_REVIEW; STOP_EXECUTION; CONTINUE

class RuleAction(BaseModel):     # extra="forbid"
    type: ActionType = ActionType.SET_DECISION
    decision: DecisionType | None = None
    reason_code: str | None = None
    attribute: str | None = None          # SET_ATTRIBUTE target (rename path → SET_OUTPUT in P3.1)
    attribute_value: Any = None
    stop_execution: bool = False

class RuleDefinition(BaseModel): condition: ConditionNode; action: RuleAction

def parse_rule_definition(condition_json: dict, action_json: dict) -> RuleDefinition
def collect_condition_fields(node: ConditionNode) -> set[str]
```

### `executor.py` key facts
```python
class ResolvedRule(BaseModel):   # per-rule plan entry: rule_code, version, rule_kind?, definition
class StepPlan(BaseModel):       # order, step_type, name, reference_code, reference_version,
                                 # on_error, config, resolved rules/table/scorecard payloads
class ExecutablePlan(BaseModel): # strategy_code, strategy_version, steps: list[StepPlan]  ← becomes graph in P3.4
class ExecutionResult(BaseModel) # final_decision, reason_codes, risk_grade, score, approved_limit,
                                 # approved_tenor_months, pricing_rate, feature_values, step_results,
                                 # score_result, validation_failures, errors, latency_ms, executed_at

def run_strategy(plan: ExecutablePlan, payload: dict[str, Any]) -> ExecutionResult   # THE driver
def _run_rule_set_step(step, context)     # evaluates each ResolvedRule; where branches go (P3.1)
def _apply_action(action, context) -> dict  # executor.py:242; SET_ATTRIBUTE arm at :252 writes
                                            #   context.features[action.attribute] = action.attribute_value
def most_severe(candidates) -> DecisionType | None   # severity aggregation — DO NOT CHANGE
```
`_ExecutionContext` (dataclass) holds `features: dict[str, Any]`, candidate decisions, reason codes, step trace list. On-error semantics live in `_apply_step_error`.

### `features.py`
```python
PAYLOAD_FEATURES: dict[str, str]   # path -> description
DERIVED_FEATURES: dict[str, str]   # loan.ltv, affordability.dti, vehicle.age_years, ...
SCORE_FEATURES:   dict[str, str]   # score.value, score.risk_grade, ...
KNOWN_FEATURES = {**PAYLOAD_FEATURES, **DERIVED_FEATURES, **SCORE_FEATURES}
```
Since Phase 2 the DB feature catalog governs validation; these dicts still drive CALCULATION capability and catalog seeding (`modules/features/service.catalog_seed_rows`). Runtime read set: `modules/features/service.active_feature_paths(session) -> set[str]`.

## 2. Strategies module (`backend/app/modules/strategies/`)

```python
# plan_builder.py — the single bridge modules→engine (shared by decisions AND simulations)
async def resolve_active_strategy_version(session, product_type: str, segment: str) -> StrategyVersion
async def get_strategy_version(session, version_id: UUID) -> StrategyVersion | None
async def build_plan(session, strategy_version: StrategyVersion) -> ExecutablePlan   # keep signature!

# service.py — lifecycle already enforces:
#   validate_steps(...)                     (unknown refs/features/calcs → 422 details list)
#   submit_strategy_version(..., simulation_id)  → opens ApprovalRequest w/ simulation_ref
#   activate_strategy_version(...)          → maker-checker + simulation_ref required (settings flag)
#                                             + _verify_references_activatable + single-active retire
#   rollback_to_version(..., reason)        (reason mandatory)
# models.py: Strategy, StrategyVersion (status: DRAFT/PENDING_APPROVAL/ACTIVE/REJECTED/RETIRED),
#            StrategyStep (step_order, step_type, reference_code, on_error, config_json)  ← replaced in P3.4
```

## 3. Rules module

```python
# service.validate_rule_definition(session, condition, action) -> RuleDefinition
#   parses DSL, checks fields ∈ active_feature_paths(session), checks reason_code exists.
#   → P3.1 extends: branches form, typed-operator matrix, SET_OUTPUT target checks.
# Lifecycle mirrors strategies (submit→approval request, activate: maker-checker, retire, reject).
# rule_versions columns today: version, status, condition_json, action_json, version_note,
#   created_by, approved_by, effective_from/to.
```

## 4. Cross-cutting facts

| Fact | Value |
|---|---|
| Audit helper | `from app.modules.audit.service import record_audit_event` — call `record_audit_event(session, event_type=..., entity_type=..., entity_id=..., action=..., actor=user, before_value=..., after_value=..., reason=..., metadata=...)` then `await session.commit()`; it stages in the SAME transaction |
| Auth dependency | `user: User = require_permission(Permissions.RULE_CREATE)` in route signature |
| Permissions class | `backend/app/modules/auth/permissions.py` — `Permissions.*`, `ALL_PERMISSIONS`, `DEFAULT_ROLE_PERMISSIONS` (seed source) |
| Error types | `app.shared.domain.errors`: `ValidationFailedError(msg, details=[{field,issue}])`→422, `NotFoundError`→404, `ConflictError`→409, `AuthorizationError`→403 |
| Settings | pydantic-settings, env prefix `OSCAR_`; file `app/shared/config/settings.py`; dev/test DB port **5455** |
| Router registration | add imports + `api_router.include_router(...)` in `backend/app/api/v1/router.py` |
| Model registration | export every new SQLAlchemy model in `backend/app/models.py` (Alembic autogenerate reads it) |
| Alembic | `cd backend && OSCAR_DATABASE_URL=postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar uv run alembic revision --autogenerate -m "..."` then hand-edit; upgrade with same env var |
| Display IDs | `app.shared.utils.ids.display_id("SIM") → "SIM-YYYYMMDD-XXXXXXXXXX"` |
| Masking | `app.shared.utils.masking.sanitize_snapshot`, `redact` — apply to the new trace `outputs` snapshot |

## 5. Test infrastructure (`backend/tests/`)

```python
# conftest.py provides:
@pytest.fixture(session)  database   # drops+recreates oscar_test, runs alembic upgrade head, seeds
@pytest.fixture           db_client  # httpx AsyncClient over the app with the migrated+seeded DB
async def login(client, username) -> dict[str,str]   # returns {"Authorization": "Bearer ..."} headers
# passwords: OscarDemo123! for all seeded users

# heavily reused helpers:
tests/integration/test_decision_runtime.py: lease_back_motor_payload(**overrides), submit(client, payload)
tests/integration/test_strategy_management.py: VALID_STEPS, submit_with_simulation(client, analyst, strategy_id, version_id)
# pytest-asyncio auto mode: plain `async def test_*` works, no decorator needed
```

## 6. Frontend facts

| Fact | Value |
|---|---|
| Stack | SvelteKit 2, **Svelte 5 runes mode forced** (`$state`, `$derived`, `$effect`, `$props`, snippets); TS strict; Tailwind 4 |
| API client | `import { api, ApiError } from '$lib/api/client'` — `api<T>(path, {method?, body?, query?})`; token auto-attached; errors are `ApiError{code,status,details,detailText,correlationId}` |
| Auth/permissions (UX only) | `import { auth } from '$lib/auth.svelte'` — `auth.hasPermission('rule.create')` |
| Shared components | `$lib/components/`: `Card.svelte` (snippet children + `actions`), `Badge.svelte` (`value`, `kind="decision"|"status"`), `ErrorNote.svelte` (`error`), `JsonBlock.svelte` (`value`), `Pagination.svelte`, `ConditionBuilder.svelte` (v1, flat — rewritten in P3.3) |
| Types | hand-written DTOs in `frontend/src/lib/api/types.ts` — extend, don't duplicate |
| Meta | pages load `api<Meta>('/v1/meta')` for dropdowns; never hardcode lists |
| Nav | sidebar array `NAV` in `src/routes/+layout.svelte` |
| Tests | Vitest specs `src/**/*.spec.ts` (node env); Playwright specs `e2e/*.e2e.ts`, webServer = preview :4173, backend must run on :8000 (compose) |
| Style | prettier + eslint (`svelte/no-navigation-without-resolve` disabled); run `npm run format` before lint |

## 7. Seeded objects you can rely on in tests

Strategy `LEASEBACK_MOTOR` v1 ACTIVE (product MOTOR_LEASEBACK / DEFAULT) with 7 steps; rule sets `ELIGIBILITY_MOTOR`, `FRAUD_BASIC`, `AFFORDABILITY_STANDARD`; scorecard `MOTOR_SCORECARD` v1 ACTIVE; decision table `FINAL_DECISION_MOTOR` v1 ACTIVE; reason codes incl. `HIGH_DTI`, `DTI_NEAR_THRESHOLD`, `BLACKLIST_HIT`; users per README; model registry `MOTOR_SCORE:V1`.

Canonical golden payload behaviors (current, to hard-code in golden tests): base payload → `APPROVE_WITH_CONDITION` (limit 12.5jt); `fraud={"blacklist_hit": True}` → `REJECT`; `applicant={"monthly_income": 7_440_000}` → `MANUAL_REVIEW`; `fraud={"identity_match": False}` → `FRAUD_INVESTIGATION`.

# Phase 3 Data Model & Migrations

Baseline: Alembic head `1864d7efc83f` (5 revisions). Phase 3 adds **three** revisions, one per engine-affecting sub-phase, each applied and tested from a clean database (existing pytest session fixture already migrates `oscar_test` from scratch).

## M1 — `p3 rule model v2` (lands with P3.1/P3.2)

```
rule_versions
  + rule_kind        varchar(20) NOT NULL DEFAULT 'POLICY_OUTCOME'
  + expression_text  text NULL                      -- original text for EXPRESSION rules

features
  + writable         boolean NOT NULL DEFAULT false
  (new allowed source value 'RULE_OUTPUT' — varchar column, no DDL needed)

rule_categories (NEW)
  id uuid PK, code varchar(50) UNIQUE NOT NULL, label varchar(100) NOT NULL,
  active boolean NOT NULL DEFAULT true, created_at timestamptz DEFAULT now()
```
Data: seed `rule_categories` from the current enum values inside the migration (idempotent inserts) so existing `rules.category` strings remain valid; seed writable `outputs.*` features via `app/seed.py` (not the migration — consistent with existing seeding policy).

Storage note: v2 rule bodies reuse `condition_json` (`{"branches": [...], "default": [...]}` or `{"expression_ast": ...}`); `action_json` stays for legacy rows. No destructive change; downgrade drops the new columns/table.

## M2 — `p3 strategy graph` (lands with P3.4) — THE critical migration

```
strategy_nodes (NEW)
  id uuid PK
  strategy_version_id uuid NOT NULL FK strategy_versions(id) ON DELETE CASCADE, INDEX
  node_key   varchar(50) NOT NULL          -- stable per-version identity
  node_type  varchar(20) NOT NULL          -- START|VALIDATION|CALCULATION|RULE_SET|SCORECARD|DECISION_TABLE|CONDITION|END
  name       varchar(200) NOT NULL DEFAULT ''
  reference_code varchar(100) NULL
  on_error   varchar(20) NOT NULL DEFAULT 'FAIL'
  config_json jsonb NOT NULL DEFAULT '{}'  -- required_fields / calculations / condition (CONDITION nodes)
  position_x integer NOT NULL DEFAULT 0
  position_y integer NOT NULL DEFAULT 0
  UNIQUE (strategy_version_id, node_key)

strategy_edges (NEW)
  id uuid PK
  strategy_version_id uuid NOT NULL FK strategy_versions(id) ON DELETE CASCADE, INDEX
  from_node_key varchar(50) NOT NULL
  to_node_key   varchar(50) NOT NULL
  label         varchar(10) NULL           -- 'TRUE'|'FALSE' from CONDITION nodes, else NULL
  UNIQUE (strategy_version_id, from_node_key, to_node_key, label)
```

**Data conversion (upgrade), in the same revision, pure SQL/SQLAlchemy core (no app imports):**
```
for each strategy_version:
    steps = SELECT * FROM strategy_steps WHERE strategy_version_id = :id ORDER BY step_order
    INSERT node ('start', START, x=0)
    for i, s in enumerate(steps, 1):
        INSERT node (f'n{i}', s.step_type, s.name, s.reference_code, s.on_error, s.config_json,
                     position_x = 240*i, position_y = 0)
    INSERT node ('end', END, x = 240*(len+1))
    INSERT edges: start→n1, n1→n2, ..., n_last→end   (label NULL)
DROP TABLE strategy_steps
```
**Downgrade (best effort, documented):** recreate `strategy_steps`; for versions whose graph is a **linear chain** (every non-END out-degree ≤1, no CONDITION), reconstruct ordered steps; abort with a clear error if any non-linear graph exists.

**Safety requirements for the implementing agent:**
1. Golden tests (`10_test_plan.md` §5) run the seeded strategies against the golden payloads **before** writing the migration (capture expected outputs into the test file) and assert identical decisions after.
2. Conversion covers ALL versions regardless of status (DRAFT/PENDING/ACTIVE/REJECTED/RETIRED) — retired versions must stay reproducible for audit.
3. `alembic upgrade head` then `downgrade -1` then `upgrade head` must succeed on a seeded dev database *before* any non-linear graph exists.

ORM: `StrategyStep` model is deleted; `StrategyNode`/`StrategyEdge` added in `modules/strategies/models.py`; `app/models.py` exports updated; seeds write graphs.

## M3 — `p3 permission expression` (lands with P3.6)

No schema change (permissions are rows). Seed inserts permission `rule.author_expression` + grant to ADMIN via existing idempotent `seed_rbac`. If the implementing agent prefers migration-seeded permissions, keep consistency with Phase-2 practice: **seed script, not migration** — therefore M3 may be empty/omitted; listed here so nobody hunts for a missing migration.

## Entity relationship delta

```
strategy_versions 1──* strategy_nodes
strategy_versions 1──* strategy_edges        (edges reference node_key, scoped by version)
rules *──1 rule_categories (by code, soft reference validated in service)
features.writable=true  ⇐ targets of SET_OUTPUT / EXPRESSION outputs
```

## Index & performance notes

- `strategy_nodes(strategy_version_id)`, `strategy_edges(strategy_version_id)` btree indexes (created by FK columns above) are sufficient: graphs are ≤100 nodes and loaded whole by `plan_builder`.
- No change to hot decision-path tables (`decisions`, `decision_traces`).

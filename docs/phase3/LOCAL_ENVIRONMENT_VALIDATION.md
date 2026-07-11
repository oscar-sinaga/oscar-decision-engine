# Phase 3 Local Environment Validation Notes

Workstation acceptance completed on 2026-07-11 (Asia/Jakarta) against branch
`integrate/phase3-20260711`, starting at Phase 3 commit `d248408`.

## Repository and workstation

- Initial branch/HEAD: `integrate/phase3-20260711` / `d2484088135e6ccb356ca937071ae0ed8d1265ea`.
- The only initial untracked content was the user-owned backup directory. `backups/` is now ignored; the SQL file was never modified or staged.
- Backup verified at `backups/oscar_before_phase3_20260711.sql`: **327,510 bytes**, non-empty.
- Toolchain: system Python 3.11.4; uv 0.10.0 managing Python 3.13.12; Node 24.16.0; npm 11.13.0; Docker 28.2.2; Compose 2.37.1; Chrome 150.0.7871.101; Edge 150.0.4078.48.

## Preserved-volume rebuild and migration evidence

- The user required preservation of `oscar-decision-engine_oscar_pgdata`; no `down -v`, reset, truncate, or database drop was performed on `oscar`.
- `docker compose down` followed by `docker compose up -d --build` succeeded. PostgreSQL logged `Database directory appears to contain a database; Skipping initialization`; postgres was healthy and backend/frontend were running on 5455/8000/3000.
- PostgreSQL, backend, and frontend logs were clean at startup. Backend ran Alembic and the idempotent seed before Uvicorn became ready.
- `alembic heads`, `current`, and `upgrade head` all reported `f4b7c9d2e601 (head)`.
- The pre-Phase-3 backup contains `CREATE TABLE` and `COPY` records for `strategy_steps`. The preserved database now has no `strategy_steps` table and has `strategy_nodes`/`strategy_edges`.
- Migrated `LEASEBACK_MOTOR` v1 remained ACTIVE with 9 nodes and 8 edges: `START -> VALIDATION -> CALCULATION -> FRAUD_BASIC -> ELIGIBILITY_MOTOR -> AFFORDABILITY_STANDARD -> MOTOR_SCORECARD -> FINAL_DECISION_MOTOR -> END`.
- The full pytest fixture independently recreated `oscar_test` and applied all migrations from a clean database on every full backend run.

## Final automated gates

- Backend: `uv sync --frozen`; Ruff format check (**141 files**); Ruff lint; mypy (**133 source files**); full pytest **213 passed in 79.84s**.
- Four clean-seed golden reproducibility cases passed inside the backend suite.
- Frontend: `npm ci`; Prettier/ESLint; Svelte check **0 errors / 0 warnings**; Vitest **5 files / 27 tests passed**; production build succeeded.
- Playwright Chromium installed. The final standard `npx playwright test` ran serially (the journeys mutate one shared acceptance database) and passed **7/7 in 40.3s**.
- A workstation-only CORS defect was fixed: the documented Playwright origin `http://127.0.0.1:4173` was absent from the local allowlist. Runtime preflight now returns 200 with the exact allow-origin header; a regression test covers it.

## Manual acceptance spot-check

- [x] Existing migrated strategy renders as the same linear flow. Database connectivity was verified node-by-node; the workbench rendered the flow canvas for `LEASEBACK_MOTOR`.
- [x] CONDITION TRUE/FALSE paths both execute and appear in trace. A targeted integration test asserted `taken_edge` TRUE/FALSE plus the corresponding next node.
- [x] Active strategy versions are read-only. The active version showed disabled palette/version controls and an explicit read-only configuration state.
- [x] Maker-checker plus exact-version simulation evidence blocks/permits activation correctly. Covered by the backend gate and passing graph/governance Playwright journey.
- [x] Decision-table overlap warnings appear after save and reopen. Reopened draft v2 displayed one overlapping pair and marked both rows.
- [x] Admin can author expressions; analyst receives 403 from the API. Covered in the passing expression-permission E2E.
- [x] Primary PRD journey can be completed without editing JSON. Builder-first rule authoring, grid table, canvas, governance, decision, and trace were exercised by the passing E2E suite.

## Latency smoke

Forty compose-stack decisions were measured (10 rounds across the four canonical payload shapes):

| Count | Min | Average | P50 | P95 | Max | Target |
|---:|---:|---:|---:|---:|---:|---|
| 40 | 116.31 ms | 223.12 ms | 222.64 ms | 318.00 ms | 332.39 ms | **PASS**, P95 < 500 ms |

The preserved workstation policy intentionally differs from the clean seed: `DOCUMENT_IDENTITY_MISMATCH` v1 was retired through the workbench on 2026-07-04 before the Phase 3 backup (the backup contains the audit event). Therefore the persistent-volume fraud-mismatch payload currently returns `APPROVE_WITH_CONDITION`, while clean-seed golden tests correctly return `FRAUD_INVESTIGATION`. Acceptance preserved this user policy decision and did not reactivate or rewrite it.

## PII masking spot-check

- A synthetic decision and trace request verified NIK, phone, email, and address are returned as `***REDACTED***`; none of the raw values appeared in the trace response.
- A synthetic 422 validation response contained no raw PII values.
- Searching the complete backend container log found zero occurrences of all four synthetic values.
- Trace responses expose the Phase 3 `outputs` field. The seeded strategy produced `{}`; a regression test verifies a sensitive dotted output key such as `outputs.synthetic_phone` is redacted while `outputs.eligible_limit` remains available.

## Safe workstation procedure

The preserved-volume acceptance procedure is intentionally:

```powershell
docker compose down
docker compose up -d --build
```

Do not replace it with `docker compose down -v` when validating legacy-row conversion. The verified backup must remain outside Git.

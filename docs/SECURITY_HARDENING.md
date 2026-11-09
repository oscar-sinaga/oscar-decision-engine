# Security & Reliability Hardening — November 2026

Status: **proposed hardening branch**, not production deployment approval.

Branch: `fix/security-reliability-hardening-20261104`.

## Six audit items

| Finding | Implementation | Required operational follow-up |
| --- | --- | --- |
| P0: Compose secrets and demo users | Secrets supplied via private `.env`, loopback-only ports, demo seeding off by default, backend non-local guard | Provide strong rotated credentials, disable demo users in any hosted environment, use a real secrets manager |
| P0: PII traces and logs | Redact dynamic feature paths, evaluated field values and scalar log extras; sanitize at write and read | Validate against real schema classifications using only synthetic samples; privacy / penetration review |
| P1: Idempotency | Fingerprint canonical payload + actor; 409 for reused/mismatched or legacy keys; race recheck | Coordinate callers' request-key policies and retention |
| P1: CI and unprotected main | GitHub Actions adds PostgreSQL+Alembic, Ruff, mypy, pytest, frontend lint/check/Vitest/build, Playwright E2E | **GitHub administrator must enable main branch ruleset and required checks** |
| P1: Application-layer immutability only | DB migration adds update/delete/truncate rejection triggers to decision traces and audit log | Runtime DB role must lack DDL/trigger override privileges; backup and restore drills |
| P2: Documentation drift | README/backend guide/status/API contract/final report updated with November changes | Keep future changes and tests in sync |

## Non-destructive local startup

1. Back up the **existing PostgreSQL volume** and confirm the backup is recoverable.
2. Copy `.env.example` to ignored `.env` and replace secret placeholders with random values.
   Generate random values locally, for example `python -c "import secrets; print(secrets.token_hex(32))"`.
   Generate separate values for database and JWT. Use URL-safe hexadecimal for PostgreSQL.
3. If the database volume **already exists**, changing `POSTGRES_PASSWORD` in Compose
   does **not** update the existing PostgreSQL user's password. Keep the currently working
   password until you perform a planned `ALTER ROLE` rotation using existing authorized
   credentials, then change the API DSN and recheck startup.
4. `docker compose config`, then `docker compose up -d --build`.
   **Do not run `docker compose down -v`** on a database you wish to preserve.
5. Test `/health`, migration revision, application flow, trace access and audit integrity.
   The new migration is `c1e5f09a64d2` and includes defensive triggers.
6. Demo seed is disabled by default. Only on an empty *disposable local* database:
   set `OSCAR_ENABLE_DEMO_SEED=true`, `OSCAR_SEED_PASSWORD` to a unique demo-only value,
   then start Compose. Never use demo data/accounts on internet-accessible services.

The default full stack listens only on `127.0.0.1:3000`, `127.0.0.1:8000` and
`127.0.0.1:5455`. For a real deployment use private networking, HTTPS, authentication
hardening, secrets management, role-separated database users, and firewall restrictions.
The development Compose file is **not** a production deployment template.

## API behavioral compatibility

- `Idempotency-Key`: same caller + same canonical body = replay. Different caller/body = 409.
  Old keyed decisions have `request_fingerprint=NULL` and always return 409 when retried;
  the original unmasked request payload cannot safely be reconstructed from storage.
- Input and trace PII: masking is intentionally irreversible. Redacted trace content is useful
  for audit but cannot guarantee full input-level replay without governed external evidence.
- Database append-only triggers prevent modification of evidence via ordinary SQL and ORM.
  DBA/superuser privileges can override triggers, so database privilege segregation and
  independent backups remain mandatory.

## CI/CD and branch protection

Workflow `.github/workflows/quality-gates.yml` runs on `main`, `fix/**` and PRs to main.
The checks run against **ephemeral synthetic CI-only PostgreSQL**, never the production DB.

Recommended repository settings (requires owner/admin action):

1. GitHub repository → Settings → Rules → Rulesets → New branch ruleset.
2. Target `main`; require a pull request before merging.
3. Require passing status checks `backend`, `frontend`, and `e2e`; prevent force pushes
   and branch deletion. Choose review requirements appropriate for the team.
4. Verify the ruleset is **active**, not evaluation mode, and there are no unsafe bypasses.

The connector used to update source code does not currently expose ruleset admin writes.
A CI workflow file alone does **not** protect the branch.

## Validation and release checklist

- [ ] Ruff format + lint and mypy strict green
- [ ] Full pytest suite green on new PostgreSQL and migration revision
- [ ] Frontend ESLint/Prettier, Svelte check, Vitest and build green
- [ ] Playwright suite green on seeded ephemeral PostgreSQL
- [ ] Preserved-volume migration and rollback/recovery rehearsal
- [ ] Test idempotency key reuse and concurrent caller retries
- [ ] PII leakage tests on nested rule evaluation, simulation and model output fields
- [ ] Dependency vulnerability triage (npm/pip) and independent security assessment
- [ ] Branch protection enabled and required checks enforced by GitHub administrator
- [ ] Product owner approves credit policy assumptions and exception handling
- [ ] Controlled deployment with rollback plan and monitoring

**No automated test suite can establish absolute absence of bugs.** Treat successful
CI as a release gate, not as proof of production readiness. Do not insert real personal
customer information into GitHub issues, CI fixtures, screenshots, or sample traces.

## Request-boundary follow-up — 2026-11-05

The latest migration is `d7a4c192e605`, following the original append-only migration
`c1e5f09a64d2`. Audit identifiers are widened to preserve valid feature/model/strategy names.
Downgrade refuses to truncate evidence that no longer fits the old schema. Read
`REQUEST_BOUNDARY_AUDIT_2026_11_05.md` for the newly reproduced defects, tests and remaining
release gates. CI's schema rehearsal uses only a reset, guarded `oscar_test` database; it is
not a preserved-production-volume migration/restore claim.

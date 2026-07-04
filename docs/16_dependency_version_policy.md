# 16 — Dependency & Version Policy

## Purpose

This document prevents agentic implementation from accidentally drifting dependency versions while building OSCAR Decision Engine.

## Backend Version Policy

FastAPI must be pinned exactly for MVP:

```text
fastapi[standard]==0.139.0
```

Recommended Python constraint:

```text
>=3.12,<3.15
```

Do not use floating FastAPI versions such as:

```text
fastapi
fastapi[standard]
fastapi>=0.139.0
```

unless the user explicitly asks to upgrade.

## Backend Dependency Baseline

Recommended initial backend dependency set:

```text
fastapi[standard]==0.139.0
pydantic>=2,<3
sqlalchemy>=2,<3
alembic>=1,<2
asyncpg>=0.29,<1
pytest>=8,<9
httpx>=0.27,<1
```

The exact dependency resolution must be captured in a lockfile or equivalent reproducibility artifact.

## Frontend Version Policy

Use SvelteKit + TypeScript + Tailwind CSS latest stable at scaffold time.

After scaffold:

- commit `package.json`,
- commit package manager lockfile,
- do not auto-upgrade major versions during feature implementation,
- keep API DTOs typed,
- prefer generated OpenAPI client later when backend contract stabilizes.

## Allowed Package Managers

Pick one and stay consistent:

- Backend: `uv` preferred, but pip/venv is acceptable.
- Frontend: pnpm preferred, but npm is acceptable.

Do not mix package managers in the same project unless explicitly requested.

## Upgrade Process

Any upgrade to FastAPI, SvelteKit, Tailwind, SQLAlchemy, or Pydantic must include:

1. reason for upgrade,
2. changelog/release note review,
3. test run,
4. rollback plan,
5. updated lockfile,
6. documentation update.

## Agentic Coding Guardrail

When implementing features, the coding agent must not silently change dependency versions. If a package is missing, add it deliberately and document why.

## Logging and Observability Dependency Policy

- Use the Python standard library where sufficient.
- Add a structured logging, tracing, metrics, or OpenTelemetry package only with a documented need.
- Pin/lock the resolved version and record the reason in `docs/IMPLEMENTATION_DECISIONS.md`.
- Do not introduce a vendor-specific observability SDK into decision-domain logic.
- Any dependency upgrade must preserve PII masking, context propagation, and logging tests.

## Lockfile Commit Rule

Dependency manifests and lockfiles are committed together in the same coherent change. Automated implementation must not silently regenerate lockfiles unrelated to the current task.

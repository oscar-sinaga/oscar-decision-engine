# OSCAR Decision Engine — Backend

FastAPI `0.139.0` backend for the OSCAR credit-risk decision engine.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) ≥ 0.10 (manages Python 3.13 automatically)
- Docker (for the PostgreSQL dev database)

## Quickstart

```bash
# At repo root: create a private .env and replace password/JWT placeholders.
# For EXISTING database volumes, read docs/SECURITY_HARDENING.md before password rotation.
docker compose up -d postgres

# Set OSCAR_DATABASE_URL to match the actual PostgreSQL password/port.
# Set OSCAR_JWT_SECRET to a strong local secret.
cd backend
uv sync                      # install locked dependencies
uv run alembic upgrade head  # apply migrations
# ONLY for an intentionally synthetic local database, after setting OSCAR_SEED_PASSWORD:
# uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

OpenAPI docs: http://localhost:8000/docs

## Quality gates

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy app tests
uv run pytest
```

Integration tests require the compose PostgreSQL to be running; they use a
separate `oscar_test` database created automatically.

## Configuration

Settings load from `OSCAR_`-prefixed environment variables (see `.env.example`
at the repository root). Never commit a real `.env`.

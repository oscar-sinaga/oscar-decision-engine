# OSCAR Decision Engine — Backend

FastAPI `0.139.0` backend for the OSCAR credit-risk decision engine.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) ≥ 0.10 (manages Python 3.13 automatically)
- Docker (for the PostgreSQL dev database)

## Quickstart

```bash
# from the repository root: start PostgreSQL (host port 5455)
docker compose up -d postgres

cd backend
uv sync                      # install locked dependencies
uv run alembic upgrade head  # apply migrations
uv run python -m app.seed    # load synthetic users, rules, strategy config
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

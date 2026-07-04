"""Shared test fixtures.

Integration tests run against a dedicated ``oscar_test`` PostgreSQL database
(compose service on host port 5455). The database is dropped, recreated,
migrated via Alembic, and seeded once per test session — which also verifies
that migrations apply to a clean database every run.
"""

import asyncio
import os
from collections.abc import AsyncIterator

TEST_DATABASE_URL = os.environ.setdefault(
    "OSCAR_DATABASE_URL",
    "postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar_test",
)

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.seed import SEED_PASSWORD, seed_all  # noqa: E402

_ADMIN_DSN = {
    "host": "localhost",
    "port": 5455,
    "user": "oscar",
    "password": "oscar_dev_password",
    "database": "oscar",
}


async def _recreate_test_database() -> None:
    import asyncpg

    conn = await asyncpg.connect(**_ADMIN_DSN)
    try:
        await conn.execute("DROP DATABASE IF EXISTS oscar_test WITH (FORCE)")
        await conn.execute("CREATE DATABASE oscar_test")
    finally:
        await conn.close()


def _run_migrations() -> None:
    from alembic.config import Config

    from alembic import command

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")


async def _seed_test_database() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with async_sessionmaker(engine)() as session:
            await seed_all(session)
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def database() -> None:
    asyncio.run(_recreate_test_database())
    _run_migrations()
    asyncio.run(_seed_test_database())


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture
async def db_client(app: FastAPI, database: None) -> AsyncIterator[AsyncClient]:
    """Client backed by the migrated + seeded test database."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def login(client: AsyncClient, username: str) -> dict[str, str]:
    response = await client.post(
        "/v1/auth/login", json={"username": username, "password": SEED_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

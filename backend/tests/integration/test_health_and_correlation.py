import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app


async def test_health_returns_ok_with_correlation_headers(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"].startswith("req-")
    assert response.headers["x-correlation-id"].startswith("corr-")


async def test_inbound_correlation_id_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Correlation-Id": "corr-from-caller-01"})
    assert response.headers["x-correlation-id"] == "corr-from-caller-01"


async def test_unsafe_inbound_correlation_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"X-Correlation-Id": "bad value !!"})
    assert response.headers["x-correlation-id"] != "bad value !!"
    assert response.headers["x-correlation-id"].startswith("corr-")


async def test_not_found_uses_structured_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["correlation_id"] == response.headers["x-correlation-id"]


@pytest.fixture
def crashing_app() -> FastAPI:
    app = create_app()

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("internal detail with connection string postgres://secret")

    return app


async def test_unhandled_error_returns_safe_envelope(crashing_app: FastAPI) -> None:
    transport = ASGITransport(app=crashing_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "postgres://" not in response.text
    assert "RuntimeError" not in response.text
    assert body["correlation_id"] == response.headers["x-correlation-id"]
    assert response.headers["x-request-id"].startswith("req-")

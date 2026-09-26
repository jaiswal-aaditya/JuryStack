import httpx
import pytest
from fastapi import HTTPException

from app.core.health import require_database_ready
from app.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    async def database_is_ready() -> None:
        return None

    app.dependency_overrides[require_database_ready] = database_is_ready
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ready"}


@pytest.mark.asyncio
async def test_health_is_unavailable_when_database_is_not_ready() -> None:
    async def database_is_unavailable() -> None:
        raise HTTPException(status_code=503, detail={"code": "database_unavailable"})

    app.dependency_overrides[require_database_ready] = database_is_unavailable
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/api/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "database_unavailable"

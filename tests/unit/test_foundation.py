from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health() -> None:
    app = create_app(Settings(environment="test"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert len(response.headers["X-Request-ID"]) == 36
        assert (await client.get("/docs")).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("available", [True, False])
async def test_readiness(available: bool) -> None:
    app = create_app(Settings(environment="test"))
    connection = AsyncMock()
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=connection)
    context.__aexit__ = AsyncMock(return_value=None)
    app.state.database = MagicMock()
    app.state.database.connect.return_value = context
    app.state.redis = AsyncMock()
    app.state.redis.ping.return_value = available
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/v1/ready")
        assert response.status_code == (200 if available else 503)
        assert response.json()["dependencies"]["redis"] == available

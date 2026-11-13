import asyncio

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app
from tests.helpers import provision


@pytest.mark.asyncio
async def test_payload_limit_and_sanitized_validation() -> None:
    app = create_app(Settings(environment="test", max_payload_bytes=1024))
    await provision(app)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        response = await client.post("/v1/optimize", content=b"x" * 1025)
        assert response.status_code == 413
        response = await client.post(
            "/v1/optimize",
            headers={"Authorization": "Bearer gateway-test"},
            json={"model": "gpt-4.1-mini", "text": {"secret": "private"}},
        )
        assert response.status_code == 422
        assert "private" not in response.text
        assert "secret" not in response.text
    await app.state.database.dispose()


@pytest.mark.asyncio
async def test_concurrent_health_smoke() -> None:
    app = create_app(Settings(environment="test"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        responses = await asyncio.gather(*(client.get("/v1/health") for _ in range(100)))
        assert all(response.status_code == 200 for response in responses)
        assert len({r.headers["X-Request-ID"] for r in responses}) == 100

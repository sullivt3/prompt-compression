from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.core.rate_limit import ACQUIRE
from app.main import create_app
from tests.helpers import provision


@pytest.mark.asyncio
async def test_preview_rejects_full_concurrency_before_compression() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    app.state.redis.eval.side_effect = lambda script, *args: 0 if script == ACQUIRE else 1
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            with patch("app.api.optimize.run_in_threadpool", new_callable=AsyncMock) as compress:
                response = await client.post(
                    "/v1/optimize",
                    headers={"Authorization": "Bearer gateway-test"},
                    json={"model": "gpt-4.1-mini", "text": "Explain Docker."},
                )
            assert response.status_code == 429
            compress.assert_not_awaited()
            app.state.redis.zrem.assert_not_awaited()
    finally:
        await app.state.database.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["algorithmic", "semantic"])
async def test_preview_releases_lease_once_on_success_or_error(mode: str) -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            response = await client.post(
                "/v1/optimize",
                headers={"Authorization": "Bearer gateway-test"},
                json={"model": "gpt-4.1-mini", "text": "Explain Docker.", "strategy": mode},
            )
            assert response.status_code == (200 if mode == "algorithmic" else 422)
            app.state.redis.zrem.assert_awaited_once()
    finally:
        await app.state.database.dispose()

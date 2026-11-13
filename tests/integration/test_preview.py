from unittest.mock import AsyncMock

import httpx
import pytest
from redis.exceptions import ConnectionError

from app.core.config import Settings
from app.main import create_app
from tests.helpers import provision


@pytest.mark.asyncio
async def test_preview_without_provider() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app, "test-key")
    app.state.redis = AsyncMock()
    app.state.redis.eval.return_value = 1
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        payload = {"model": "gpt-4.1-mini", "text": "Hey ChatGPT, please explain Kubernetes."}
        assert (await client.post("/v1/optimize", json=payload)).status_code == 401
        client.headers["Authorization"] = "Bearer test-key"
        response = await client.post("/v1/optimize", json=payload)
        assert response.status_code == 200
        assert response.json()["applied"]
        assert response.json()["transformations"][0]["validation_succeeded"]
        assert (
            await client.post("/v1/optimize", json={**payload, "strategy": "semantic"})
        ).status_code == 422
        app.state.redis.eval.return_value = 0
        assert (await client.post("/v1/optimize", json=payload)).status_code == 429
        app.state.redis.eval.side_effect = ConnectionError("private diagnostic")
        response = await client.post("/v1/optimize", json=payload)
        assert response.status_code == 503
        assert "private diagnostic" not in response.text

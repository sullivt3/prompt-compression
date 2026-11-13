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


@pytest.mark.asyncio
async def test_preview_compresses_test_purpose_sentence() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            response = await client.post(
                "/v1/optimize",
                headers={"Authorization": "Bearer gateway-test"},
                json={
                    "model": "gpt-4.1-mini",
                    "text": (
                        "Paste a prompt below. This is just a test to see how many "
                        "filler words can be removed form the input."
                    ),
                },
            )
            assert response.status_code == 200
            result = response.json()
            assert result["applied"]
            assert result["rules_applied"] == ["test_introduction"]
            assert result["optimized"].startswith("Paste a prompt below. This tests how many")
            assert result["saved_tokens"] > 0
    finally:
        await app.state.database.dispose()


@pytest.mark.asyncio
async def test_preview_compresses_instructions_around_fenced_code() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    code = "```python\ndef add(a, b):\n    return a + b\n```"
    text = (
        "Can you please provide an explanation of this function?\n\n"
        + code
        + "\n\nProvide an explanation of addition in order to teach a beginner."
    )
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            response = await client.post(
                "/v1/optimize",
                headers={"Authorization": "Bearer gateway-test"},
                json={"model": "gpt-4.1-mini", "text": text},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["applied"] and result["saved_tokens"] > 0
            assert code in result["optimized"]
            assert "Explain addition to teach a beginner." in result["optimized"]
            assert result["validation"]["checks"]["protected_content"]
            assert set(result["rules_applied"]) >= {"explanation_phrase", "purpose_phrase"}
    finally:
        await app.state.database.dispose()

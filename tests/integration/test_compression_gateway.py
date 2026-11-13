import json
from unittest.mock import patch

import httpx
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import TenantConfig, UsageRecord
from app.main import create_app
from app.providers.openai import OpenAIProvider
from app.providers.registry import ProviderRegistry
from tests.helpers import provision


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_gateway_compression_and_fallback(failure: bool) -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    async with app.state.sessions() as session:
        config = await session.get(TenantConfig, "tenant-test")
        config.compression_mode = "algorithmic"
        await session.commit()
    text = "Hey ChatGPT, can you please explain Kubernetes?"
    captured = []

    def provider(req: httpx.Request) -> httpx.Response:
        captured.append(json.loads(req.content))
        return httpx.Response(
            200, json={"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 2}}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as upstream:
        app.state.providers = ProviderRegistry(OpenAIProvider(upstream, "mock"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            with (
                patch(
                    "app.compression.router.RuleCompressor.compress",
                    side_effect=RuntimeError("simulated"),
                )
                if failure
                else patch(
                    "app.compression.router.RuleCompressor.compress",
                    wraps=__import__("app.compression.rules", fromlist=["RuleCompressor"])
                    .RuleCompressor()
                    .compress,
                )
            ):
                response = await client.post(
                    "/v1/chat/completions",
                    headers={"Authorization": "Bearer gateway-test"},
                    json={
                        "model": "gpt-4.1-mini",
                        "temperature": 0.5,
                        "messages": [
                            {"role": "system", "content": text},
                            {"role": "user", "content": text},
                        ],
                    },
                )
            assert response.status_code == 200
            assert captured[0]["messages"][0]["content"] == text
            assert captured[0]["messages"][1]["content"] == (
                text if failure else "explain Kubernetes?"
            )
            assert captured[0]["temperature"] == 0.5
    async with app.state.sessions() as session:
        row = await session.scalar(select(UsageRecord))
        assert row.optimized is not failure
        assert row.provider_input_tokens == 10
    await app.state.database.dispose()

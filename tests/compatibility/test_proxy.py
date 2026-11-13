import json
from collections.abc import AsyncIterator

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import Settings
from app.main import create_app
from app.providers.openai import OpenAIProvider
from app.providers.registry import ProviderRegistry
from tests.helpers import provision


class SSE(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        for text in ["Hello", " world"]:
            event = {
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": 1,
                "model": "gpt-4.1-mini",
                "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(event)}\n\n".encode()
        yield b"data: [DONE]\n\n"


@pytest.mark.asyncio
@pytest.mark.parametrize("stream", [False, True])
async def test_official_sdk(stream: bool) -> None:
    def upstream(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.openai.com/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer upstream-test"
        body = json.loads(request.content)
        assert body["messages"] == [{"role": "user", "content": "Hello"}]
        assert body["temperature"] == 0.5
        if stream:
            return httpx.Response(200, stream=SSE(), headers={"content-type": "text/event-stream"})
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Hello world"},
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
            },
        )

    settings = Settings(environment="test")
    app = create_app(settings)
    await provision(app)
    async with httpx.AsyncClient(transport=httpx.MockTransport(upstream)) as provider_http:
        app.state.providers = ProviderRegistry(OpenAIProvider(provider_http, "upstream-test"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as gateway_http:
            client = AsyncOpenAI(
                api_key="gateway-test",
                base_url="http://gateway/v1",
                http_client=gateway_http,
                max_retries=0,
            )
            result = await client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": "Hello"}],
                stream=stream,
                temperature=0.5,
            )
            if stream:
                texts = [chunk.choices[0].delta.content async for chunk in result]
                assert texts == ["Hello", " world"]
            else:
                assert result.choices[0].message.content == "Hello world"


@pytest.mark.asyncio
async def test_auth_validation_provider_errors() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, json={"secret": "must-not-escape"})
        )
    ) as provider_http:
        app.state.providers = ProviderRegistry(OpenAIProvider(provider_http, "upstream-test"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            body = {"model": "gpt-4.1-mini", "messages": [{"role": "user", "content": "Hi"}]}
            assert (await client.post("/v1/chat/completions", json=body)).status_code == 401
            client.headers["Authorization"] = "Bearer gateway-test"
            response = await client.post("/v1/chat/completions", json=body)
            assert response.status_code == 429
            assert "must-not-escape" not in response.text
            body["tools"] = []
            assert (await client.post("/v1/chat/completions", json=body)).status_code == 422

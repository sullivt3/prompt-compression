import asyncio
import json
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import select

from app.api.chat import ManagedStream
from app.core.config import Settings
from app.db.models import TenantConfig, UsageRecord
from app.main import create_app
from app.providers.openai import OpenAIProvider
from app.providers.registry import ProviderRegistry
from tests.helpers import provision


class UpstreamStream(httpx.AsyncByteStream):
    def __init__(self, failure: bool) -> None:
        self.failure = failure
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
        if self.failure:
            raise httpx.ReadError("sensitive diagnostics")
        yield b'data: {"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":1}}\n\n'
        yield b"data: [DONE]\n\n"

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_stream_cleanup_usage_and_no_retry(failure: bool) -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    async with app.state.sessions() as session:
        config = await session.get(TenantConfig, "tenant-test")
        config.compression_mode = "algorithmic"
        await session.commit()
    stream = UpstreamStream(failure)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(json.loads(request.content))
        return httpx.Response(200, stream=stream)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as provider:
        app.state.providers = ProviderRegistry(OpenAIProvider(provider, "mock"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer gateway-test"},
                json={
                    "model": "gpt-4.1-mini",
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    "messages": [
                        {"role": "user", "content": "Hey ChatGPT, please explain Docker."}
                    ],
                },
            )
            assert response.status_code == 200
            assert "hello" in response.text
            assert "sensitive diagnostics" not in response.text
            assert ("Upstream stream interrupted" in response.text) is failure
    assert len(calls) == 1
    assert calls[0]["messages"][0]["content"] == "please explain Docker."
    assert stream.closed
    app.state.redis.zrem.assert_awaited_once()
    async with app.state.sessions() as session:
        record = await session.scalar(select(UsageRecord))
        assert record.status_code == (502 if failure else 200)
        assert record.provider_input_tokens == (None if failure else 8)
    await app.state.database.dispose()


@pytest.mark.asyncio
async def test_cleanup_on_disconnect_before_first_chunk() -> None:
    closed = []

    async def content() -> AsyncIterator[bytes]:
        yield b"hello"

    async def cleanup() -> None:
        closed.append(True)

    async def send(event: dict) -> None:
        raise asyncio.CancelledError()

    async def receive() -> dict:
        return {"type": "http.disconnect"}

    response = ManagedStream(content())
    response.cleanup = cleanup
    with pytest.raises(asyncio.CancelledError):
        await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
    assert closed == [True]


@pytest.mark.asyncio
async def test_chat_records_disconnect_before_stream_starts() -> None:
    from starlette.requests import Request

    from app.api.chat import chat
    from app.core.security import Principal
    from app.schemas.chat import ChatRequest

    app = create_app(Settings(environment="test"))
    await provision(app)
    stream = UpstreamStream(False)
    try:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream))
        ) as provider:
            app.state.providers = ProviderRegistry(OpenAIProvider(provider, "mock"))
            scope = {
                "type": "http",
                "app": app,
                "state": {"request_id": "disconnect-test"},
                "asgi": {"spec_version": "2.4"},
            }
            response = await chat(
                ChatRequest(
                    model="gpt-4.1-mini",
                    stream=True,
                    messages=[{"role": "user", "content": "Explain Docker."}],
                ),
                Request(scope),
                Principal("tenant-test", "key-test"),
            )

            async def send(event: dict) -> None:
                raise asyncio.CancelledError()

            async def receive() -> dict:
                return {"type": "http.disconnect"}

            with pytest.raises(asyncio.CancelledError):
                await response(scope, receive, send)
        assert stream.closed
        app.state.redis.zrem.assert_awaited_once()
        async with app.state.sessions() as session:
            record = await session.scalar(select(UsageRecord))
            assert record.status_code == 499
    finally:
        await app.state.database.dispose()

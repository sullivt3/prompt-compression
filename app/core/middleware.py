import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send


class PayloadLimitMiddleware:
    """Bound request buffering including chunked bodies before JSON parsing."""

    def __init__(self, app: ASGIApp, max_bytes: int = 1048576) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        chunks: list[bytes] = []
        size = 0
        try:
            async with asyncio.timeout(10):
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    chunk = event.get("body", b"")
                    size += len(chunk)
                    if size > self.max_bytes:
                        await self.reject(send, 413, b'{"error":{"message":"Payload too large"}}')
                        return
                    chunks.append(chunk)
                    if not event.get("more_body", False):
                        break
        except TimeoutError:
            await self.reject(send, 408, b'{"error":{"message":"Request body timed out"}}')
            return
        delivered = False

        async def replay() -> Any:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def reject(send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})


class ManagedStreamingResponseMixin:
    """Ensure cleanup also runs if disconnect happens before the first yielded chunk."""

    cleanup: Callable[[], Awaitable[None]]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)  # type: ignore[misc]
        finally:
            await asyncio.shield(self.cleanup())

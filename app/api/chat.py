import asyncio
import json
from collections.abc import AsyncGenerator
from time import perf_counter
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response, StreamingResponse

from app.core.middleware import ManagedStreamingResponseMixin
from app.core.rate_limit import (
    acquire_concurrency,
    limit_principal,
    release_concurrency,
)
from app.core.security import Principal, authenticate
from app.schemas.chat import ChatRequest
from app.services.optimization import optimize_request
from app.services.usage import record_usage
from app.telemetry.sse import SSEUsageCollector

router = APIRouter()


class ManagedStream(ManagedStreamingResponseMixin, StreamingResponse):
    pass


@router.post("/chat/completions")
async def chat(
    payload: ChatRequest, request: Request, principal: Annotated[Principal, Depends(authenticate)]
) -> Response:
    start = perf_counter()
    await limit_principal(request, principal)
    lease = await acquire_concurrency(request, principal)
    upstream: httpx.Response | None = None
    stream_handed_off = False
    try:
        forwarded, metrics = await run_in_threadpool(
            optimize_request,
            payload.model_dump(exclude_unset=True),
            principal,
            request.app.state.settings,
        )
        provider = request.app.state.providers.resolve(payload.model)
        provider_start = perf_counter()
        try:
            async with asyncio.timeout(max(0.01, 120 - (perf_counter() - start))):
                upstream = await provider.send(forwarded)
        except (httpx.TimeoutException, TimeoutError) as exc:
            await record_usage(request, principal, payload.model, metrics, 504, start)
            raise HTTPException(504, "Provider timed out") from exc
        except httpx.HTTPError as exc:
            await record_usage(request, principal, payload.model, metrics, 502, start)
            raise HTTPException(502, "Provider unavailable") from exc
        if upstream.status_code >= 300:
            status = upstream.status_code if 400 <= upstream.status_code <= 599 else 502
            await record_usage(
                request,
                principal,
                payload.model,
                metrics,
                status,
                start,
                (perf_counter() - provider_start) * 1000,
            )
            raise HTTPException(status, "Provider rejected the request")
        if payload.stream:
            stream_upstream = upstream
            collector = SSEUsageCollector()
            stream_status = 499

            async def chunks() -> AsyncGenerator[bytes, None]:
                nonlocal stream_status
                try:
                    async with asyncio.timeout(max(0.01, 120 - (perf_counter() - start))):
                        async for chunk in stream_upstream.aiter_bytes():
                            collector.feed(chunk)
                            yield chunk
                    stream_status = 200
                except (httpx.HTTPError, TimeoutError):
                    stream_status = 502
                    yield b'data: {"error":{"message":"Upstream stream interrupted"}}\n\n'

            body_iterator = chunks()
            response = ManagedStream(
                body_iterator,
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

            async def cleanup_stream() -> None:
                try:
                    await body_iterator.aclose()
                    await stream_upstream.aclose()
                    await record_usage(
                        request,
                        principal,
                        payload.model,
                        metrics,
                        stream_status,
                        start,
                        (perf_counter() - provider_start) * 1000,
                        collector.usage,
                    )
                finally:
                    await release_concurrency(request, principal, lease)

            response.cleanup = cleanup_stream
            stream_handed_off = True
            return response
        try:
            async with asyncio.timeout(max(0.01, 120 - (perf_counter() - start))):
                body = await upstream.aread()
            usage = None
            try:
                response_data = json.loads(body)
                if isinstance(response_data, dict) and isinstance(response_data.get("usage"), dict):
                    usage = response_data["usage"]
            except (ValueError, UnicodeError):
                pass
            await record_usage(
                request,
                principal,
                payload.model,
                metrics,
                upstream.status_code,
                start,
                (perf_counter() - provider_start) * 1000,
                usage,
            )
            return Response(
                content=body, status_code=upstream.status_code, media_type="application/json"
            )
        except (httpx.HTTPError, TimeoutError) as exc:
            await record_usage(request, principal, payload.model, metrics, 502, start)
            raise HTTPException(502, "Provider response interrupted") from exc
    finally:
        if not stream_handed_off:

            async def cleanup_request() -> None:
                try:
                    if upstream is not None:
                        await upstream.aclose()
                finally:
                    await release_concurrency(request, principal, lease)

            await asyncio.shield(cleanup_request())

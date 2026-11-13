import asyncio
from time import perf_counter
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from app.compression.base import Mode
from app.compression.router import CompressionPolicy, CompressionRouter, UnsupportedModeError
from app.compression.tokenizer import UnknownModelError
from app.core.rate_limit import acquire_concurrency, limit_principal, release_concurrency
from app.core.security import Principal, authenticate
from app.schemas.chat import StrictModel
from app.services.optimization import OptimizationMetrics
from app.services.usage import record_usage

router = APIRouter()


class OptimizeRequest(StrictModel):
    model: str = Field(min_length=1, max_length=200)
    text: str = Field(max_length=200000)
    strategy: Mode = "algorithmic"


@router.post("/optimize")
async def optimize(
    payload: OptimizeRequest,
    request: Request,
    principal: Annotated[Principal, Depends(authenticate)],
) -> dict[str, Any]:
    start = perf_counter()
    await limit_principal(request, principal, preview=True)
    lease = await acquire_concurrency(request, principal)
    try:
        result = await run_in_threadpool(
            CompressionRouter(
                CompressionPolicy(
                    min_saved_tokens=principal.min_saved_tokens,
                    min_saved_percent=principal.min_saved_percent,
                )
            ).optimize,
            payload.text,
            payload.model,
            payload.strategy,
        )
        metrics = OptimizationMetrics(
            original_tokens=result["original_tokens"],
            forwarded_tokens=result["optimized_tokens"],
            optimized=result["applied"],
            attempted=payload.strategy == "algorithmic",
            compression_failed=result["skip_reason"] == "compression_error",
            optimization_latency_ms=result["optimization_latency_ms"],
            rules=result["rules_applied"],
            skip_reason=result["skip_reason"],
        )
        await record_usage(
            request, principal, payload.model, metrics, 200, start, endpoint="preview"
        )
        return result
    except (UnknownModelError, UnsupportedModeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        await asyncio.shield(release_concurrency(request, principal, lease))

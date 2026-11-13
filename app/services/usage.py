import logging
from time import perf_counter
from typing import Any

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from app.core.security import Principal
from app.db.models import OptimizationResult, UsageRecord
from app.services.optimization import OptimizationMetrics

logger = logging.getLogger(__name__)


async def record_usage(
    request: Request,
    principal: Principal,
    model: str,
    metrics: OptimizationMetrics,
    status: int,
    start: float,
    provider_ms: float = 0,
    usage: dict[str, Any] | None = None,
    endpoint: str = "chat",
) -> None:
    def usage_count(name: str) -> int | None:
        value = (usage or {}).get(name)
        return (
            value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
        )

    try:
        async with request.app.state.sessions() as session:
            row = UsageRecord(
                tenant_id=principal.tenant_id,
                api_key_id=principal.key_id,
                request_id=request.state.request_id,
                endpoint=endpoint,
                model=model,
                status_code=status,
                original_tokens=metrics.original_tokens,
                forwarded_tokens=metrics.forwarded_tokens,
                optimized=metrics.optimized,
                attempted=metrics.attempted,
                compression_failed=metrics.compression_failed,
                optimization_latency_ms=metrics.optimization_latency_ms,
                gateway_latency_ms=(perf_counter() - start) * 1000,
                provider_latency_ms=provider_ms,
                provider_input_tokens=usage_count("prompt_tokens"),
                provider_output_tokens=usage_count("completion_tokens"),
            )
            session.add(row)
            await session.flush()
            session.add(
                OptimizationResult(
                    usage_id=row.id,
                    rules=metrics.rules,
                    skip_reason=metrics.skip_reason,
                    estimated_net_savings=metrics.estimated_net_savings,
                )
            )
            await session.commit()
    except SQLAlchemyError:
        logger.error("usage_write_failed")

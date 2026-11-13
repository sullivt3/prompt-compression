from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import String, case, cast, func, select

from app.compression.rules import APPROVED_RULES
from app.core.rate_limit import limit_principal
from app.core.security import Principal, authenticate
from app.db.models import OptimizationResult, UsageRecord

router = APIRouter()


@router.get("/usage")
async def usage(
    request: Request,
    principal: Annotated[Principal, Depends(authenticate)],
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    await limit_principal(request, principal)
    end = end or datetime.now(UTC)
    start = start or end - timedelta(days=30)
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise HTTPException(422, "Use timezone-aware start < end; end is exclusive")
    if end - start > timedelta(days=366):
        raise HTTPException(422, "Maximum analytics window is 366 days")

    def count_if(expression: Any) -> Any:
        return func.coalesce(func.sum(case((expression, 1), else_=0)), 0)

    columns = [
        func.count(UsageRecord.id).label("total_requests"),
        count_if(UsageRecord.optimized).label("optimized_requests"),
        count_if(UsageRecord.attempted).label("compression_attempts"),
        count_if(UsageRecord.compression_failed).label("compression_failures"),
        count_if(UsageRecord.status_code >= 400).label("errors"),
        func.coalesce(func.sum(UsageRecord.original_tokens), 0).label("estimated_original_tokens"),
        func.coalesce(func.sum(UsageRecord.forwarded_tokens), 0).label(
            "estimated_forwarded_tokens"
        ),
        func.sum(UsageRecord.provider_input_tokens).label("provider_reported_input_tokens"),
        func.sum(UsageRecord.provider_output_tokens).label("provider_reported_output_tokens"),
        func.coalesce(func.avg(UsageRecord.optimization_latency_ms), 0).label(
            "optimization_latency_ms"
        ),
        func.coalesce(func.avg(UsageRecord.gateway_latency_ms), 0).label("gateway_latency_ms"),
        func.coalesce(func.avg(UsageRecord.provider_latency_ms), 0).label("provider_latency_ms"),
    ]
    rule_columns = [
        count_if(cast(OptimizationResult.rules, String).contains(f'"{rule}"')).label(rule)
        for rule in sorted(APPROVED_RULES)
    ]
    async with request.app.state.sessions() as session:
        result = (
            (
                await session.execute(
                    select(*columns, *rule_columns)
                    .outerjoin(OptimizationResult, UsageRecord.id == OptimizationResult.usage_id)
                    .where(
                        UsageRecord.tenant_id == principal.tenant_id,
                        UsageRecord.created_at >= start,
                        UsageRecord.created_at < end,
                    )
                )
            )
            .mappings()
            .one()
        )
    data = dict(result)
    rules = {rule: data.pop(rule) for rule in sorted(APPROVED_RULES)}
    saved = data["estimated_original_tokens"] - data["estimated_forwarded_tokens"]
    total = data["total_requests"]
    return {
        **data,
        "pass_through_requests": total - data["optimized_requests"],
        "compression_successes": data["optimized_requests"],
        "estimated_tokens_saved": saved,
        "estimated_reduction_percent": 100 * saved / data["estimated_original_tokens"]
        if data["estimated_original_tokens"]
        else 0,
        "error_rate": data["errors"] / total if total else 0,
        "rule_effectiveness": rules,
        "latencies_are_averages": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "includes_endpoints": ["chat", "preview"],
        "estimate": True,
    }

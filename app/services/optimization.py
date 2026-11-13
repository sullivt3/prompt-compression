from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal
from time import perf_counter
from typing import Any, cast

from app.compression.base import CompressionContext, Mode
from app.compression.economics import evaluate_cost
from app.compression.router import CompressionPolicy, CompressionRouter
from app.compression.tokenizer import UnknownModelError
from app.core.config import Settings
from app.core.security import Principal


@dataclass
class OptimizationMetrics:
    original_tokens: int = 0
    forwarded_tokens: int = 0
    optimized: bool = False
    attempted: bool = False
    compression_failed: bool = False
    optimization_latency_ms: float = 0
    rules: list[str] = field(default_factory=list)
    skip_reason: str | None = "disabled"
    estimated_net_savings: float | None = None


def optimize_request(
    payload: dict[str, Any], principal: Principal, settings: Settings | None = None
) -> tuple[dict[str, Any], OptimizationMetrics]:
    start = perf_counter()
    metrics = OptimizationMetrics(attempted=principal.compression_mode == "algorithmic")
    try:
        router = CompressionRouter(
            CompressionPolicy(
                min_saved_tokens=principal.min_saved_tokens,
                min_saved_percent=principal.min_saved_percent,
            )
        )
        metrics.original_tokens = router.counter.count_request(payload)
        metrics.forwarded_tokens = metrics.original_tokens
        if principal.compression_mode == "off":
            return payload, metrics
        if principal.compression_mode != "algorithmic":
            metrics.skip_reason = "unsupported_mode"
            return payload, metrics
        candidate = deepcopy(payload)
        reasons: list[str] = []
        for message in candidate["messages"]:
            if message["role"] != "user":
                continue
            result = router.optimize(
                message["content"], payload["model"], cast(Mode, principal.compression_mode)
            )
            message["content"] = result["optimized"]
            metrics.rules.extend(result["rules_applied"])
            if result["skip_reason"]:
                reasons.append(result["skip_reason"])
                metrics.compression_failed |= result["skip_reason"] == "compression_error"
        valid = router.validator.validate_request(
            payload, candidate, CompressionContext(payload["model"])
        )
        forwarded = router.counter.count_request(candidate)
        if valid.valid and forwarded < metrics.original_tokens:
            pricing = settings.pricing.get(payload["model"]) if settings else None
            if pricing is not None and settings is not None:
                # Use cheaper input pricing: cache eligibility is unknown.
                cost = Decimal(str(perf_counter() - start)) * settings.local_compute_cost_per_second
                estimate = evaluate_cost(
                    pricing,
                    metrics.original_tokens - forwarded,
                    cost,
                    cached=(
                        pricing.cached_input_per_million is not None
                        and pricing.cached_input_per_million < pricing.input_per_million
                    ),
                )
                metrics.estimated_net_savings = float(estimate.net_savings)
                if estimate.net_savings <= 0:
                    metrics.rules = []
                    metrics.skip_reason = "nonpositive_net_savings"
                    return payload, metrics
            metrics.optimized = True
            metrics.forwarded_tokens = forwarded
            metrics.skip_reason = None
            return candidate, metrics
        metrics.rules = []
        metrics.skip_reason = reasons[0] if reasons else "no_valid_candidate"
        return payload, metrics
    except UnknownModelError:
        metrics.skip_reason = "unknown_tokenizer"
        return payload, metrics
    except Exception:
        metrics.compression_failed = True
        metrics.skip_reason = "compression_error"
        metrics.rules = []
        return payload, metrics
    finally:
        metrics.optimization_latency_ms = (perf_counter() - start) * 1000

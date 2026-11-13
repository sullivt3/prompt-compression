from dataclasses import asdict, dataclass, replace
from time import perf_counter
from typing import Any

from app.compression.base import CompressionContext, CompressionResult, Mode, ValidationResult
from app.compression.rules import RuleCompressor
from app.compression.tokenizer import TiktokenCounter
from app.compression.validator import CompressionValidator


class UnsupportedModeError(ValueError):
    pass


@dataclass(frozen=True)
class CompressionPolicy:
    min_saved_tokens: int = 2
    min_saved_percent: float = 1.0
    medium_tokens: int = 500
    large_tokens: int = 2000

    def __post_init__(self) -> None:
        if (
            self.min_saved_tokens < 1
            or not 0 <= self.min_saved_percent <= 100
            or not 0 < self.medium_tokens < self.large_tokens
        ):
            raise ValueError("Invalid compression policy")


class CompressionRouter:
    def __init__(self, policy: CompressionPolicy | None = None) -> None:
        self.policy = policy or CompressionPolicy()
        self.counter = TiktokenCounter()
        self.validator = CompressionValidator(self.counter)

    def optimize(
        self, text: str, model: str, strategy: Mode = "algorithmic", role: str = "user"
    ) -> dict[str, Any]:
        if strategy not in {"off", "algorithmic"}:
            raise UnsupportedModeError("Semantic and hybrid compression are not implemented")
        start = perf_counter()
        original_tokens = self.counter.count_text(text, model)
        context = CompressionContext(model, role)
        try:
            candidate = (
                RuleCompressor().compress(text, context)
                if strategy != "off"
                else CompressionResult(text, text, skip_reason="disabled")
            )
            valid = (
                self.validator.validate(
                    candidate, context, self.policy.min_saved_tokens, self.policy.min_saved_percent
                )
                if strategy != "off"
                else ValidationResult(False, reason="disabled")
            )
        except Exception:
            candidate = CompressionResult(text, text, skip_reason="compression_error")
            valid = ValidationResult(False, reason="compression_error")
        applied = strategy == "algorithmic" and valid.valid
        optimized = candidate.optimized if applied else text
        optimized_tokens = self.counter.count_text(optimized, model)
        saved = original_tokens - optimized_tokens
        reason = (
            "disabled"
            if strategy == "off"
            else candidate.skip_reason or (None if applied else valid.reason)
        )
        return {
            "original": text,
            "optimized": optimized,
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "saved_tokens": saved,
            "reduction_percent": 100 * saved / original_tokens if original_tokens else 0.0,
            "applied": applied,
            "strategy": strategy,
            "rules_applied": [t.rule for t in candidate.transformations] if applied else [],
            "transformations": [
                asdict(replace(t, validation_succeeded=True)) for t in candidate.transformations
            ]
            if applied
            else [],
            "validation_passed": valid.valid if strategy != "off" else False,
            "validation": asdict(valid),
            "skip_reason": reason,
            "estimate": True,
            "tokenizer": self.counter.encoding(model).name,
            "size_class": (
                "large"
                if original_tokens > self.policy.large_tokens
                else "medium"
                if original_tokens >= self.policy.medium_tokens
                else "small"
            ),
            "future_semantic_eligible": original_tokens >= self.policy.medium_tokens,
            "detected_repetitions": candidate.detected_repetitions,
            "optimization_latency_ms": (perf_counter() - start) * 1000,
        }

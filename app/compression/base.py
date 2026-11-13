from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["off", "algorithmic", "semantic", "hybrid"]


@dataclass(frozen=True)
class CompressionContext:
    model: str
    role: str = "user"
    enabled_rules: frozenset[str] = frozenset(
        {
            "greeting_removal",
            "gratitude_removal",
            "gratitude_closing",
            "apology_removal",
            "conversational_filler",
            "redundant_introduction",
            "request_wrapper",
            "test_introduction",
            "explanation_phrase",
            "purpose_phrase",
            "whitespace",
        }
    )


@dataclass(frozen=True)
class Transformation:
    rule: str
    start: int
    end: int
    original: str
    replacement: str
    reason: str
    risk: str = "low"
    validation_succeeded: bool = False


@dataclass(frozen=True)
class CompressionResult:
    original: str
    optimized: str
    transformations: tuple[Transformation, ...] = ()
    skip_reason: str | None = None
    detected_repetitions: int = 0


class Compressor(ABC):
    @abstractmethod
    def compress(self, text: str, context: CompressionContext) -> CompressionResult:
        raise NotImplementedError


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    checks: dict[str, bool] = field(default_factory=dict)
    reason: str = "validated"

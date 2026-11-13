"""Future extension contract. No inference service is implemented or invoked."""

from abc import abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.compression.base import CompressionContext, CompressionResult, Compressor


@dataclass(frozen=True)
class SemanticEstimate:
    estimated_inference_cost: Decimal
    estimated_saved_tokens: int
    quality_evaluation_required: bool = True


class SemanticCompressor(Compressor):
    @abstractmethod
    def estimate(self, text: str, context: CompressionContext) -> SemanticEstimate:
        """Estimate cost before explicit opt-in inference; never bill during estimation."""
        raise NotImplementedError

    @abstractmethod
    def compress(self, text: str, context: CompressionContext) -> CompressionResult:
        """Future adapters must preserve constraints and reject uncertain candidates."""
        raise NotImplementedError

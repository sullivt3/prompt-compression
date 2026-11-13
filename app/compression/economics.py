from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ModelPricing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    input_per_million: Decimal = Field(ge=0)
    output_per_million: Decimal = Field(ge=0)
    cached_input_per_million: Decimal | None = Field(default=None, ge=0)
    currency: str = "USD"
    effective_date: str


@dataclass(frozen=True)
class CostEstimate:
    gross_savings: Decimal
    compression_cost: Decimal
    net_savings: Decimal
    currency: str
    estimate: bool = True


def evaluate_cost(
    pricing: ModelPricing,
    saved_tokens: int,
    compression_cost: Decimal = Decimal(0),
    cached: bool = False,
) -> CostEstimate:
    if saved_tokens < 0 or compression_cost < 0:
        raise ValueError("Tokens and costs must be nonnegative")
    price = pricing.cached_input_per_million if cached else pricing.input_per_million
    if price is None:
        raise ValueError("Cached input pricing is unavailable")
    gross = Decimal(saved_tokens) * price / Decimal(1000000)
    return CostEstimate(gross, compression_cost, gross - compression_cost, pricing.currency)

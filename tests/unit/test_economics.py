from decimal import Decimal

from app.compression.economics import ModelPricing, evaluate_cost
from app.core.config import Settings
from app.core.security import Principal
from app.services.optimization import optimize_request


def test_economics() -> None:
    # Synthetic fixtures, not actual provider prices.
    pricing = ModelPricing(
        input_per_million="2",
        output_per_million="6",
        cached_input_per_million="0.5",
        effective_date="fixture",
    )
    assert evaluate_cost(pricing, 1000).gross_savings == Decimal("0.002")
    assert evaluate_cost(pricing, 1000, cached=True).gross_savings == Decimal("0.0005")
    assert evaluate_cost(pricing, 1000, Decimal("1")).net_savings < 0
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "user", "content": "Hey ChatGPT, can you please explain Kubernetes?"}
        ],
    }
    forwarded, metrics = optimize_request(
        payload,
        Principal("t", "k", "algorithmic"),
        Settings(pricing={"gpt-4.1-mini": pricing}, local_compute_cost_per_second="1000000"),
    )
    assert forwarded == payload
    assert metrics.skip_reason == "nonpositive_net_savings"

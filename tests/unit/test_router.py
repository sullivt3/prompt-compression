import pytest

from app.compression.router import CompressionPolicy, CompressionRouter, UnsupportedModeError


def test_routing() -> None:
    router = CompressionRouter()
    text = "Hey ChatGPT, can you please explain Kubernetes?"
    result = router.optimize(text, "gpt-4.1-mini")
    assert result["applied"]
    assert result["saved_tokens"] > 0
    assert result["optimized"] == "explain Kubernetes?"
    assert not router.optimize(text, "gpt-4.1-mini", "off")["applied"]
    assert not router.optimize(text, "gpt-4.1-mini", role="system")["applied"]
    assert not CompressionRouter(CompressionPolicy(min_saved_tokens=100)).optimize(
        text, "gpt-4.1-mini"
    )["applied"]
    for mode in ["semantic", "hybrid"]:
        with pytest.raises(UnsupportedModeError):
            router.optimize(text, "gpt-4.1-mini", mode)


def test_router_local_failure_returns_original() -> None:
    from unittest.mock import patch

    with patch("app.compression.router.RuleCompressor.compress", side_effect=RuntimeError):
        result = CompressionRouter().optimize("Hey ChatGPT, please explain Docker.", "gpt-4.1-mini")
    assert result["optimized"] == result["original"]
    assert result["skip_reason"] == "compression_error"

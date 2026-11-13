from hypothesis import given, settings
from hypothesis import strategies as st

from app.compression.base import CompressionContext
from app.compression.rules import RuleCompressor


@given(st.text(max_size=500))
@settings(max_examples=150)
def test_rule_idempotency_and_role_protection(text: str) -> None:
    engine = RuleCompressor()
    context = CompressionContext("gpt-4.1-mini")
    first = engine.compress(text, context)
    assert engine.compress(first.optimized, context).optimized == first.optimized
    assert engine.compress(text, CompressionContext(context.model, "system")).optimized == text


@given(st.sampled_from(["42", "never", '"exact"', "`code`", "https://example.com", "\n"]))
def test_protected_markers_bypass(marker: str) -> None:
    source = "Hey ChatGPT, please explain " + marker + " Docker."
    assert RuleCompressor().compress(source, CompressionContext("gpt-4.1-mini")).optimized == source

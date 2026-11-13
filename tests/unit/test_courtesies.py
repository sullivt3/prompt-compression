from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.compression.base import CompressionContext
from app.compression.router import CompressionRouter
from app.compression.rules import RuleCompressor
from app.compression.tokenizer import TiktokenCounter
from app.compression.validator import CompressionValidator

CONTEXT = CompressionContext("gpt-4.1-mini")


@pytest.mark.parametrize(
    ("text", "expected", "rule"),
    [
        ("Hello, explain Docker.", "explain Docker.", "greeting_removal"),
        ("Hi there! Explain Docker.", "Explain Docker.", "greeting_removal"),
        ("Good morning, explain Docker.", "explain Docker.", "greeting_removal"),
        ("Thanks, explain Docker.", "explain Docker.", "gratitude_removal"),
        ("Thank you for your help. Explain Docker.", "Explain Docker.", "gratitude_removal"),
        ("Explain Docker. Thanks!", "Explain Docker.", "gratitude_closing"),
        ("Explain Docker? Thank you in advance.", "Explain Docker?", "gratitude_closing"),
        ("Sorry, explain Docker.", "explain Docker.", "apology_removal"),
        ("Sorry to bother you. Explain Docker.", "Explain Docker.", "apology_removal"),
        ("Apologies for bothering you, explain Docker.", "explain Docker.", "apology_removal"),
    ],
)
def test_courtesy_rules(text: str, expected: str, rule: str) -> None:
    result = RuleCompressor().compress(text, CONTEXT)
    assert result.optimized == expected
    assert rule in [t.rule for t in result.transformations]
    assert RuleCompressor().compress(expected, CONTEXT).optimized == expected
    assert not any(
        t.rule == rule
        for t in RuleCompressor()
        .compress(text, replace(CONTEXT, enabled_rules=CONTEXT.enabled_rules - {rule}))
        .transformations
    )
    assert CompressionValidator(TiktokenCounter()).validate(result, CONTEXT).valid


@pytest.mark.parametrize(
    "text",
    [
        "Thanks!",
        "Sorry.",
        "Hello.",
        "I love you.",
        "I am sad. Explain how to cope.",
        "Explain how to support an anxious friend.",
        "Write a warm apology. Thanks.",
        "Write an affectionate letter to my partner.",
        "Explain why sorry matters. Thanks.",
        "Explain the word thanks. Thank you.",
        "Write a greeting. Hello.",
        'Say "Thanks!"',
        "Sorry for the data loss. Explain recovery options.",
        "Explain Docker. Thanks for clarifying networking.",
        "Explain Docker. Thank you for preserving backups.",
        "Explain Docker. Thanks to caching it runs faster.",
        "Thanks for nothing. Explain Docker.",
        "Thank you for your help with Docker.",
        "Never remove thanks from the response.",
        "Explain `Thanks!` and preserve the text.",
    ],
)
def test_emotional_context_and_task_material_remain(text: str) -> None:
    assert RuleCompressor().compress(text, CONTEXT).optimized == text


def test_courtesy_chain_metadata_and_roles() -> None:
    source = "Hi there, sorry to bother you, can you please explain Docker. Thanks!"
    result = RuleCompressor().compress(source, CONTEXT)
    assert result.optimized == "explain Docker."
    replay = source
    for change in result.transformations:
        assert replay[change.start : change.end] == change.original
        replay = replay[: change.start] + change.replacement + replay[change.end :]
    assert replay == result.optimized
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    for role in ["system", "developer", "assistant"]:
        assert RuleCompressor().compress(source, replace(CONTEXT, role=role)).optimized == source
    report = CompressionRouter().optimize(source, CONTEXT.model)
    assert report["applied"] and report["saved_tokens"] > 0


@given(
    st.lists(
        st.sampled_from(
            ["Hello, ", "Good evening, ", "Thanks, ", "Sorry to bother you, ", "Can you please "]
        ),
        min_size=1,
        max_size=6,
    ),
    st.sampled_from(["", " Thanks!", " Thank you in advance."]),
)
@settings(max_examples=80)
def test_courtesy_combinations_are_idempotent(prefixes: list[str], closing: str) -> None:
    text = "".join(prefixes) + "Explain Docker." + closing
    result = RuleCompressor().compress(text, CONTEXT)
    assert result.optimized == "Explain Docker."
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    assert CompressionValidator(TiktokenCounter()).validate(result, CONTEXT).valid

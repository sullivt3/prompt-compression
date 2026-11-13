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
USER_EXAMPLE = (
    "Paste a prompt below. This is just a test to see how many filler words "
    "can be removed form the input."
)


def test_user_example_compresses_and_validates() -> None:
    result = CompressionRouter().optimize(USER_EXAMPLE, CONTEXT.model)
    assert result["optimized"] == (
        "Paste a prompt below. This tests how many filler words can be removed form the input."
    )
    assert result["applied"] and result["validation_passed"]
    assert result["saved_tokens"] >= 2
    assert result["rules_applied"] == ["test_introduction"]
    change = result["transformations"][0]
    assert USER_EXAMPLE[change["start"] : change["end"]] == change["original"]
    assert change["replacement"] == "This tests"


@pytest.mark.parametrize(
    ("text", "expected", "rule"),
    [
        (
            "This is a test to check whether caching works.",
            "This tests whether caching works.",
            "test_introduction",
        ),
        (
            "The purpose of this test is to determine how caching works.",
            "This tests how caching works.",
            "test_introduction",
        ),
        ("I was wondering if you could explain Docker.", "explain Docker.", "request_wrapper"),
        (
            "Would you be able to compare Docker and Kubernetes?",
            "compare Docker and Kubernetes?",
            "request_wrapper",
        ),
        (
            "Explain Docker. I would appreciate it if you could describe Kubernetes.",
            "Explain Docker. describe Kubernetes.",
            "request_wrapper",
        ),
        (
            "Explain Docker! Can you please explain Kubernetes?",
            "Explain Docker! explain Kubernetes?",
            "conversational_filler",
        ),
    ],
)
def test_approved_sentence_rules(text: str, expected: str, rule: str) -> None:
    result = RuleCompressor().compress(text, CONTEXT)
    assert result.optimized == expected
    assert any(t.rule == rule for t in result.transformations)
    assert RuleCompressor().compress(expected, CONTEXT).optimized == expected
    assert (
        RuleCompressor()
        .compress(text, replace(CONTEXT, enabled_rules=CONTEXT.enabled_rules - {rule}))
        .optimized
        == text
    )
    assert CompressionValidator(TiktokenCounter()).validate(result, CONTEXT).valid


@pytest.mark.parametrize(
    "text",
    [
        "This is just a test to see the results.",
        "Explain why this is just a test to see how caching works.",
        "This is just a test. This is a real deployment.",
        "Would you be able to attend tomorrow?",
        "Explain how just and only differ.",
        'Discuss "This is just a test to see how caching works."',
        "This is just a test to see whether we must retain backups.",
        "This is just a test to see whether we never delete backups.",
        "This is just a test to see how 42 pods work.",
        "Rewrite this is just a test to see how caching works.",
        "Paste a prompt below. This is just a test to see how `code` works.",
        "This is just a test to see how https://example.com works.",
    ],
)
def test_unsafe_or_nonmatching_prose_is_preserved(text: str) -> None:
    assert RuleCompressor().compress(text, CONTEXT).optimized == text


@given(
    st.lists(
        st.sampled_from(
            [
                "Can you please explain Docker?",
                "This is just a test to see whether caching works.",
                "Would you be able to describe Kubernetes?",
                "I would like you to explain networking.",
                "Explain Docker.",
            ]
        ),
        min_size=1,
        max_size=12,
    )
)
@settings(max_examples=80)
def test_sentence_rules_are_idempotent_and_metadata_replays(sentences: list[str]) -> None:
    text = " ".join(sentences)
    result = RuleCompressor().compress(text, CONTEXT)
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    replay = text
    for change in result.transformations:
        assert replay[change.start : change.end] == change.original
        replay = replay[: change.start] + change.replacement + replay[change.end :]
    assert replay == result.optimized
    for role in ["system", "developer", "assistant"]:
        assert RuleCompressor().compress(text, replace(CONTEXT, role=role)).optimized == text

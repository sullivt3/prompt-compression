import pytest

from app.compression.base import CompressionContext
from app.compression.rules import RuleCompressor

CONTEXT = CompressionContext("gpt-4.1-mini")


@pytest.mark.parametrize(
    ("source", "expected", "rule"),
    [
        (
            "Hey ChatGPT, please explain Kubernetes.",
            "please explain Kubernetes.",
            "greeting_removal",
        ),
        (
            "Can you please help me write a Python function?",
            "write a Python function?",
            "conversational_filler",
        ),
        ("I would like you to explain Docker.", "explain Docker.", "redundant_introduction"),
        ("Explain  Kubernetes.", "Explain Kubernetes.", "whitespace"),
    ],
)
def test_rules(source: str, expected: str, rule: str) -> None:
    result = RuleCompressor().compress(source, CONTEXT)
    assert result.optimized == expected
    assert result.transformations[0].rule == rule
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    assert (
        RuleCompressor()
        .compress(source, CompressionContext("gpt-4.1-mini", enabled_rules=frozenset()))
        .optimized
        == source
    )


@pytest.mark.parametrize(
    "source",
    [
        'Hey ChatGPT, explain "hello".',
        "Can you please explain JSON?",
        "Hey ChatGPT, never delete backups.",
        "Explain 42 pods.",
        "Explain /etc/passwd",
        "Explain https://example.com",
        "Explain `kubectl get pods`",
        "Explain\n  code",
        "Translate hello to French.",
        "Hey ChatGPT, output a table.",
        "Hey ChatGPT, explain Kubernetes. Explain Kubernetes.",
    ],
)
def test_protection(source: str) -> None:
    result = RuleCompressor().compress(source, CONTEXT)
    if source.endswith("explain Kubernetes. Explain Kubernetes."):
        assert result.optimized.endswith("explain Kubernetes. Explain Kubernetes.")
    else:
        assert result.optimized == source


def test_roles_and_idempotency() -> None:
    text = "Hey ChatGPT, Can you please I would like you to explain  Docker."
    result = RuleCompressor().compress(text, CONTEXT)
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    for role in ["system", "developer", "assistant", "tool"]:
        assert (
            RuleCompressor().compress(text, CompressionContext(CONTEXT.model, role)).optimized
            == text
        )


def test_repetition_detection_and_transformation_budget() -> None:
    result = RuleCompressor().compress("Explain Docker. Explain Docker.", CONTEXT)
    assert result.detected_repetitions == 1
    text = "Hey ChatGPT, " * 100 + "please explain Docker."
    assert RuleCompressor().compress(text, CONTEXT).optimized == text

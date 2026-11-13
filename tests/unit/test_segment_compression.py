from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.compression.base import CompressionContext
from app.compression.eligibility import compression_plan
from app.compression.router import CompressionRouter
from app.compression.rules import RuleCompressor
from app.compression.tokenizer import TiktokenCounter
from app.compression.validator import CompressionValidator

CONTEXT = CompressionContext("gpt-4.1-mini")


@pytest.mark.parametrize(
    ("source", "expected", "rule"),
    [
        ("Provide an explanation of Docker.", "Explain Docker.", "explanation_phrase"),
        (
            "Please provide me with an explanation of Docker.",
            "Explain Docker.",
            "explanation_phrase",
        ),
        (
            "Can you please provide an explanation of Docker.",
            "Explain Docker.",
            "explanation_phrase",
        ),
        (
            "Explain Docker in order to understand containers.",
            "Explain Docker to understand containers.",
            "purpose_phrase",
        ),
    ],
)
def test_precise_phrase_rewrites(source: str, expected: str, rule: str) -> None:
    result = RuleCompressor().compress(source, CONTEXT)
    assert result.optimized == expected
    assert rule in [t.rule for t in result.transformations]
    assert RuleCompressor().compress(expected, CONTEXT).optimized == expected
    disabled = replace(CONTEXT, enabled_rules=CONTEXT.enabled_rules - {rule})
    assert not any(
        t.rule == rule for t in RuleCompressor().compress(source, disabled).transformations
    )
    assert CompressionValidator(TiktokenCounter()).validate(result, CONTEXT).valid


@pytest.mark.parametrize(
    "text",
    [
        "List the words in order to explain their meaning.",
        "Discuss the phrase in order to.",
        "The team met in order to discuss Docker.",
        "Provide an explanation of exactly three examples.",
        "Explain Docker in order to never expose passwords.",
        'Provide an explanation of "in order to".',
    ],
)
def test_phrase_rules_preserve_noninstruction_and_protected_text(text: str) -> None:
    assert RuleCompressor().compress(text, CONTEXT).optimized == text


@pytest.mark.parametrize(
    "protected",
    [
        (
            '```python\ndef example():\n    return "Can you please explain Docker?"'
            "\n\n# Never delete this\n```"
        ),
        "~~~sh\nkubectl get pods\n~~~",
        '{"replicas": 3, "enabled": true}',
        '"Can you please explain Docker?"',
        "'Can you please explain Docker?'",
        "`Can you please explain Docker?`",
        "replicas: 3\nenabled: true",
        "<config><replicas>3</replicas></config>",
        "Never delete backups. Keep three examples.",
        "https://example.com/a?x=3",
        "| name | value |\n| test | 42 |",
    ],
)
def test_protected_blocks_unchanged_and_transformations_replay(protected: str) -> None:
    source = (
        "Can you please explain Docker?\n\n"
        + protected
        + "\n\nProvide an explanation of networking in order to understand containers."
    )
    result = RuleCompressor().compress(source, CONTEXT)
    assert protected in result.optimized
    assert result.optimized.startswith("explain Docker?\n\n")
    assert result.optimized.endswith("Explain networking to understand containers.")
    replay = source
    for change in result.transformations:
        assert replay[change.start : change.end] == change.original
        replay = replay[: change.start] + change.replacement + replay[change.end :]
    assert replay == result.optimized
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    validator = CompressionValidator(TiktokenCounter())
    validation = validator.validate(result, CONTEXT)
    assert validation.valid and validation.checks["protected_content"]
    assert not validator.validate(
        replace(result, optimized=result.optimized.replace(protected, "Deleted content")), CONTEXT
    ).valid


@pytest.mark.parametrize(
    "protected",
    [
        '```python\nprint("hello")',
        "~~~sh\necho hello",
        '"a quote that never closes',
        "'a quote that never closes",
        "`a code span that never closes",
        '{"replicas": 3',
        '    {"replicas": 3',
        "<config><value>3</config>",
        '<!DOCTYPE data [<!ENTITY test "text">]><data>&test;</data>',
        "Rewrite the following text.",
        "Preserve every word above.",
        "Proofread the following passage.",
    ],
)
def test_ambiguous_boundaries_and_exact_tasks_bypass_whole_message(protected: str) -> None:
    source = "Can you please explain Docker?\n\n" + protected
    result = RuleCompressor().compress(source, CONTEXT)
    assert result.optimized == source
    assert not result.transformations


def test_no_cross_boundary_phrases_or_whitespace_changes() -> None:
    source = "Provide an explanation\n\nof Docker.\n\n```text\na  b\r\n  c\n```\n"
    assert RuleCompressor().compress(source, CONTEXT).optimized == source
    crlf = "Can you please explain Docker?\r\n```text\r\n  a  b\r\n```\r\n"
    result = RuleCompressor().compress(crlf, CONTEXT)
    assert result.optimized == "explain Docker?\r\n```text\r\n  a  b\r\n```\r\n"


@given(st.text(alphabet=st.characters(blacklist_characters="`~"), max_size=300))
@settings(max_examples=100)
def test_arbitrary_fenced_payload_is_preserved(payload: str) -> None:
    protected = "```text\n" + payload + "\n```"
    source = "Can you please explain Docker?\n\n" + protected
    result = RuleCompressor().compress(source, CONTEXT)
    assert protected in result.optimized
    assert RuleCompressor().compress(result.optimized, CONTEXT).optimized == result.optimized
    for role in ["system", "developer", "assistant"]:
        assert RuleCompressor().compress(source, replace(CONTEXT, role=role)).optimized == source


def test_partition_covers_entire_message_and_router_savings() -> None:
    source = 'Can you please explain Docker?\n\n```sh\necho "hello"\n```\n\nNever delete backups.'
    plan = compression_plan(source, CONTEXT)
    assert "".join(source[r.start : r.end] for r in plan.regions) == source
    assert plan.skip_reason is None
    result = CompressionRouter().optimize(source, CONTEXT.model)
    assert result["applied"] and result["saved_tokens"] > 0
    assert result["validation"]["checks"]["protected_content"]
    original = {"model": CONTEXT.model, "messages": [{"role": "user", "content": source}]}
    changed = {**original, "messages": [{"role": "user", "content": result["optimized"]}]}
    validator = CompressionValidator(TiktokenCounter())
    assert validator.validate_request(original, changed, CONTEXT).valid
    changed["messages"][0]["content"] = changed["messages"][0]["content"].replace("hello", "oops")
    assert not validator.validate_request(original, changed, CONTEXT).valid


def test_exact_task_material_is_protected_even_without_blank_lines() -> None:
    text = "Proofread the following passage. Provide an explanation of Docker."
    assert RuleCompressor().compress(text, CONTEXT).optimized == text


def test_indented_ambiguous_content_is_not_whitespace_normalized() -> None:
    protected = "    pass"
    source = "Can you please explain Docker?\n\n" + protected
    result = RuleCompressor().compress(source, CONTEXT)
    assert result.optimized.endswith(protected)
    assert RuleCompressor().compress(protected, CONTEXT).optimized == protected

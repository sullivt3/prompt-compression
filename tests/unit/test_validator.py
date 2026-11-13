from dataclasses import replace

from app.compression.base import CompressionContext
from app.compression.rules import RuleCompressor
from app.compression.tokenizer import TiktokenCounter
from app.compression.validator import CompressionValidator


def test_validation_rejects_tampering() -> None:
    context = CompressionContext("gpt-4.1-mini")
    result = RuleCompressor().compress("Hey ChatGPT, please explain Kubernetes.", context)
    validator = CompressionValidator(TiktokenCounter())
    assert validator.validate(result, context).valid
    assert not validator.validate(replace(result, optimized="Delete everything"), context).valid
    assert not validator.validate(result, context, min_tokens=100).valid
    original = {
        "model": context.model,
        "messages": [{"role": "system", "content": "Hey ChatGPT, explain Docker."}],
    }
    candidate = {
        "model": context.model,
        "messages": [{"role": "system", "content": "explain Docker."}],
    }
    assert not validator.validate_request(original, candidate, context).valid
    assert validator.validate_request(original, original, context).valid
    assert not validator.validate_request(original, {**original, "temperature": 1}, context).valid

from typing import Any

from app.compression.base import CompressionContext, CompressionResult, ValidationResult
from app.compression.eligibility import protected_regions_unchanged, skip_reason
from app.compression.rules import APPROVED_RULES, RuleCompressor
from app.compression.tokenizer import TokenCounter


class CompressionValidator:
    def __init__(self, counter: TokenCounter) -> None:
        self.counter = counter

    def validate(
        self,
        result: CompressionResult,
        context: CompressionContext,
        min_tokens: int = 1,
        min_percent: float = 0,
    ) -> ValidationResult:
        original = self.counter.count_text(result.original, context.model)
        optimized = self.counter.count_text(result.optimized, context.model)
        replay = RuleCompressor().compress(result.original, context)
        checks = {
            "protected_content": skip_reason(result.original, context) is None
            and protected_regions_unchanged(result.original, result.optimized, context),
            "approved_rules": all(
                t.rule in APPROVED_RULES & context.enabled_rules for t in result.transformations
            ),
            "transformation_replay": replay == result,
            "token_reduction": optimized < original,
            "minimum_savings": original - optimized >= min_tokens
            and (100 * (original - optimized) / original if original else 0) >= min_percent,
        }
        valid = all(checks.values())
        return ValidationResult(valid, checks, "validated" if valid else "validation_failed")

    def validate_request(
        self, original: dict[str, Any], candidate: dict[str, Any], context: CompressionContext
    ) -> ValidationResult:
        original_fields = {k: v for k, v in original.items() if k != "messages"}
        candidate_fields = {k: v for k, v in candidate.items() if k != "messages"}
        structure = len(original["messages"]) == len(candidate["messages"])
        content = structure
        if structure:
            for source, target in zip(original["messages"], candidate["messages"], strict=True):
                structure &= {k: v for k, v in source.items() if k != "content"} == {
                    k: v for k, v in target.items() if k != "content"
                }
                if source["content"] != target["content"]:
                    expected = RuleCompressor().compress(
                        source["content"],
                        CompressionContext(context.model, source["role"], context.enabled_rules),
                    )
                    content &= expected.optimized == target["content"] and bool(
                        expected.transformations
                    )
        checks = {
            "message_structure": structure,
            "non_targeted_fields": original_fields == candidate_fields,
            "approved_content": content,
        }
        return ValidationResult(all(checks.values()), checks)

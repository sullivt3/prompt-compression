import re
from dataclasses import dataclass

from app.compression.base import (
    CompressionContext,
    CompressionResult,
    Compressor,
    Transformation,
)
from app.compression.eligibility import skip_reason


@dataclass(frozen=True)
class Rule:
    identifier: str
    description: str
    pattern: str
    risk: str = "low"


RULES = (
    Rule(
        "greeting_removal",
        "Remove an explicit leading assistant greeting",
        r"\A(?:Hey|Hello|Hi) ChatGPT, +",
    ),
    Rule(
        "conversational_filler",
        "Remove a narrowly defined leading request wrapper",
        r"\A(?:Can you please (?:help me )?|Could you please (?:help me )?)",
    ),
    Rule(
        "redundant_introduction",
        "Remove an explicit leading request introduction",
        r"\AI would like you to +",
    ),
    Rule("whitespace", "Collapse repeated ASCII spaces in eligible plain prose", r" {2,}"),
)
APPROVED_RULES = frozenset(rule.identifier for rule in RULES)
ACTION = re.compile(
    r"(?:please )?(?:explain|describe|write|list|compare|define|show|give|tell)\b", re.I
)


class RuleCompressor(Compressor):
    def compress(self, text: str, context: CompressionContext) -> CompressionResult:
        reason = skip_reason(text, context)
        if reason:
            return CompressionResult(text, text, skip_reason=reason)
        candidate = text
        changes: list[Transformation] = []
        # Fixed point makes cascaded prefix removal deterministic and idempotent.
        while True:
            before = candidate
            for rule in RULES:
                if rule.identifier not in context.enabled_rules:
                    continue
                matches = list(re.finditer(rule.pattern, candidate, re.IGNORECASE))
                # Each transformation records offsets relative to its input candidate.
                for match in reversed(matches):
                    replacement = " " if rule.identifier == "whitespace" else ""
                    suffix = candidate[match.end() :]
                    if rule.identifier != "whitespace" and not (
                        ACTION.match(suffix)
                        or any(re.match(r.pattern, suffix, re.I) for r in RULES[:3])
                    ):
                        continue
                    changes.append(
                        Transformation(
                            rule.identifier,
                            match.start(),
                            match.end(),
                            match.group(),
                            replacement,
                            rule.description,
                        )
                    )
                    candidate = candidate[: match.start()] + replacement + suffix
            if len(changes) > 32:
                return CompressionResult(text, text, skip_reason="transformation_budget")
            if candidate == before:
                break
        segments = [s.strip() for s in re.findall(r"[^.!?]+[.!?]?", text)]
        repeats = len(segments) - len(set(segments))
        return CompressionResult(
            text,
            candidate,
            tuple(changes),
            None if changes else "no_approved_transformation",
            repeats,
        )

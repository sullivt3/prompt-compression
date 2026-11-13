import re
from dataclasses import dataclass, replace

from app.compression.base import (
    CompressionContext,
    CompressionResult,
    Compressor,
    Transformation,
)
from app.compression.eligibility import compression_plan


@dataclass(frozen=True)
class Rule:
    identifier: str
    description: str
    pattern: str
    risk: str = "low"
    replacement: str = ""
    requires_action: bool = True
    sentence_start: bool = True
    instruction_only: bool = False
    preceding_action: bool = False
    courtesy: bool = False


RULES = (
    Rule(
        "greeting_removal",
        "Remove an explicit leading assistant greeting",
        r"\A(?:(?:Hey|Hello|Hi)(?: (?:ChatGPT|there|assistant))?|"
        r"Good (?:morning|afternoon|evening))(?:, +|[.!] +)",
        courtesy=True,
    ),
    Rule(
        "gratitude_removal",
        "Remove a separate conversational thanks before an instruction",
        r"\A(?:Thanks(?: (?:so|very) much)?|Thank you(?: (?:so|very) much)?)"
        r"(?: in advance| for your help)?(?:, +|[.!] +)",
        courtesy=True,
    ),
    Rule(
        "gratitude_closing",
        "Remove a standalone closing thanks after an instruction",
        r"(?<=[.!?]) +(?:Thanks(?: (?:so|very) much)?|Thank you(?: (?:so|very) much)?)"
        r"(?: in advance| for your help)?[.!]?\Z",
        requires_action=False,
        sentence_start=False,
        preceding_action=True,
        courtesy=True,
    ),
    Rule(
        "apology_removal",
        "Remove a courtesy apology directly before an instruction",
        r"\A(?:Sorry|Sorry to bother you|Apologies for bothering you)(?:, +|[.!] +)",
        courtesy=True,
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
    Rule(
        "request_wrapper",
        "Remove an approved indirect request wrapper before a known action",
        r"\A(?:I was wondering if you could |Would you be able to |"
        r"I would appreciate it if you could )",
    ),
    Rule(
        "test_introduction",
        "Shorten an explicit test-purpose wrapper while retaining the test objective",
        r"\A(?:This is (?:just )?a test to (?:see|check|determine)|"
        r"The purpose of this test is to (?:see|check|determine))(?= (?:how|whether|if)\b)",
        replacement="This tests",
        requires_action=False,
    ),
    Rule(
        "explanation_phrase",
        "Shorten a leading request for an explanation",
        r"\A(?:Please )?provide (?:me with )?an explanation of +(?=[A-Za-z])",
        replacement="Explain ",
        requires_action=False,
    ),
    Rule(
        "purpose_phrase",
        "Shorten a purpose clause within an affirmative instruction",
        r"\bin order to\b(?= [A-Za-z])",
        replacement="to",
        requires_action=False,
        sentence_start=False,
        instruction_only=True,
    ),
    Rule(
        "whitespace",
        "Collapse repeated ASCII spaces in eligible plain prose",
        r" {2,}",
        replacement=" ",
        requires_action=False,
        sentence_start=False,
    ),
)
APPROVED_RULES = frozenset(rule.identifier for rule in RULES)
ACTION = re.compile(
    r"(?:please )?(?:explain|describe|write|list|compare|define|show|give|tell|provide)\b", re.I
)


# Do not mistake requested dialogue, tone, emotional context, or examples for courtesies.
COURTESY_CONTEXT = re.compile(
    r"\b(?:say|says|include|append|greet|greeting|greetings|word|words|phrase|term|"
    r"dialogue|conversation|apology|apologies|sorry|thanks|thank|gratitude|affection|"
    r"emotion|emotional|tone|love|sad|anxious|depressed|distressed)\b|"
    r"\b(?:start|end|respond|reply) with\b",
    re.I,
)


def has_action(text: str) -> bool:
    return any(
        ACTION.match(text, pos=position)
        for position in [0, *(m.end() for m in re.finditer(r"[.!?] +", text))]
    )


def courtesy_task_context(text: str) -> str:
    """Inspect the task after excluding only the approved courtesy forms themselves."""
    for _ in range(32):
        before = text
        for rule in RULES:
            if rule.courtesy and rule.preceding_action:
                text = re.sub(rule.pattern, "", text, flags=re.I, count=1)
            elif rule.requires_action:
                text = re.sub(rule.pattern, "", text, flags=re.I, count=1)
        if text == before:
            break
    return text


class RuleCompressor(Compressor):
    def compress(self, text: str, context: CompressionContext) -> CompressionResult:
        plan = compression_plan(text, context)
        if plan.skip_reason:
            return CompressionResult(text, text, skip_reason=plan.skip_reason)
        candidate = text
        changes: list[Transformation] = []
        repetitions = 0
        for region in reversed(plan.regions):
            if not region.eligible:
                continue
            result = self._compress_prose(text[region.start : region.end], context)
            if result.skip_reason == "transformation_budget":
                return CompressionResult(text, text, skip_reason="transformation_budget")
            changes.extend(
                replace(t, start=t.start + region.start, end=t.end + region.start)
                for t in result.transformations
            )
            if len(changes) > 32:
                return CompressionResult(text, text, skip_reason="transformation_budget")
            repetitions += result.detected_repetitions
            candidate = candidate[: region.start] + result.optimized + candidate[region.end :]
        return CompressionResult(
            text,
            candidate,
            tuple(changes),
            None if changes else "no_approved_transformation",
            repetitions,
        )

    def _compress_prose(self, text: str, context: CompressionContext) -> CompressionResult:
        candidate = text
        changes: list[Transformation] = []
        # Fixed point makes cascaded prefix removal deterministic and idempotent.
        while True:
            before = candidate
            for rule in RULES:
                if rule.identifier not in context.enabled_rules:
                    continue
                # Prefix rules run only at message/sentence boundaries, never arbitrary words.
                starts = [0, *(m.end() for m in re.finditer(r"[.!?] +", candidate))]
                matches: list[tuple[int, int]] = []
                if rule.sentence_start:
                    pattern = re.compile(rule.pattern.removeprefix(r"\A"), re.IGNORECASE)
                    for start in starts:
                        match = pattern.match(candidate, pos=start)
                        if match:
                            matches.append((match.start(), match.end()))
                else:
                    matches = [
                        (m.start(), m.end()) for m in re.finditer(rule.pattern, candidate, re.I)
                    ]
                # Offsets refer to the candidate immediately before each transformation.
                for start, end in reversed(matches):
                    suffix = candidate[end:]
                    if rule.courtesy and COURTESY_CONTEXT.search(courtesy_task_context(candidate)):
                        continue
                    if rule.preceding_action and not has_action(candidate[:start]):
                        continue
                    if rule.instruction_only:
                        sentence_start = max(position for position in starts if position <= start)
                        following = next(
                            (position for position in starts if position > start), len(candidate)
                        )
                        sentence = candidate[sentence_start:following]
                        if not ACTION.match(sentence) or re.search(
                            r"\b(?:word|words|phrase|term|grammar|idiom|expression|sentence)\b",
                            sentence,
                            re.I,
                        ):
                            continue
                    if rule.requires_action and not (
                        ACTION.match(suffix)
                        or any(
                            r.requires_action and re.match(r.pattern, suffix, re.I) for r in RULES
                        )
                    ):
                        continue
                    changes.append(
                        Transformation(
                            rule.identifier,
                            start,
                            end,
                            candidate[start:end],
                            rule.replacement,
                            rule.description,
                            rule.risk,
                        )
                    )
                    if len(changes) > 32:
                        return CompressionResult(text, text, skip_reason="transformation_budget")
                    candidate = candidate[:start] + rule.replacement + suffix
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

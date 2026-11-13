import json
import re
from dataclasses import dataclass
from xml.etree import ElementTree

from app.compression.base import CompressionContext
from app.compression.protected_spans import ProtectedContentDetector


@dataclass(frozen=True)
class Region:
    start: int
    end: int
    eligible: bool
    kind: str


@dataclass(frozen=True)
class CompressionPlan:
    regions: tuple[Region, ...]
    skip_reason: str | None = None


def plain_skip_reason(text: str) -> str | None:
    if not text.strip():
        return "empty"
    if text.startswith((" ", "\t")):
        return "ambiguous_content"
    if EXACT_TASK.search(text) or ProtectedContentDetector().detect(text):
        return "protected_content"
    if not all(character.isalpha() or character in " .,!?-" for character in text):
        return "ambiguous_content"
    return None


# These instructions can make otherwise ordinary prose exact-match task material.
EXACT_TASK = re.compile(
    r"\b(?:verbatim|exact|exactly|preserve|retain|translate|rewrite|summarize|edit|"
    r"quote|repeat|transform|proofread|rephrase|paraphrase|transcribe)\b|"
    r"\bfollowing (?:text|document|passage|content|material|email|prompt)\b",
    re.I,
)
FENCE = re.compile(r"(?m)^ {0,3}(`{3,}|~{3,})([^\r\n]*)(?:\r?\n|$)")


def _ambiguous(block: str) -> bool:
    # Unbalanced delimiters cannot safely establish where task material ends.
    if len(re.findall(r'(?<!\\)"', block)) % 2:
        return True
    if block.count("“") != block.count("”") or block.count("‘") != block.count("’"):
        return True
    if len(re.findall(r"(?<![A-Za-z])'|'(?![A-Za-z])", block)) % 2:
        return True
    if "```" in block or "~~~" in block:
        return True
    if block.count("`") % 2:
        return True
    if re.search(r"[{}\[\]]", block):
        try:
            json.loads(block)
        except (ValueError, RecursionError):
            return True
    if "<" in block or ">" in block:
        # Never expand declarations/entities just to classify protected content.
        if "<!" in block or "<?" in block:
            return True
        try:
            ElementTree.fromstring(block)
        except ElementTree.ParseError:
            return True
    return False


def compression_plan(text: str, context: CompressionContext) -> CompressionPlan:
    if context.role != "user":
        return CompressionPlan((), "protected_role")
    reason = plain_skip_reason(text)
    if reason is None:
        return CompressionPlan((Region(0, len(text), True, "prose"),))
    if reason == "empty":
        return CompressionPlan((), reason)
    # Inline mixed content still bypasses; only independently delimited blocks qualify.
    if "\n" not in text:
        return CompressionPlan((Region(0, len(text), False, reason),), reason)
    regions: list[Region] = []
    outside: list[tuple[int, int]] = []
    cursor = 0
    while opening := FENCE.search(text, cursor):
        marker = opening.group(1)
        if marker[0] == "`" and "`" in opening.group(2):
            return CompressionPlan((), "ambiguous_protected_content")
        closing = re.compile(
            rf"(?m)^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*(?:\r?\n|$)"
        ).search(text, opening.end())
        if closing is None:
            return CompressionPlan((), "ambiguous_protected_content")
        outside.append((cursor, opening.start()))
        regions.append(Region(opening.start(), closing.end(), False, "code_fence"))
        cursor = closing.end()
    outside.append((cursor, len(text)))
    for start, end in outside:
        portion = text[start:end]
        if EXACT_TASK.search(portion):
            return CompressionPlan((), "protected_content")
        # Preserve paragraph separators and fence-adjacent line endings byte-for-byte.
        boundary = start
        for match in re.finditer(r"(?:\r?\n){2,}", portion):
            absolute = start + match.start()
            regions.extend(_paragraph_regions(text, boundary, absolute))
            regions.append(Region(absolute, start + match.end(), False, "separator"))
            boundary = start + match.end()
        regions.extend(_paragraph_regions(text, boundary, end))
    regions.sort(key=lambda region: region.start)
    for region in regions:
        if (
            not region.eligible
            and region.kind not in {"code_fence", "separator"}
            and _ambiguous(text[region.start : region.end])
        ):
            return CompressionPlan((), "ambiguous_protected_content")
    if any(region.eligible for region in regions):
        return CompressionPlan(tuple(regions))
    return CompressionPlan(tuple(regions), reason)


def _paragraph_regions(text: str, start: int, end: int) -> list[Region]:
    block = text[start:end]
    content = block.strip("\r\n")
    if not content:
        return [Region(start, end, False, "separator")] if block else []
    left = start + len(block) - len(block.lstrip("\r\n"))
    right = end - (len(block) - len(block.rstrip("\r\n")))
    reason = plain_skip_reason(content)
    return [
        Region(start, left, False, "separator"),
        Region(left, right, reason is None, reason or "prose"),
        Region(right, end, False, "separator"),
    ]


def skip_reason(text: str, context: CompressionContext) -> str | None:
    return compression_plan(text, context).skip_reason


def protected_regions_unchanged(original: str, candidate: str, context: CompressionContext) -> bool:
    source = compression_plan(original, context)
    target = compression_plan(candidate, context)
    if source.skip_reason or target.skip_reason or len(source.regions) != len(target.regions):
        return original == candidate
    return all(
        left.kind == right.kind
        and left.eligible == right.eligible
        and (left.eligible or original[left.start : left.end] == candidate[right.start : right.end])
        for left, right in zip(source.regions, target.regions, strict=True)
    )

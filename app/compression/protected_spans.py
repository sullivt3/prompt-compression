import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProtectedSpan:
    start: int
    end: int
    kind: str


class ProtectedContentDetector:
    """Conservative whole-message protection; classification is not a semantic proof."""

    patterns = (
        ("structured_or_exact", r"[`\"“”‘’{}\[\]<>|\\\n\r\t]"),
        ("quoted_or_contracted", r"'"),
        ("numeric", r"\d"),
        ("url_path_command", r"[/~$=]|https?\b|www\.|\b(?:sudo|kubectl|curl|bash|chmod|ssh)\b"),
        (
            "constraint",
            r"\b(?:no|not|never|without|except|only|must|shall|required|exact|exactly|"
            r"preserve|retain|verbatim|limit|maximum|minimum|avoid|don't|cannot|can't|"
            r"security|secure|password|secret|credential|token|format|output|json|yaml|xml|"
            r"markdown|csv|schema|translate|rewrite|summarize|edit|quote|repeat|transform)\b",
        ),
        ("structured_punctuation", r"[:;#*_@%&]"),
    )

    def detect(self, text: str) -> tuple[ProtectedSpan, ...]:
        return tuple(
            ProtectedSpan(match.start(), match.end(), kind)
            for kind, pattern in self.patterns
            for match in re.finditer(pattern, text, re.IGNORECASE)
        )

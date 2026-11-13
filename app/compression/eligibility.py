from app.compression.base import CompressionContext
from app.compression.protected_spans import ProtectedContentDetector


def skip_reason(text: str, context: CompressionContext) -> str | None:
    if context.role != "user":
        return "protected_role"
    if not text.strip():
        return "empty"
    if ProtectedContentDetector().detect(text):
        return "protected_content"
    # Restrict MVP rules to simple natural-language requests.
    if not all(character.isalpha() or character in " .,!?-" for character in text):
        return "ambiguous_content"
    return None

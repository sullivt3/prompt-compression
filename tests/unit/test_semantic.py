import pytest
from pydantic import ValidationError

from app.compression.router import CompressionRouter, UnsupportedModeError
from app.compression.semantic import SemanticCompressor
from app.core.config import Settings


def test_semantic_is_interface_only() -> None:
    with pytest.raises(TypeError):
        SemanticCompressor()
    for mode in ["semantic", "hybrid"]:
        with pytest.raises(UnsupportedModeError, match="not implemented"):
            CompressionRouter().optimize("Explain Docker.", "gpt-4.1-mini", mode)


def test_semantic_configuration_cannot_enable_inference() -> None:
    with pytest.raises(ValidationError, match="not implemented"):
        Settings(semantic_enabled=True)

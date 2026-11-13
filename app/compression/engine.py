"""Public, HTTP-independent compression entry point."""

from app.compression.router import CompressionPolicy, CompressionRouter

__all__ = ["CompressionPolicy", "CompressionRouter"]

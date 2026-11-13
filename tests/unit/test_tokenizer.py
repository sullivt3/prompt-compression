import pytest
import tiktoken

from app.compression.tokenizer import TiktokenCounter, UnknownModelError


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Hello, world!",
        "你好 🌍 café",
        "def f():\n    return 42",
        "Kubernetes kubectl StatefulSet " * 10000,
        "<|endoftext|>",
    ],
)
def test_tokenizer_matches_encoding(text: str) -> None:
    counter = TiktokenCounter()
    assert counter.count_text(text, "gpt-4.1-mini") == len(
        tiktoken.encoding_for_model("gpt-4.1-mini").encode(text, disallowed_special=())
    )


def test_unknown_model() -> None:
    with pytest.raises(UnknownModelError):
        TiktokenCounter().count_text("test", "unregistered-model")


def test_request_estimate() -> None:
    result = TiktokenCounter().analyze(
        {"model": "gpt-4.1-mini", "messages": [{"role": "user", "content": "Hello"}]}
    )
    assert result["estimate"] is True
    assert result["estimated_request_tokens"] > result["original_text_tokens"]

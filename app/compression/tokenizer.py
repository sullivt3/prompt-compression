import json
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

import tiktoken


class UnknownModelError(ValueError):
    pass


class TokenCounter(ABC):
    @abstractmethod
    def count_text(self, text: str, model: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def count_request(self, payload: dict[str, Any]) -> int:
        raise NotImplementedError


class TiktokenCounter(TokenCounter):
    @staticmethod
    @lru_cache(maxsize=128)
    def encoding(model: str) -> tiktoken.Encoding:
        try:
            name = tiktoken.encoding_name_for_model(model)
            if name not in {"o200k_base", "cl100k_base"}:
                raise KeyError(model)
            return tiktoken.get_encoding(name)
        except KeyError as exc:
            raise UnknownModelError(f"No tokenizer registered for model: {model}") from exc

    def count_text(self, text: str, model: str) -> int:
        return len(self.encoding(model).encode(text, disallowed_special=()))

    def count_request(self, payload: dict[str, Any]) -> int:
        # Conservative framing heuristic; actual provider usage is authoritative.
        model = str(payload["model"])
        total = 3
        for message in payload["messages"]:
            total += 3
            for key, value in message.items():
                serialized = (
                    value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
                )
                total += self.count_text(serialized, model)
                if key == "name":
                    total += 1
        return total

    def analyze(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = str(payload["model"])
        counts = [self.count_text(m["content"], model) for m in payload["messages"]]
        return {
            "model": model,
            "original_text_tokens": sum(counts),
            "estimated_request_tokens": self.count_request(payload),
            "tokens_per_message": counts,
            "tokenizer": self.encoding(model).name,
            "estimate": True,
        }

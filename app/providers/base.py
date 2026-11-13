from abc import ABC, abstractmethod
from typing import Any

import httpx


class Provider(ABC):
    @abstractmethod
    async def send(self, payload: dict[str, Any]) -> httpx.Response:
        """Open an upstream response; the caller must close it."""
        raise NotImplementedError

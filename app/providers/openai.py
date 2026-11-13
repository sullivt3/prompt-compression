from typing import Any

import httpx
from fastapi import HTTPException

from app.providers.base import Provider


class OpenAIProvider(Provider):
    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self.client = client
        self.api_key = api_key

    async def send(self, payload: dict[str, Any]) -> httpx.Response:
        if not self.api_key:
            raise HTTPException(503, "Provider is not configured")
        # Fixed destination: never accept an upstream URL or auth header from clients.
        request = self.client.build_request(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        return await self.client.send(request, stream=True, follow_redirects=False)

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.core.config import Settings
from app.core.security import generate_api_key, key_digest
from app.db.models import APIKey
from app.main import create_app
from tests.helpers import provision


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["valid", "revoked", "expired", "unknown"])
async def test_key_lifecycle(state: str) -> None:
    app = create_app(Settings(environment="test"))
    token = generate_api_key()
    await provision(app, token)
    async with app.state.sessions() as session:
        key = await session.get(APIKey, "key-test")
        assert key.digest == key_digest(token) and key.digest != token
        if state == "revoked":
            key.revoked = True
        if state == "expired":
            key.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        response = await client.post(
            "/v1/optimize",
            headers={"Authorization": f"Bearer {token if state != 'unknown' else 'unknown'}"},
            json={"model": "gpt-4.1-mini", "text": "Explain Docker."},
        )
        assert response.status_code == (200 if state == "valid" else 401)
    await app.state.database.dispose()

import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_playground_assets_and_api_authentication() -> None:
    app = create_app(Settings(environment="test"))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        assert (await client.get("/")).headers["location"] == "/playground"
        response = await client.get("/playground")
        assert response.status_code == 200
        assert "Same intent." in response.text
        assert 'id="compression-time"' in response.text
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        for asset, media_type in [
            ("style.css", "text/css"),
            ("playground.js", "application/javascript"),
        ]:
            response = await client.get(f"/playground/assets/{asset}")
            assert response.status_code == 200
            assert media_type in response.headers["content-type"]
        assert (await client.get("/playground/assets/../../core/config.py")).status_code == 404
        response = await client.post(
            "/v1/optimize",
            json={"model": "gpt-4.1-mini", "text": "Hey ChatGPT, please explain Kubernetes."},
        )
        assert response.status_code == 401

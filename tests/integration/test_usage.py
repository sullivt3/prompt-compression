import httpx
import pytest

from app.core.config import Settings
from app.core.security import key_digest
from app.db.models import APIKey, Tenant, TenantConfig
from app.main import create_app
from tests.helpers import provision


@pytest.mark.asyncio
async def test_usage_tenant_isolation_and_filters() -> None:
    app = create_app(Settings(environment="test"))
    await provision(app)
    async with app.state.sessions() as session:
        session.add(Tenant(id="other", name="Other"))
        await session.flush()
        session.add(TenantConfig(tenant_id="other"))
        session.add(APIKey(tenant_id="other", digest=key_digest("other-token")))
        await session.commit()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        client.headers["Authorization"] = "Bearer gateway-test"
        await client.post(
            "/v1/optimize",
            json={
                "model": "gpt-4.1-mini",
                "text": "Hey ChatGPT, can you please explain Kubernetes?",
            },
        )
        usage = (await client.get("/v1/usage")).json()
        assert usage["total_requests"] == 1
        assert usage["optimized_requests"] == 1
        assert usage["estimated_tokens_saved"] > 0
        assert usage["provider_reported_input_tokens"] is None
        assert usage["rule_effectiveness"]["greeting_removal"] == 1
        assert (await client.get("/v1/usage", params={"start": "2000-01-01"})).status_code == 422
        client.headers["Authorization"] = "Bearer other-token"
        assert (await client.get("/v1/usage")).json()["total_requests"] == 0
    await app.state.database.dispose()

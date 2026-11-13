"""Real PostgreSQL/Redis authenticated preview and analytics integration. No paid calls."""

import asyncio
from uuid import uuid4

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.requests import Request

from app.core.config import Settings
from app.core.rate_limit import acquire_concurrency, release_concurrency
from app.core.security import Principal, generate_api_key, key_digest
from app.db.models import APIKey, OptimizationResult, Tenant, TenantConfig, UsageRecord
from app.main import create_app


async def main() -> None:
    settings = Settings()
    tenant_id, key_id = str(uuid4()), str(uuid4())
    other_id, other_key_id = str(uuid4()), str(uuid4())
    token, other_token = generate_api_key(), generate_api_key()
    engine = create_async_engine(settings.database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            session.add_all(
                [Tenant(id=tenant_id, name="Integration"), Tenant(id=other_id, name="Isolation")]
            )
            await session.flush()
            session.add_all(
                [
                    TenantConfig(tenant_id=tenant_id, max_concurrency=1),
                    TenantConfig(tenant_id=other_id),
                    APIKey(id=key_id, tenant_id=tenant_id, digest=key_digest(token)),
                    APIKey(id=other_key_id, tenant_id=other_id, digest=key_digest(other_token)),
                ]
            )
            await session.commit()
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://gateway"
            ) as client:
                client.headers["Authorization"] = f"Bearer {token}"
                lease_request = Request(
                    {"type": "http", "app": app, "state": {"request_id": str(uuid4())}}
                )
                principal = Principal(tenant_id, key_id, max_concurrency=1)
                lease = await acquire_concurrency(lease_request, principal)
                try:
                    blocked = await client.post(
                        "/v1/optimize", json={"model": "gpt-4.1-mini", "text": "Explain Docker."}
                    )
                    assert blocked.status_code == 429
                finally:
                    await release_concurrency(lease_request, principal, lease)
                response = await client.post(
                    "/v1/optimize",
                    json={
                        "model": "gpt-4.1-mini",
                        "text": "Hey ChatGPT, can you please explain Kubernetes?",
                    },
                )
                assert response.status_code == 200, response.status_code
                assert response.json()["applied"]
                response = await client.get("/v1/usage")
                assert response.status_code == 200
                assert response.json()["total_requests"] == 1
                assert response.json()["estimated_tokens_saved"] > 0
                client.headers["Authorization"] = f"Bearer {other_token}"
                assert (await client.get("/v1/usage")).json()["total_requests"] == 0
                print("PostgreSQL/Redis preview concurrency, analytics and isolation checks passed")
    finally:
        async with sessions() as session:
            usage_ids = select(UsageRecord.id).where(
                UsageRecord.tenant_id.in_([tenant_id, other_id])
            )
            await session.execute(
                delete(OptimizationResult).where(OptimizationResult.usage_id.in_(usage_ids))
            )
            for model, column in [
                (UsageRecord, UsageRecord.tenant_id),
                (APIKey, APIKey.tenant_id),
                (TenantConfig, TenantConfig.tenant_id),
                (Tenant, Tenant.id),
            ]:
                await session.execute(delete(model).where(column.in_([tenant_id, other_id])))
            await session.commit()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

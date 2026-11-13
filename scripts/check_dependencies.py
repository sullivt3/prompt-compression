"""Integration assertions against configured PostgreSQL and Redis; no paid API calls."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from redis.asyncio import Redis
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.rate_limit import acquire_concurrency, enforce_limit, release_concurrency
from app.core.security import Principal


async def main() -> None:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        tables = await connection.run_sync(lambda conn: inspect(conn).get_table_names())
        assert {
            "tenants",
            "api_keys",
            "usage_records",
            "optimization_results",
            "tenant_config",
        } <= set(tables)
    redis = Redis.from_url(settings.redis_url)
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(redis=redis)),
        state=SimpleNamespace(request_id=str(uuid4())),
    )
    prefix = "integration:" + str(uuid4())
    principal = Principal(prefix, prefix, max_concurrency=1)
    try:
        await enforce_limit(request, prefix, 1)
        try:
            await enforce_limit(request, prefix, 1)
        except Exception as exc:
            assert exc.status_code == 429
        else:
            raise AssertionError("Redis rate limit did not enforce")
        lease = await acquire_concurrency(request, principal)
        try:
            await acquire_concurrency(request, principal)
        except Exception as exc:
            assert exc.status_code == 429
        else:
            raise AssertionError("Redis concurrency did not enforce")
        await release_concurrency(request, principal, lease)
        await acquire_concurrency(request, principal)
        print("PostgreSQL migration and Redis rate/concurrency integration checks passed")
    finally:
        await redis.delete(prefix, f"concurrency:{prefix}")
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

from unittest.mock import AsyncMock

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import key_digest
from app.db.models import APIKey, Base, Tenant, TenantConfig


async def provision(app: FastAPI, token: str = "gateway-test") -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    app.state.database = engine
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    app.state.redis = AsyncMock()
    app.state.redis.eval.return_value = 1
    async with app.state.sessions() as session:
        session.add(Tenant(id="tenant-test", name="Test"))
        await session.flush()
        session.add(TenantConfig(tenant_id="tenant-test"))
        session.add(APIKey(id="key-test", tenant_id="tenant-test", digest=key_digest(token)))
        await session.commit()

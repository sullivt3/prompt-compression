import asyncio
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    async def database() -> bool:
        async with request.app.state.database.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True

    async def redis() -> bool:
        return bool(await request.app.state.redis.ping())

    async def check(operation: Any) -> bool:
        try:
            return bool(
                await asyncio.wait_for(
                    operation(), timeout=request.app.state.settings.dependency_timeout_seconds
                )
            )
        except Exception:
            return False

    db_ok, redis_ok = await asyncio.gather(check(database), check(redis))
    healthy = db_ok and redis_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ready" if healthy else "unavailable",
            "dependencies": {"database": db_ok, "redis": redis_ok},
        },
    )

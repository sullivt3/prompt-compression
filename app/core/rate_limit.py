import time

from fastapi import HTTPException, Request
from redis.exceptions import RedisError

from app.core.security import Principal

WINDOW_LIMIT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return count <= tonumber(ARGV[1]) and 1 or 0
"""


async def enforce_limit(request: Request, key: str, limit: int) -> None:
    try:
        allowed = await request.app.state.redis.eval(WINDOW_LIMIT, 1, key, limit, 60)
    except (RedisError, OSError) as exc:
        raise HTTPException(503, "Rate limiter unavailable") from exc
    if not allowed:
        raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": "60"})


async def limit_principal(request: Request, principal: "Principal", preview: bool = False) -> None:
    await enforce_limit(request, f"rate:key:{principal.key_id}", principal.key_requests_per_minute)
    await enforce_limit(
        request, f"rate:tenant:{principal.tenant_id}", principal.requests_per_minute
    )
    if preview:
        await enforce_limit(
            request, f"rate:preview:{principal.key_id}", principal.preview_per_minute
        )


ACQUIRE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[4]) then return 0 end
redis.call('ZADD', KEYS[1], ARGV[2], ARGV[3])
redis.call('EXPIRE', KEYS[1], ARGV[5])
return 1
"""


async def acquire_concurrency(request: Request, principal: "Principal") -> str:
    lease = str(request.state.request_id)
    now = time.time()
    try:
        acquired = await request.app.state.redis.eval(
            ACQUIRE,
            1,
            f"concurrency:{principal.tenant_id}",
            now,
            now + 130,
            lease,
            principal.max_concurrency,
            131,
        )
    except (RedisError, OSError) as exc:
        raise HTTPException(503, "Concurrency limiter unavailable") from exc
    if not acquired:
        raise HTTPException(429, "Concurrency limit exceeded")
    return lease


async def release_concurrency(request: Request, principal: "Principal", lease: str) -> None:
    try:
        await request.app.state.redis.zrem(f"concurrency:{principal.tenant_id}", lease)
    except (RedisError, OSError):
        # Lease expires; new acquisitions still fail closed while Redis is unavailable.
        pass

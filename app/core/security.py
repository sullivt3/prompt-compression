import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.models import APIKey, TenantConfig


def generate_api_key() -> str:
    return "pgw_" + secrets.token_urlsafe(32)


def key_digest(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    key_id: str
    compression_mode: str = "off"
    requests_per_minute: int = 60
    preview_per_minute: int = 30
    key_requests_per_minute: int = 60
    max_concurrency: int = 4
    min_saved_tokens: int = 2
    min_saved_percent: float = 1.0


async def authenticate(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> Principal:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 256:
        raise HTTPException(401, "Invalid API key", headers={"WWW-Authenticate": "Bearer"})
    try:
        async with request.app.state.sessions() as session:
            key = await session.scalar(select(APIKey).where(APIKey.digest == key_digest(token)))
            if (
                key is None
                or key.revoked
                or (
                    key.expires_at is not None
                    and key.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
                )
            ):
                raise HTTPException(401, "Invalid API key")
            config = await session.get(TenantConfig, key.tenant_id)
            if config is None:
                raise HTTPException(503, "Tenant configuration unavailable")
            return Principal(
                key.tenant_id,
                key.id,
                config.compression_mode,
                config.requests_per_minute,
                config.preview_per_minute,
                config.key_requests_per_minute,
                config.max_concurrency,
                config.min_saved_tokens,
                config.min_saved_percent,
            )
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Authentication unavailable") from exc

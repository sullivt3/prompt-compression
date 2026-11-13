"""Host-admin CLI; requires direct database credentials. No HTTP key-creation endpoint."""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.security import generate_api_key, key_digest
from app.db.models import APIKey, Tenant, TenantConfig


async def run(args: argparse.Namespace) -> None:
    engine = create_async_engine(Settings().database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            if args.revoke:
                key = await session.get(APIKey, args.revoke)
                if key is None:
                    raise SystemExit("Unknown key ID")
                key.revoked = True
                await session.commit()
                print("Key revoked")
                return
            if args.days < 1:
                raise SystemExit("--days must be positive")
            tenant = await session.get(Tenant, args.tenant) if args.tenant else None
            if args.tenant and tenant is None:
                raise SystemExit("Unknown tenant ID")
            if tenant is None:
                tenant = Tenant(name=args.name)
                session.add(tenant)
                await session.flush()
                session.add(TenantConfig(tenant_id=tenant.id, compression_mode=args.mode))
            elif args.configure:
                config = await session.get(TenantConfig, tenant.id)
                if config is None:
                    raise SystemExit("Tenant configuration missing")
                config.compression_mode = args.mode
                config.requests_per_minute = args.rpm
                config.key_requests_per_minute = args.rpm
                config.preview_per_minute = args.preview_rpm
                config.max_concurrency = args.concurrency
                await session.commit()
                print("Tenant configuration updated")
                return
            token = generate_api_key()
            key = APIKey(
                tenant_id=tenant.id,
                digest=key_digest(token),
                label=args.name,
                expires_at=datetime.now(UTC) + timedelta(days=args.days),
            )
            session.add(key)
            await session.commit()
            print(f"Tenant ID: {tenant.id}\nKey ID: {key.id}\nAPI key (shown once): {token}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant")
    parser.add_argument("--name", default="Developer")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--revoke", metavar="KEY_ID")
    parser.add_argument("--configure", action="store_true", help="Update existing --tenant policy")
    parser.add_argument("--mode", choices=["off", "algorithmic"], default="off")
    parser.add_argument("--rpm", type=int, default=60)
    parser.add_argument("--preview-rpm", type=int, default=30)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    if args.configure and not args.tenant:
        parser.error("--configure requires --tenant")
    if min(args.rpm, args.preview_rpm, args.concurrency) < 1:
        parser.error("Rate and concurrency limits must be positive")
    asyncio.run(run(args))

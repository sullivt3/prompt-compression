from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def identifier() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    digest: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(200), default="default")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TenantConfig(Base):
    __tablename__ = "tenant_config"
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), primary_key=True)
    compression_mode: Mapped[str] = mapped_column(String(20), default="off")
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    preview_per_minute: Mapped[int] = mapped_column(Integer, default=30)
    key_requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=4)
    min_saved_tokens: Mapped[int] = mapped_column(Integer, default=2)
    min_saved_percent: Mapped[float] = mapped_column(Float, default=1.0)


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_tenant_created", "tenant_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"))
    api_key_id: Mapped[str] = mapped_column(ForeignKey("api_keys.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    request_id: Mapped[str] = mapped_column(String(36))
    endpoint: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(200))
    status_code: Mapped[int] = mapped_column(Integer)
    original_tokens: Mapped[int] = mapped_column(Integer, default=0)
    forwarded_tokens: Mapped[int] = mapped_column(Integer, default=0)
    provider_input_tokens: Mapped[int | None] = mapped_column(Integer)
    provider_output_tokens: Mapped[int | None] = mapped_column(Integer)
    optimized: Mapped[bool] = mapped_column(Boolean, default=False)
    attempted: Mapped[bool] = mapped_column(Boolean, default=False)
    compression_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    optimization_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    gateway_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    provider_latency_ms: Mapped[float] = mapped_column(Float, default=0)


class OptimizationResult(Base):
    __tablename__ = "optimization_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    usage_id: Mapped[str] = mapped_column(ForeignKey("usage_records.id"), unique=True)
    skip_reason: Mapped[str | None] = mapped_column(String(100))
    rules: Mapped[list[str]] = mapped_column(JSON, default=list)
    estimated_net_savings: Mapped[float | None] = mapped_column(Float)

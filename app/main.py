from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.optimize import router as optimize_router
from app.api.playground import router as playground_router
from app.api.usage import router as usage_router
from app.core.config import Settings
from app.core.middleware import PayloadLimitMiddleware
from app.providers.openai import OpenAIProvider
from app.providers.registry import ProviderRegistry
from app.telemetry.logging import configure_logging
from app.telemetry.tracing import create_tracer


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    trace_provider, tracer = create_tracer(settings.trace_console_export)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.database = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_timeout=5,
            connect_args={"timeout": 5, "command_timeout": 5},
        )
        app.state.sessions = async_sessionmaker(app.state.database, expire_on_commit=False)
        app.state.redis = Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
        app.state.http = httpx.AsyncClient(
            timeout=httpx.Timeout(60, connect=5),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            trust_env=False,
        )
        app.state.providers = ProviderRegistry(
            OpenAIProvider(app.state.http, settings.openai_api_key.get_secret_value())
        )
        try:
            yield
        finally:
            await app.state.http.aclose()
            await app.state.redis.aclose()
            await app.state.database.dispose()
            trace_provider.shutdown()

    app = FastAPI(
        title="Prompt Gateway",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.environment == "development" else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(PayloadLimitMiddleware, max_bytes=settings.max_payload_bytes)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={"error": {"message": str(exc.detail), "type": "gateway_error"}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "Unsupported or invalid request structure",
                    "type": "invalid_request_error",
                    "fields": [
                        {"location": list(error["loc"]), "type": error["type"]}
                        for error in exc.errors()
                    ],
                }
            },
        )

    @app.middleware("http")
    async def correlation_id(request: Request, call_next: object) -> Response:
        request.state.request_id = str(uuid4())
        with tracer.start_as_current_span(
            "gateway.request", record_exception=False, set_status_on_exception=False
        ) as span:
            span.set_attribute("request.id", request.state.request_id)
            span.set_attribute("http.request.method", request.method)
            response = await call_next(request)  # type: ignore[operator]
            span.set_attribute("http.response.status_code", response.status_code)
        response.headers["X-Request-ID"] = request.state.request_id
        return response  # type: ignore[no-any-return]

    app.include_router(playground_router)
    app.include_router(usage_router, prefix="/v1")
    app.include_router(optimize_router, prefix="/v1")
    app.include_router(chat_router, prefix="/v1")
    app.include_router(health_router, prefix="/v1")
    return app


app = create_app()

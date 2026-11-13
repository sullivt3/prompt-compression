# Development and controlled deployment

Use Python 3.12+ and uv. `uv sync --frozen --python 3.12` installs pinned development
dependencies. `cp .env.example .env` then configure provider credentials for live
chat only. Preview and tests need no paid provider credential. Tokenizer assets are
public downloads, not inference. Docker preloads o200k_base and cl100k_base during
build so the read-only runtime does not download them. Direct local setup can use
`python -m scripts.bootstrap` to preload supported assets and run migrations.

```sh
docker compose up --build -d
docker compose exec gateway python scripts/create_api_key.py --name Developer
curl http://localhost:8000/v1/ready
```

Copy the displayed gateway key privately to your client. Use the displayed tenant
ID to configure optimization:
`docker compose exec gateway python scripts/create_api_key.py --tenant TENANT_ID --configure --mode algorithmic`.
Off is the default.
Revoke with `--revoke KEY_ID`. Production administration requires trusted access to
the container/database, not public HTTP. Each tenant should have separate keys.

To run the host application, point DATABASE_URL/REDIS_URL at reachable services,
run `alembic upgrade head`, then `uvicorn app.main:app --reload`. Compose intentionally
does not publish database or Redis ports. Its database volume persists across restarts.
Stop containers with `docker compose stop`; do not delete volumes to reset errors.

Production needs a TLS reverse proxy, unique database credentials, secret injection,
private service networks, backup/restore, resource limits, retention policy and
operational monitoring. Set `GATEWAY_ENVIRONMENT=production` to disable docs/schema.
Run migrations once as a release job before replicas start; Compose's startup
migration is intended for the single local instance. The image runs as UID 10001,
with a read-only filesystem, writable tmpfs and no-new-privileges in Compose.
Do not auto-deploy this repository. CI only validates and builds.

Pricing configuration is a JSON object via `GATEWAY_PRICING`, keyed by exact model
ID, with input_per_million, output_per_million, optional cached_input_per_million,
currency and effective_date. Supply verified current data; none is bundled.
GATEWAY_LOCAL_COMPUTE_COST_PER_SECOND optionally models local processing cost.
GATEWAY_TRACE_CONSOLE_EXPORT enables content-free console traces for diagnostics.
GATEWAY_MAX_PAYLOAD_BYTES defaults to 1MiB. Consult Settings for all bounds/defaults.

Checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`,
`uv run pytest --cov=app`. Integration checks against real local services:
`docker compose exec -T gateway python < scripts/check_dependencies.py`.

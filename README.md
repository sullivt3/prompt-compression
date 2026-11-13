# Prompt Gateway

A Python API gateway for conservative, local prompt compression and measurable
input-token estimates. It proxies a documented text-chat subset of OpenAI Chat
Completions, supports SSE, authenticates tenant API keys, limits requests with Redis,
and stores metadata in PostgreSQL. Semantic compression is unavailable and disabled.

The rules prioritize preservation over savings: protected or ambiguous messages
pass through unchanged. No raw prompts or responses are stored. Compression defaults
to off and can be enabled per tenant. See [limitations](docs/security.md).

## Run locally

Requires Docker Desktop/Compose. For host development, Python 3.12+ and uv.

```sh
cp .env.example .env
# Set GATEWAY_OPENAI_API_KEY in .env only for live chat.
docker compose up --build -d
docker compose exec gateway python scripts/create_api_key.py --name Developer
curl http://localhost:8000/v1/ready
```

Keep the generated gateway key private. Development API docs: http://localhost:8000/docs.
Preview uses no LLM:

```sh
curl http://localhost:8000/v1/optimize \
  -H "Authorization: Bearer $GATEWAY_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4.1-mini","text":"Hey ChatGPT, please explain Kubernetes."}'
```

Point the OpenAI SDK at `http://localhost:8000/v1` and supply your gateway key.
See [API examples and supported fields](docs/api.md). Tool calls and multimodal
messages are rejected. A provider credential is needed only for live chat calls.

## Develop and verify

```sh
uv sync --frozen --python 3.12
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest --cov=app
uv run python -m scripts.benchmark
```

See [deployment](docs/deployment.md), [architecture](docs/architecture.md),
[compression](docs/compression.md), [security](docs/security.md),
[benchmarks](docs/benchmarks.md), [roadmap](docs/roadmap.md), and the
[implementation status](docs/implementation-status.md) for measured validation and
remaining limits. The initial 120-prompt synthetic benchmark reduced total estimated
tokens by 0.89%; no response-quality equivalence claim is made.

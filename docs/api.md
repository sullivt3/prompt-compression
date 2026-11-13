# API contract

Development-only `/docs` and `/openapi.json` contain the generated schemas.
All product endpoints require `Authorization: Bearer <gateway-key>`. Public health:
`GET /v1/health`; dependency readiness: `GET /v1/ready` (200 or 503).

`POST /v1/chat/completions` supports string-content messages with roles system,
developer, user and assistant; optional names; model; stream; stream_options with
include_usage; temperature; top_p; max_tokens; max_completion_tokens; stop; seed;
presence_penalty; frequency_penalty; n. Unknown fields and multimodal/tool/function
messages are rejected with 422, never silently discarded. Supported explicitly
provided fields are forwarded as supplied; the provider may further reject a
parameter/model combination. Null content is unsupported. Responses are relayed
without rewriting usage or content. Streaming preserves upstream bytes/chunk order;
HTTP transport chunk boundaries are not an API guarantee. No automatic retries.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="YOUR_GATEWAY_KEY")
result = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Explain Kubernetes pods."}],
)
print(result.choices[0].message.content)
```

Model selection and provider availability are the caller's responsibility. The model
above follows the requested example and is not a recommendation of current availability.
SDK compatibility is tested with mocked OpenAI responses, including SSE streams.
Reference: [official Chat Completions contract](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

`POST /v1/optimize` takes model, text and strategy (default algorithmic). It returns
original/optimized text, actual tokenizer counts, token savings, applied rules,
transformation metadata, validation checks, size class, latency and skip reason.
It never calls an LLM. Example body:

```json
{"model":"gpt-4.1-mini","text":"Hey ChatGPT, please explain Kubernetes.","strategy":"algorithmic"}
```

`GET /v1/usage?start=2026-11-01T00:00:00Z&end=2026-11-12T00:00:00Z`
returns tenant aggregates for chat and previews together. Dates must be timezone
aware; end is exclusive. Default last 30 days; maximum 366 days. Counts cover stored
product operations, not public health or auth/rate-limit rejections. Provider token
sums are null if unreported. Rule effectiveness counts requests applying each rule.
Latencies are averages; streaming gateway/provider latency includes stream lifetime.
Estimated preview tokens are text-only; chat estimates include message framing.

Errors use an error object and meaningful HTTP status (401 auth, 413 size, 422
validation/unsupported mode/tokenizer in preview, 429 limits, 502/504 upstream,
503 unavailable dependencies/configuration). Upstream diagnostics are sanitized.
Streaming interruptions after headers use an SSE error object without retrying.
Every application response has a server-generated X-Request-ID.

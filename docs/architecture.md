# Architecture

The repository root is the `prompt-gateway` project described in the assignment.
The modular monolith owns async HTTP, database and Redis pools in FastAPI lifespan.
The HTTP-independent compression package can run in scripts or other applications.

Chat processing: authenticate a hashed tenant key → enforce Redis key/tenant limits
and tenant concurrency → validate the documented text-chat subset → count estimated
request tokens → optimize eligible user messages → replay transformations and verify
whole-request structure → evaluate configured costs → call the fixed OpenAI endpoint
once → relay response → persist metadata. Compression defaults to off per tenant.
CPU tokenization and rules execute in a worker thread. Streaming uses an async
iterator with bounded usage-frame inspection, cancellation cleanup, and a deadline.
The response owns streaming cleanup, including disconnects before the first chunk;
upstream closure, metadata recording and lease release run on that path once.
Chat and preview share the same tenant concurrency pool.
Provider HTTP status errors are sanitized. Once streaming starts, upstream failure
is signaled by an SSE error frame; the already-sent HTTP status remains 200.

SQLAlchemy stores tenants, hashed keys, tenant policies, usage and optimization
metadata. PostgreSQL is the deployment database. SQLite supports isolated test
fixtures, not deployment. Redis Lua scripts enforce fixed-window rate limits and
expiring concurrency leases. Infrastructure failure does not disable authentication
or rate limiting. Usage write failures log a static event and preserve the provider
response; delivery is best-effort, without a durable telemetry queue.

Health checks only the process. Readiness checks PostgreSQL connectivity and Redis;
it does not establish provider credentials, migration state, or quota availability.
Alembic migrations are a separate deployment responsibility. Compose runs them
before the single local gateway instance starts.

OpenAI behavior reference: [Chat Completions API](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
The supported subset is intentionally narrower than the provider API.

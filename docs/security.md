# Security and operational limits

Gateway keys contain 256 bits of random material and are stored as SHA-256 digests.
The admin CLI requires direct database access; there is no key-minting HTTP route.
Keys expire and can be revoked. Tenants are resolved from the key, never from a
client-provided tenant ID. SQL analytics predicates include the authenticated tenant.
Restrict database credentials and CLI/container access to trusted administrators.
Gateway keys and provider credentials serve different purposes and must differ.

The upstream is fixed to `https://api.openai.com/v1/chat/completions`. Client URLs,
custom auth forwarding, redirects and environment HTTP proxies are not supported.
Connections use TLS certificate verification. Payloads are bounded before parsing,
including chunked bodies, with a ten-second body deadline. Upstream work has a
120-second deadline and pooled connections. Requests are not retried, avoiding
accidental duplicate inference charges. Reverse proxies should also enforce body,
header, idle connection and TLS policies.

Redis is mandatory for product requests, with per-key and tenant fixed windows,
a preview-specific limit, and concurrency leases shared by chat and preview. The window begins at the
first request and expires after 60 seconds. Redis failure returns 503. Leases expire
after 130 seconds if cleanup fails. The Redis deployment is standalone; Lua is not
currently compatible with Redis Cluster multi-key policies. Network isolation is
required: Compose only publishes the gateway on localhost.

Prompts and responses are not persisted. Logs/traces omit bodies, headers, URLs,
provider diagnostics and secrets. HTTP access logs and httpx info logs are disabled.
Preview necessarily echoes prompt content to its authenticated caller. Configure
TLS and response handling accordingly. OpenTelemetry emits content-free metadata;
console export is optional and disabled by default. There is no external collector
export configured by default. Disable verbose third-party logging in deployments.

Remaining limits: conservative heuristic compression is not a semantic guarantee;
stream usage inspection supports fragmented LF, CRLF and CR event frames,
but is best-effort and bounded to 64KiB frames; usage persistence is
best-effort with no durable queue; authentication/limit rejections are not currently
included in tenant usage; no live-provider or distributed failover/load validation;
no automatic data retention job; no zero-downtime migration orchestration; no
centralized key-management integration. The admin key CLI prints a new secret once;
run it in a private terminal and never paste output into logs. Secrets are configured
through the environment; use your deployment's secret manager. Local Compose's
password default is only for development.

Dependency scanning runs in CI. A clean scan is a point-in-time result, not a
security certification. Do not expose the local development setup publicly.

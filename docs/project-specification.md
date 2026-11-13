# CODEX MASTER PROMPT — PROMPT GATEWAY

## PROJECT: Hybrid Prompt Compression & Token Optimization API Gateway

### YOUR ROLE

Act as a principal software architect, senior Python engineer, AI infrastructure engineer, security engineer, and DevOps engineer.

You are responsible for building a complete, production-oriented LLM Prompt Optimization Gateway.

This is an implementation assignment, not a request for architectural documentation alone.

Create actual source code, project files, tests, database schemas, Docker configurations, API endpoints, and technical documentation.

Implement the project incrementally in the phases specified below.

Do not stop after creating scaffolding.

Do not implement advanced features before the foundational components are working and tested.

---

# 1. PROJECT OBJECTIVE

Build a developer-focused API gateway that reduces the number of input tokens sent to large language models while preserving the original prompt's intent, requirements, and constraints.

Developers should be able to integrate the gateway into their existing applications by changing their API base URL and authentication key.

The gateway must:

1. Accept LLM API requests.
2. Authenticate incoming requests.
3. Identify the target model.
4. Calculate estimated input token usage.
5. Analyze the prompt for compression opportunities.
6. Determine whether compression is safe.
7. Apply algorithmic compression when beneficial.
8. Optionally use AI-powered semantic compression in a future phase.
9. Validate the compressed candidate.
10. Compare original and compressed token counts.
11. Evaluate expected economic savings.
12. Forward the best eligible candidate or the original request.
13. Return the provider's response.
14. Record token usage, compression results, and latency.
15. Provide analytics through API endpoints.

The primary product goal is:

**Reduce the cost of LLM input tokens without materially degrading response quality or breaking existing API integrations.**

The system must never prioritize compression ratio over correctness.

---

# 2. ARCHITECTURAL STRATEGY

Use a hybrid compression architecture with three main components.

## A. RuleCompressor

A deterministic Python compression engine.

It must not require an AI model, network request, or external inference service.

Responsibilities:

- Identify narrowly defined redundant phrases.
- Remove eligible conversational filler.
- Detect exact repeated text where removal is provably safe.
- Normalize insignificant whitespace in approved contexts.
- Preserve structured data.
- Protect exact-match content.
- Return transformation metadata.
- Calculate token savings.

The RuleCompressor is the primary compression implementation for the MVP.

## B. SemanticCompressor

An optional future component that uses a language model to rewrite longer prompts more efficiently.

Design the interface now, but do not require semantic compression for the MVP.

Future implementations may support:

- Ollama
- Locally hosted language models
- OpenAI API
- Anthropic API
- Other compatible inference services

Semantic compression must be explicitly enabled.

Never silently invoke a paid model.

## C. CompressionRouter

A Python component that decides which compression strategy to use.

Responsibilities:

- Inspect prompt characteristics.
- Evaluate compression eligibility.
- Detect protected content.
- Evaluate prompt size.
- Evaluate estimated token savings.
- Evaluate compression cost.
- Apply configured optimization policies.
- Select the best validated candidate.
- Fall back to the original prompt when necessary.

The router must support these modes:

- `off`
- `algorithmic`
- `semantic`
- `hybrid`

Initially, only `off` and `algorithmic` must be operational.

Unsupported modes must produce explicit, documented behavior.

---

# 3. TECHNOLOGY STACK

Use:

### Backend
- Python 3.12+
- FastAPI
- Uvicorn
- Pydantic v2
- httpx
- asyncio

### Tokenization
- tiktoken
- Model-aware tokenizer registry

### Compression
- Python standard library
- Regular expressions
- Syntax-aware parsing where necessary
- Custom deterministic rule engine
- Protected-span detection
- Configurable policy engine

### Database
- PostgreSQL
- SQLAlchemy 2.x
- Alembic

### Infrastructure
- Docker
- Docker Compose
- Redis
- GitHub Actions

### Testing
- pytest
- pytest-asyncio
- pytest-cov
- Hypothesis
- respx
- Ruff
- mypy

### Observability
- Structured logging
- OpenTelemetry
- Request correlation IDs

Do not introduce microservices or unnecessary infrastructure.

---

# 4. REPOSITORY STRUCTURE

Create:

```text
prompt-gateway/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── chat.py
│   │   ├── optimize.py
│   │   ├── usage.py
│   │   └── health.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── rate_limit.py
│   │   └── exceptions.py
│   │
│   ├── compression/
│   │   ├── base.py
│   │   ├── rules.py
│   │   ├── semantic.py
│   │   ├── router.py
│   │   ├── tokenizer.py
│   │   ├── eligibility.py
│   │   ├── protected_spans.py
│   │   ├── validator.py
│   │   ├── economics.py
│   │   └── engine.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── openai.py
│   │   └── registry.py
│   │
│   ├── schemas/
│   ├── services/
│   ├── telemetry/
│   └── db/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── compatibility/
│   ├── security/
│   └── benchmarks/
│
├── scripts/
│   ├── bootstrap.py
│   ├── create_api_key.py
│   └── benchmark.py
│
├── migrations/
│
├── docs/
│   ├── architecture.md
│   ├── compression.md
│   ├── api.md
│   ├── security.md
│   ├── benchmarks.md
│   ├── roadmap.md
│   └── implementation-status.md
│
└── .github/
    └── workflows/
        └── ci.yml
```

Use modular, testable Python classes.

---

# PHASE 1 — PROJECT FOUNDATION

## Objective

Create a functional Python application with a stable development environment.

## Tasks

1. Initialize the Python project.
2. Create the repository structure.
3. Configure FastAPI.
4. Configure Pydantic Settings.
5. Create environment configuration.
6. Configure structured logging.
7. Configure Ruff and mypy.
8. Configure pytest.
9. Create a Dockerfile.
10. Create Docker Compose.
11. Add PostgreSQL.
12. Add Redis.
13. Create health endpoints.
14. Create the initial README.
15. Create AGENTS.md containing persistent development rules.

## API endpoints

Implement:

`GET /v1/health`

`GET /v1/ready`

Health should verify that the application process is functioning.

Readiness should check required dependencies.

## Acceptance criteria

- Application starts locally.
- FastAPI documentation is available in development.
- Docker Compose starts the services.
- Health endpoint responds successfully.
- Basic automated tests pass.

Do not proceed until the foundation is functional.

---

# PHASE 2 — OPENAI-COMPATIBLE API GATEWAY

## Objective

Build a transparent proxy before introducing compression.

## Primary endpoint

`POST /v1/chat/completions`

Support a documented subset of OpenAI Chat Completions.

The gateway must:

1. Receive requests.
2. Validate supported request structures.
3. Authenticate callers.
4. Forward requests to OpenAI.
5. Return compatible responses.
6. Support streaming.
7. Handle provider errors.
8. Preserve supported generation parameters.

## Provider abstraction

Implement a base provider interface.

The initial implementation must support OpenAI.

Design the interface for future providers without implementing them yet.

## Streaming requirements

Support Server-Sent Events.

Preserve chunk ordering and provider response structure.

Handle client disconnects, cancellation, and upstream failures.

Do not buffer entire streaming responses.

Do not retry requests after response bytes have been delivered.

## Compatibility

Test the gateway with the official OpenAI Python SDK.

Example:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="GATEWAY_API_KEY"
)

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {
            "role": "user",
            "content": "Explain Kubernetes pods."
        }
    ]
)

print(response.choices[0].message.content)
```

The gateway must support this integration when properly configured.

## Important constraints

Do not claim complete OpenAI compatibility.

Do not silently discard unsupported fields.

Use a fixed, trusted upstream provider configuration.

Do not allow arbitrary client-controlled upstream URLs.

## Acceptance criteria

- Non-streaming requests work.
- Streaming requests work.
- SDK compatibility tests pass.
- Provider errors are handled.
- Unsupported request shapes are rejected appropriately.
- Compression remains disabled.

---

# PHASE 3 — TOKENIZATION ENGINE

## Objective

Build a reusable Python token-counting engine.

## Requirements

Implement a `TokenCounter` abstraction.

Support:

- Model-specific tokenizers
- Text token counting
- Estimated complete request token counts
- Unicode text
- Technical terminology
- Code snippets
- Long prompts
- Unknown-model handling

Use tiktoken for supported OpenAI models.

Do not calculate tokens by simply dividing character count by four.

## Token analysis

Calculate:

- Original text tokens
- Estimated complete request tokens
- Tokens per eligible message
- Model identifier
- Tokenizer identifier

Distinguish between estimated token usage and actual provider-reported usage.

## Example internal result

```json
{
  "model": "gpt-4.1-mini",
  "original_text_tokens": 1200,
  "estimated_request_tokens": 1212,
  "tokenizer": "model_specific",
  "estimate": true
}
```

Values are illustrative.

## Acceptance criteria

- Token counts match supported tokenizer behavior.
- Unknown models are handled explicitly.
- Unit tests cover Unicode, code, punctuation, and long inputs.
- Tokenization does not require paid API calls.

---

# PHASE 4 — ALGORITHMIC COMPRESSION ENGINE

## Objective

Build the first functional prompt compression algorithm entirely in Python.

This is the most important MVP phase.

## 4.1 Compression interface

Implement a reusable interface resembling:

```python
class Compressor:
    def compress(self, text, context):
        raise NotImplementedError
```

Use strongly typed request and result models in the actual implementation.

## 4.2 Rule engine

Create independent compression rules.

Each rule must have:

- Unique identifier
- Description
- Eligibility criteria
- Transformation function
- Risk classification
- Unit tests
- Ability to be enabled or disabled

Initial rule categories:

### Rule A — Greeting removal

Example:

Original:

"Hey ChatGPT, please explain Kubernetes."

Candidate:

"Please explain Kubernetes."

Only apply when the greeting is clearly outside quoted or task content.

### Rule B — Conversational filler

Example:

Original:

"Can you please help me write a Python function?"

Candidate:

"Write a Python function."

Only use narrowly approved patterns.

### Rule C — Redundant introductions

Example:

Original:

"I would like you to explain what Docker containers are."

Candidate:

"Explain what Docker containers are."

### Rule D — Safe whitespace normalization

Normalize whitespace only in contexts where whitespace has no syntactic or semantic significance.

Do not modify whitespace in code, Markdown tables, structured data, or exact-match text.

### Rule E — Exact repetition detection

Detect exact repeated segments.

Do not automatically delete repeated instructions merely because they appear more than once.

Only remove repetition when the rule can establish that the duplicate is redundant and removal is permitted by policy.

## 4.3 Transformation metadata

Each rule must return metadata identifying:

- Rule applied
- Original span
- Replacement span
- Reason
- Estimated risk
- Whether validation succeeded

## 4.4 Important restrictions

Do not use unrestricted global regex replacements.

Do not remove negations.

Do not change numeric values.

Do not modify code or commands.

Do not change quoted strings.

Do not modify system or developer messages.

Do not alter API request parameters.

Do not compress prompts containing ambiguous protected content.

## 4.5 Idempotency

Applying deterministic compression twice should produce the same result as applying it once.

Add automated tests for this property.

## Acceptance criteria

- Rule-based compression works without AI.
- All rules are independently tested.
- Protected content is preserved in tests.
- Rules are deterministic.
- Compression can be disabled.
- Invalid transformations are rejected.

---

# PHASE 5 — PROTECTED CONTENT AND VALIDATION

## Objective

Prevent unsafe compression.

Implement a protected-content detector.

## Protected content

Protect:

- Code blocks
- Inline code
- JSON
- YAML
- XML
- Shell commands
- File paths
- URLs
- API definitions
- Function schemas
- Tool calls
- Quoted strings
- Numeric values
- Dates and times
- Units
- Negation
- Explicit constraints
- Security requirements
- Output formatting instructions
- User-supplied material intended for transformation

For the MVP, use conservative whole-message bypass when content cannot be safely classified.

## Validation engine

Create a `CompressionValidator`.

It must verify:

1. Message roles remain unchanged.
2. Message ordering remains unchanged.
3. Protected content remains unchanged.
4. Non-targeted fields remain unchanged.
5. Only approved rules were applied.
6. The candidate is shorter under the target tokenizer.
7. Configured minimum savings are achieved.

The validator must return structured results.

Example:

```json
{
  "valid": true,
  "checks": {
    "protected_content": true,
    "message_structure": true,
    "approved_rules": true,
    "token_reduction": true
  },
  "reason": "validated"
}
```

Do not treat these checks as proof of semantic equivalence.

## Fail-safe behavior

When validation fails:

- Discard the candidate.
- Preserve the original prompt.
- Record the skip reason.
- Continue forwarding if the request is otherwise valid.

## Acceptance criteria

- Protected spans are unchanged.
- Validation failures trigger pass-through.
- The engine does not silently modify unsupported content.
- Regression tests cover dangerous transformations.

---

# PHASE 6 — COMPRESSION ROUTER

## Objective

Build the decision-making engine that determines when and how to compress.

Implement `CompressionRouter`.

## Routing inputs

The router must consider:

- Model
- Original token count
- Content type
- Protected-content classification
- Selected compression strategy
- Minimum token savings
- Minimum percentage savings
- Estimated compression cost
- Expected net savings
- Validation result

## Initial routing policies

Use configurable starting policies:

### Small prompts

Under 500 tokens:

- Algorithmic compression only.
- Skip if estimated savings are insignificant.

### Medium prompts

500–2,000 tokens:

- Attempt algorithmic compression.
- Record whether semantic compression might be useful in the future.
- Do not invoke an AI model.

### Large prompts

Over 2,000 tokens:

- Attempt eligible algorithmic transformations.
- Preserve protected regions.
- Mark semantic compression eligibility for future evaluation.
- Do not invoke an AI model in the MVP.

These thresholds are configurable hypotheses, not fixed optimal values.

## Candidate selection

The router must:

1. Generate eligible candidates.
2. Validate each candidate.
3. Calculate token savings.
4. Reject unsafe candidates.
5. Reject candidates that do not meet savings thresholds.
6. Select the best eligible candidate.
7. Otherwise return the original prompt.

## Compression modes

Implement:

`off`

`algorithmic`

Reserve:

`semantic`

`hybrid`

Future modes must not be represented as functional until implemented.

## Acceptance criteria

- Routing decisions are deterministic.
- Policies are configurable.
- Unsafe candidates are rejected.
- Unsupported modes are handled explicitly.
- Original prompt fallback works.

---

# PHASE 7 — COMPRESSION PREVIEW API

## Objective

Allow developers to inspect compression results without sending requests to an LLM.

Implement:

`POST /v1/optimize`

## Example request

```json
{
  "model": "gpt-4.1-mini",
  "text": "Hey ChatGPT, can you please explain what Kubernetes is?",
  "strategy": "algorithmic"
}
```

## Example response

```json
{
  "original": "Hey ChatGPT, can you please explain what Kubernetes is?",
  "optimized": "Explain what Kubernetes is?",
  "original_tokens": 15,
  "optimized_tokens": 6,
  "saved_tokens": 9,
  "reduction_percent": 60.0,
  "applied": true,
  "strategy": "algorithmic",
  "rules_applied": [
    "greeting_removal",
    "conversational_filler"
  ],
  "validation_passed": true
}
```

Example counts are illustrative.

Actual counts must come from the tokenizer.

## Requirements

- Require authentication.
- Apply rate limiting.
- Do not call an LLM.
- Do not store raw prompt text by default.
- Return accurate transformation metadata.
- Return explicit skip reasons.
- Support previewing the original request when compression is not applied.

## Acceptance criteria

- Preview works.
- Counts are calculated correctly.
- Rules are reported accurately.
- No provider API call occurs.

---

# PHASE 8 — AUTHENTICATION, DATABASE, AND RATE LIMITING

## Objective

Secure the gateway for multiple developers.

## Authentication

Implement:

- Secure gateway API key generation
- Key verification
- Key revocation
- Key expiration
- Tenant association
- Protected administrative key creation
- Tenant isolation

Never expose an unauthenticated key-generation endpoint.

## Database

Use PostgreSQL.

Create tables for:

- Tenants
- API keys
- Usage records
- Optimization results
- Tenant configuration

Use Alembic migrations.

Store no raw prompts or responses by default.

## Redis

Implement:

- Per-key request limits
- Tenant-level limits
- Maximum concurrency
- Preview request limits
- Configurable rate limit policies

Do not silently disable rate limits in production when Redis is unavailable.

## Acceptance criteria

- Unauthorized requests fail.
- Revoked keys fail.
- Expired keys fail.
- Tenant isolation is enforced.
- Rate limits work.
- Database migrations run successfully.

---

# PHASE 9 — INTEGRATE COMPRESSION INTO THE GATEWAY

## Objective

Connect the compression pipeline to real LLM requests.

Processing order:

1. Authenticate request.
2. Validate request.
3. Identify provider and model.
4. Analyze eligible prompt content.
5. Calculate original token estimates.
6. Run the CompressionRouter.
7. Apply eligible algorithmic transformations.
8. Validate candidate.
9. Evaluate token savings.
10. Forward selected request.
11. Return provider response.
12. Record usage and optimization metrics.

## Important behavior

Compression must be optional.

If compression fails, use the original prompt.

Do not change system or developer messages.

Do not modify tool definitions or unrelated request fields.

Do not alter provider responses to exaggerate savings.

Preserve streaming behavior.

Do not introduce unnecessary provider calls.

## Acceptance criteria

- Gateway works with compression enabled.
- Gateway works with compression disabled.
- Streaming remains compatible.
- Failed compression falls back safely.
- Token metrics are recorded.

---

# PHASE 10 — COST-AWARE OPTIMIZATION

## Objective

Ensure compression provides actual economic value.

Create a cost evaluation module.

## Cost inputs

Support:

- Target model
- Input token price
- Output token price
- Cached input token price
- Estimated tokens removed
- Compression compute cost
- Optional future semantic model cost

Use configurable pricing data.

Do not hardcode prices as permanent truth.

## Savings calculation

Calculate:

`gross_savings = estimated_saved_input_tokens × applicable_input_price_per_token`

Then:

`net_savings = gross_savings - compression_cost`

Account for cached-token pricing where available.

For the algorithmic MVP, estimate local processing costs conservatively when practical.

## Important

Actual provider billing can differ from estimates.

Do not present estimates as confirmed charges.

Measure provider-reported usage separately.

For benchmark comparisons, use equivalent requests and account for caching and output-token differences.

## Acceptance criteria

- Cost calculations are tested.
- Pricing is configurable.
- Negative net savings are detected.
- Estimates are labeled appropriately.
- No invented pricing data is presented.

---

# PHASE 11 — TELEMETRY AND ANALYTICS

## Objective

Provide developers with measurable optimization results.

Implement:

`GET /v1/usage`

Track:

- Total requests
- Optimized requests
- Pass-through requests
- Compression attempts
- Compression successes
- Compression failures
- Estimated tokens saved
- Estimated percentage reduction
- Provider-reported input tokens
- Provider-reported output tokens
- Optimization latency
- Gateway latency
- Provider latency
- Error rates
- Compression rule effectiveness

## Example response

```json
{
  "total_requests": 1000,
  "optimized_requests": 420,
  "pass_through_requests": 580,
  "estimated_original_tokens": 500000,
  "estimated_forwarded_tokens": 410000,
  "estimated_tokens_saved": 90000,
  "estimated_reduction_percent": 18.0
}
```

All numbers are illustrative.

## Requirements

- Tenant-scoped results.
- Date filtering.
- Efficient database queries.
- No raw prompt storage.
- Clear distinction between estimated and actual usage.
- No sensitive content in logs or traces.

## Acceptance criteria

- Usage metrics are persisted.
- Tenant isolation works.
- Metrics calculations are tested.
- Analytics endpoint returns accurate stored data.

---

# PHASE 12 — COMPRESSION BENCHMARKING

## Objective

Prove that the compression engine is useful.

Create a benchmark suite with at least 100 representative prompts.

Include:

- Short conversational prompts
- Long natural-language prompts
- Programming requests
- Kubernetes questions
- Infrastructure automation prompts
- Structured output instructions
- JSON-containing prompts
- Code blocks
- Shell commands
- Technical documentation
- Security-sensitive prompts
- Prompts with negation
- Repeated instructions
- Mixed-language text
- Long conversation contexts

## Metrics

Measure:

- Compression eligibility rate
- Original token count
- Optimized token count
- Tokens saved
- Compression ratio
- Compression latency
- Rule effectiveness
- Validation rejection rate
- Pass-through rate

Export results to JSON and CSV.

## Quality evaluation

Design an optional evaluation workflow comparing original and compressed prompt responses.

Use:

- Deterministic assertions where possible
- Structured output comparisons
- Code execution tests where safe
- Task-specific grading
- Optional model-based evaluation

Do not assume that text similarity guarantees response equivalence.

Do not fabricate benchmark results.

## Acceptance criteria

- Benchmark runner executes locally.
- Results are reproducible.
- Reports are generated.
- Compression failures are visible.
- Quality evaluation is documented separately.

---

# PHASE 13 — SECURITY AND PERFORMANCE HARDENING

## Objective

Prepare the MVP for controlled deployment.

Implement:

- Secure secret management
- TLS-ready deployment
- Payload size limits
- Request timeouts
- Connection pooling
- Safe retries
- Streaming cancellation
- Tenant isolation
- Rate limiting
- Structured error handling
- Secure container configuration
- Provider endpoint allowlisting
- Protection against SSRF
- Dependency vulnerability scanning
- Graceful shutdown
- Request correlation IDs

## Performance goals

Aim for:

- Minimal additional request latency
- Efficient tokenization
- Low-overhead algorithmic compression
- Nonblocking network I/O
- Efficient database writes
- Streaming without full buffering

Use a target of under 30 ms p95 additional local processing time for conservative compression on a representative benchmark workload.

Do not claim this target is achieved without measurement.

## Acceptance criteria

- Security tests pass.
- Load tests run.
- Container builds.
- Performance measurements are documented.
- Remaining security limitations are disclosed.

---

# PHASE 14 — OPTIONAL SEMANTIC COMPRESSION FOUNDATION

## Objective

Prepare the system for AI-powered compression without making it a mandatory dependency.

Create a `SemanticCompressor` interface.

Support future adapters for:

- Ollama
- Local inference servers
- External LLM APIs

## Semantic compression workflow

When implemented in a later release:

1. Inspect prompt complexity.
2. Determine semantic compression eligibility.
3. Estimate potential savings.
4. Estimate inference cost.
5. Invoke the configured semantic model.
6. Generate a compressed candidate.
7. Validate protected content.
8. Check explicit constraints.
9. Compare token counts.
10. Evaluate net cost savings.
11. Accept or reject the candidate.
12. Record quality and cost metrics.

## Semantic validation

Recognize that semantic preservation cannot be guaranteed by simple string checks.

Provide mechanisms for:

- Structured requirement extraction
- Constraint preservation checks
- Protected-span verification
- Task-specific regression evaluation
- Optional model-based evaluation
- Automatic rejection when uncertain

## Important restrictions

Do not automatically enable semantic compression.

Do not invoke paid inference services without explicit configuration.

Do not implement a multi-step autonomous AI agent unless there is a demonstrated need.

Do not present an unimplemented semantic compressor as operational.

For this phase, implement the interface, configuration, documentation, and isolated tests needed for future expansion.

Full AI compression is outside the initial MVP acceptance criteria.

---

# PHASE 15 — DOCUMENTATION AND CI/CD

## Documentation

Create:

- README.md
- Architecture documentation
- API documentation
- Compression algorithm documentation
- Security documentation
- Deployment guide
- Benchmark methodology
- Future roadmap

Document:

- How the gateway works
- How developers integrate it
- How compression rules work
- Which content is protected
- How compression decisions are made
- How savings are calculated
- How to configure the gateway
- How to run tests
- How to deploy with Docker
- Known limitations

## CI/CD

Create GitHub Actions workflows for:

- Python linting
- Formatting checks
- Type checking
- Unit tests
- Integration tests
- Compatibility tests
- Security tests
- Docker image build
- Dependency scanning

CI must not require paid API credentials.

Do not automatically deploy to production.

---

# 16. DEVELOPMENT AND EXECUTION RULES

Follow these rules throughout the project.

### Rule 1 — Implement real functionality

Do not stop at architecture diagrams, empty classes, or pseudocode.

### Rule 2 — Build incrementally

Complete each phase before introducing the next dependent phase.

### Rule 3 — Test continuously

Run relevant tests after each phase.

Fix failures before proceeding.

### Rule 4 — Preserve existing work

Inspect the repository before making changes.

Do not overwrite unrelated files.

### Rule 5 — Prefer correctness over compression

A prompt that remains unchanged is preferable to an unsafe compressed prompt.

### Rule 6 — Keep compression independent

The compression engine must be usable independently of FastAPI and the provider adapter.

### Rule 7 — Avoid unnecessary AI calls

The algorithmic compressor must operate locally.

### Rule 8 — Avoid overengineering

Use a modular monolith.

Do not introduce unnecessary distributed infrastructure.

### Rule 9 — Document limitations

Distinguish between completed, partially implemented, untested, and future functionality.

### Rule 10 — Maintain progress

Update:

`docs/implementation-status.md`

After every phase, record:

- Completed work
- Files changed
- Tests executed
- Test results
- Outstanding issues
- Next phase

### Rule 11 — Handle execution limits

If the environment or context window prevents completing the project in one session, preserve the implementation state and provide clear continuation instructions.

### Rule 12 — Security first

Do not disable authentication, validation, or tenant isolation to make tests pass.

---

# 17. MVP DEFINITION OF DONE

The MVP is complete when:

- FastAPI gateway runs.
- OpenAI-compatible proxy works for documented supported requests.
- Streaming works.
- API authentication works.
- PostgreSQL persistence works.
- Redis rate limiting works.
- Model-aware token counting works.
- Algorithmic compression works.
- Compression validation works.
- Protected content remains unchanged in tests.
- Unsafe candidates fall back to the original prompt.
- Compression preview API works.
- CompressionRouter works.
- Usage analytics work.
- Benchmark runner works.
- Docker Compose works.
- Automated tests pass.
- CI configuration exists.
- Documentation is complete.
- No paid AI compression service is required.
- Semantic compression remains optional and disabled.

The MVP must function even when no semantic compression model is installed.

A real provider credential may be required for live API calls, but ordinary automated tests must use mocked provider responses.

---

# 18. FINAL DELIVERABLES

Provide:

1. Complete source code.
2. Working Python compression algorithm.
3. Functional FastAPI gateway.
4. Tokenization engine.
5. RuleCompressor.
6. CompressionRouter.
7. CompressionValidator.
8. Protected-content detector.
9. Cost evaluation module.
10. OpenAI provider adapter.
11. Streaming support.
12. Authentication.
13. Database migrations.
14. Redis rate limiting.
15. Usage analytics.
16. Benchmark suite.
17. Docker deployment configuration.
18. Automated tests.
19. GitHub Actions CI.
20. Complete documentation.
21. AGENTS.md development instructions.
22. Implementation status report.
23. Future semantic compression interface.

---

# 19. START DEVELOPMENT

Begin by inspecting the repository.

Read any existing AGENTS.md and project documentation.

If the repository is empty, initialize the project.

Create a concise development plan and identify any essential architectural decisions.

Then immediately begin Phase 1.

Implement actual code, not just plans.

After each phase:

1. Run relevant tests.
2. Fix failures.
3. Update implementation-status.md.
4. Summarize progress.
5. Continue to the next phase when feasible.

Do not request approval for ordinary implementation decisions.

Request approval before destructive operations, production deployments, or actions requiring credentials or external spending.

Continue through the development phases until the MVP acceptance criteria are satisfied or a genuine execution limitation prevents further progress.

**Build the Prompt Gateway as a functional, secure, measurable, developer-focused prompt optimization platform.**
# Development rules

Build the phases in docs/implementation-status.md in order. Run relevant tests and
record evidence after each phase; do not claim unexecuted checks passed.
Preserve existing work. Prefer unchanged prompts over uncertain transformations.
Keep compression independent of HTTP and provider code. Never modify system or
developer messages, protected content, or unrelated request fields.
Never log or persist raw prompts, responses, credentials, or authorization headers.
Use mocked providers in ordinary tests; no paid inference calls without explicit configuration.
Require authentication and tenant isolation. Redis failure must fail closed.
Semantic and hybrid modes remain explicitly unavailable until implemented and evaluated.
Run Ruff, mypy and pytest before declaring a phase complete.
Do not deploy or push without user authorization.

# Benchmark methodology

Run `python -m scripts.benchmark --output artifacts` after provisioning tokenizer data.
The checked-in dataset has 120 synthetic prompts: eight topics across fifteen
categories, including structured content, commands, code, negation, repetition,
mixed languages and long context. It is a regression workload, not a representative
sample of all customer traffic. Topic/template expansion may bias measured coverage.

JSON contains aggregate metrics and per-prompt IDs/counts/latencies/skip reasons;
CSV contains per-prompt results without raw prompts. Tokenizer loading is warmed
before measurement. Timing uses perf_counter; host load and hardware affect results.
Token counts and decisions are reproducible for a fixed lockfile; timing is not.
Errors are explicit, not excluded. Validation rejection includes insufficient
savings. The broad eligibility rate means not protected/ambiguous, not guaranteed
applicability or preserved response quality.

Initial local run: 120 prompts, zero errors, 13,456 original estimated tokens,
13,336 optimized, 120 saved (0.89%), 20% applied, 80% pass-through. Warm compression
p95 was about 12ms. See `artifacts/benchmark.json` for the actual run. This measures
the compression engine only; it does not establish the under-30ms p95 target for
all added gateway processing. The conservative algorithm may have small economic
benefit on real traffic, especially when constraints cause whole-message bypass.

Optional quality evaluation must be separately authorized/configured for provider
calls. Pair identical original/optimized requests, record model snapshot and all
parameters, track cached/uncached input and output usage, and compare deterministic
requirements, parsed structured outputs, and task-specific grading. Execute generated
code only in an isolated sandbox. Use blinded human review and optional model
judging with a disclosed rubric. Never infer semantic equivalence from text similarity.
No response-quality or paid-provider benchmark has been run in this project.

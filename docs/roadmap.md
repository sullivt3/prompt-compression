# Roadmap

The initial gateway intentionally supports a text-only Chat Completions subset and
conservative deterministic rules. Follow-on work should be driven by representative
customer workloads and response-quality evaluation, rather than compression ratio.

Future work: richer typed tool/multimodal pass-through; tokenizer framing registry
with evaluated per-model request estimates; explicit duplicate-removal permissions;
stronger task/constraint classifiers; durable telemetry and retention; external OTLP
export; distributed deployment/load/cancellation testing; cache-aware economics.

Semantic compression is reserved and disabled. Future adapters may use Ollama,
local inference, OpenAI or Anthropic only after explicit configuration, quality and
cost evaluation, protected-content validation and automatic rejection when uncertain.
No autonomous multi-step agent is required. Interface tests must never invoke inference.

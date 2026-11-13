"""Offline token/latency benchmark. No provider calls or response-quality claims."""

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

from app.compression.router import CompressionRouter


def run(output: Path, dataset: Path, model: str) -> dict[str, object]:
    prompts = json.loads(dataset.read_text())
    router = CompressionRouter()
    router.counter.count_text("warm up tokenizer", model)
    rows = []
    rules: Counter[str] = Counter()
    for prompt in prompts:
        try:
            result = router.optimize(prompt["text"], model)
            rules.update(result["rules_applied"])
            rows.append(
                {
                    "id": prompt["id"],
                    "category": prompt["category"],
                    **{
                        k: result[k]
                        for k in [
                            "original_tokens",
                            "optimized_tokens",
                            "saved_tokens",
                            "applied",
                            "skip_reason",
                            "optimization_latency_ms",
                        ]
                    },
                    "error": None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "id": prompt["id"],
                    "category": prompt["category"],
                    "original_tokens": 0,
                    "optimized_tokens": 0,
                    "saved_tokens": 0,
                    "applied": False,
                    "skip_reason": "error",
                    "optimization_latency_ms": 0,
                    "error": type(exc).__name__,
                }
            )
    latencies = sorted(row["optimization_latency_ms"] for row in rows)
    original = sum(row["original_tokens"] for row in rows)
    optimized = sum(row["optimized_tokens"] for row in rows)
    applied = sum(row["applied"] for row in rows)
    errors = sum(row["error"] is not None for row in rows)
    summary = {
        "model": model,
        "count": len(rows),
        "errors": errors,
        "eligible_rate": sum(
            row["skip_reason"] not in {"protected_content", "ambiguous_content"} for row in rows
        )
        / len(rows),
        "applied_rate": applied / len(rows),
        "pass_through_rate": 1 - applied / len(rows),
        "original_tokens": original,
        "optimized_tokens": optimized,
        "saved_tokens": original - optimized,
        "reduction_percent": 100 * (original - optimized) / original if original else 0,
        "validation_rejection_rate": sum(row["skip_reason"] == "validation_failed" for row in rows)
        / len(rows),
        "latency_p50_ms": statistics.median(latencies),
        "latency_p95_ms": latencies[min(len(rows) - 1, int(len(rows) * 0.95))],
        "rule_effectiveness": dict(rules),
        "tokenizer_warmed": True,
        "quality_evaluated": False,
        "estimate": True,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    with (output / "benchmark.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    parser.add_argument("--dataset", type=Path, default=Path("tests/benchmarks/prompts.json"))
    parser.add_argument("--model", default="gpt-4.1-mini")
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.dataset, args.model), indent=2))

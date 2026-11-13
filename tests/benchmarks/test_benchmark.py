from pathlib import Path

from scripts.benchmark import run


def test_benchmark_exports(tmp_path: Path) -> None:
    report = run(tmp_path, Path("tests/benchmarks/prompts.json"), "gpt-4.1-mini")
    assert report["count"] >= 100
    assert report["errors"] == 0
    assert (tmp_path / "benchmark.csv").exists()
    assert report["quality_evaluated"] is False

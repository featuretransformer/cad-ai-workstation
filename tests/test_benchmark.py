"""
Unit Tests for CAD Workstation Benchmark Suite.
Verifies prompt specifications, trial execution, and metric reporting.
"""
import pytest
from pathlib import Path
import sys

# Ensure backend and scripts directories are in sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
scripts_dir = root_dir / "scripts"
for d in (backend_dir, scripts_dir):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from benchmark import (
    BENCHMARK_PROMPTS,
    run_baseline_trial,
    run_enhanced_trial,
    run_benchmark,
)


def test_benchmark_prompts_coverage():
    """Verify that all 10 specification prompts (L1 to L5) are defined."""
    assert len(BENCHMARK_PROMPTS) == 10
    expected_keys = ["L1-1", "L1-2", "L2-1", "L2-2", "L3-1", "L3-2", "L4-1", "L4-2", "L5-1", "L5-2"]
    for k in expected_keys:
        assert k in BENCHMARK_PROMPTS
        assert BENCHMARK_PROMPTS[k]["level"].startswith("L")
        assert len(BENCHMARK_PROMPTS[k]["prompt"]) > 10


def test_benchmark_enhanced_trial():
    """Verify enhanced trial execution on L1-1 (rectangular box)."""
    p_info = BENCHMARK_PROMPTS["L1-1"]
    res = run_enhanced_trial("L1-1", p_info["prompt"])

    assert res["mode"] == "enhanced"
    assert res["prompt_id"] == "L1-1"
    assert res["cadir_valid"] is True
    assert res["success"] is True
    assert res["watertight"] is True
    assert res["latency_sec"] > 0
    assert res["dfm_score"] >= 80


def test_benchmark_summary_aggregation(tmp_path):
    """Verify benchmark execution and summary calculation on L1 complexity level."""
    out_file = tmp_path / "benchmark_test_results.json"
    results = run_benchmark(levels=["L1"], output_file=out_file)

    assert results["total_cases"] == 2
    assert "summary" in results
    summary = results["summary"]
    assert summary["enhanced_success_rate"] == 100.0
    assert summary["enhanced_cadir_valid_rate"] == 100.0
    assert summary["enhanced_watertight_rate"] == 100.0
    assert out_file.exists()

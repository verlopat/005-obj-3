"""Smoke tests for the benchmarking module."""
import pytest
from src.benchmark import run_benchmark


def test_benchmark_returns_four_systems():
    results = run_benchmark()
    # RF, SVM, BC-only, Integrated
    assert len(results) == 4


def test_integrated_has_blockchain():
    results = run_benchmark()
    integrated = [r for r in results if "Integrated" in r["system"]]
    assert len(integrated) == 1
    assert integrated[0]["blockchain"] is True


def test_f1_scores_in_range():
    results = run_benchmark()
    for r in results:
        assert 0.0 <= r["f1_score"] <= 1.0

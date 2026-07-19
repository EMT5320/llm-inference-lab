"""Tests for benchmark metrics."""

import pytest

from llm_inference_lab.bench.metrics import aggregate_round, percentile


def test_percentile_interpolates() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert percentile(values, 0.5) == 2.5


def test_aggregate_round_computes_qps_and_ttft() -> None:
    results = [
        {"ok": True, "latency_s": 1.0, "ttft_s": 0.1, "completion_tokens": 10, "prompt_tokens": 5, "tps": 10.0},
        {"ok": True, "latency_s": 2.0, "ttft_s": 0.2, "completion_tokens": 20, "prompt_tokens": 5, "tps": 10.0},
    ]
    summary = aggregate_round(results, concurrency=2, requests_per_worker=1, wall_s=2.0)
    assert summary["success_count"] == 2
    assert summary["qps"] == 1.0
    assert summary["aggregate_tps"] == 15.0
    assert summary["p50_latency_s"] == 1.5
    assert summary["p50_ttft_ms"] == pytest.approx(150.0)


def test_aggregate_round_does_not_invent_token_throughput_without_usage() -> None:
    results = [
        {
            "ok": True,
            "latency_s": 1.0,
            "ttft_s": 0.1,
            "completion_tokens": None,
            "prompt_tokens": None,
            "tps": None,
            "token_count_source": "unavailable",
        }
    ]

    summary = aggregate_round(results, concurrency=1, requests_per_worker=1, wall_s=1.0)

    assert summary["success_count"] == 1
    assert summary["aggregate_tps"] is None
    assert summary["avg_request_tps"] is None
    assert summary["total_completion_tokens"] is None
    assert summary["token_count_coverage"] == 0.0

"""Benchmark metric helpers."""

from __future__ import annotations

import statistics
from typing import Any


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile on a sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def aggregate_round(results: list[dict[str, Any]], *, concurrency: int, requests_per_worker: int, wall_s: float) -> dict[str, Any]:
    """Aggregate per-request results into one benchmark round summary."""
    successes = [item for item in results if item.get("ok")]
    failures = [item for item in results if not item.get("ok")]
    latencies = sorted(float(item["latency_s"]) for item in successes)
    ttfts = sorted(float(item["ttft_s"]) for item in successes if item.get("ttft_s") is not None)
    total_completion_tokens = sum(int(item.get("completion_tokens") or 0) for item in successes)
    total_prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in successes)
    total_requests = len(results)
    success_count = len(successes)

    return {
        "concurrency": concurrency,
        "requests_per_worker": requests_per_worker,
        "total_requests": total_requests,
        "success_count": success_count,
        "failure_count": len(failures),
        "success_rate": (success_count / total_requests) if total_requests else 0.0,
        "wall_s": wall_s,
        "qps": (success_count / wall_s) if wall_s > 0 else 0.0,
        "aggregate_tps": (total_completion_tokens / wall_s) if wall_s > 0 else 0.0,
        "avg_request_tps": statistics.mean(float(item["tps"]) for item in successes) if successes else 0.0,
        "avg_latency_s": statistics.mean(latencies) if latencies else 0.0,
        "p50_latency_s": percentile(latencies, 0.50),
        "p95_latency_s": percentile(latencies, 0.95),
        "max_latency_s": max(latencies) if latencies else 0.0,
        "p50_ttft_ms": percentile(ttfts, 0.50) * 1000 if ttfts else None,
        "p95_ttft_ms": percentile(ttfts, 0.95) * 1000 if ttfts else None,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "failures": failures[:5],
    }

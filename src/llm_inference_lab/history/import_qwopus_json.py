"""Import benchmark_qwopus35.py JSON output into history records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import BENCH_RUN_SCHEMA_VERSION, HISTORY_RECORD_SCHEMA_VERSION


def import_qwopus_json(path: Path) -> dict[str, Any]:
    """Convert legacy qwopus benchmark JSON into a history record."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("qwopus benchmark JSON must be an object")
    rounds = payload.get("rounds") or []
    normalized_rounds = []
    for row in rounds:
        normalized_rounds.append(_normalize_round(row))
    return {
        "schema_version": HISTORY_RECORD_SCHEMA_VERSION,
        "bench_schema_version": BENCH_RUN_SCHEMA_VERSION,
        "source": "history",
        "evidence_class": "historical/imported",
        "source_file": path.name,
        "endpoint_id": "qwopus35_a10",
        "model": str(payload.get("model") or "qwopus35"),
        "base_url": payload.get("base_url"),
        "hardware": "4xA10",
        "test_date": payload.get("test_date"),
        "notes": "Imported from benchmark_qwopus35.py --output-json format.",
        "concurrency_levels": payload.get("concurrency_levels") or [row["concurrency"] for row in normalized_rounds],
        "rounds": normalized_rounds,
        "threshold_concurrency_with_failure": payload.get("threshold_concurrency_with_failure"),
        "provenance": {
            "importer": "illab-import-history",
            "source_path": str(path),
        },
    }


def write_qwopus_history(path: Path, output_path: Path) -> dict[str, Any]:
    """Import qwopus JSON and write normalized history artifact."""
    payload = import_qwopus_json(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _normalize_round(row: dict[str, Any]) -> dict[str, Any]:
    ttft_ms = row.get("p50_ttft_ms")
    return {
        "concurrency": int(row["concurrency"]),
        "requests_per_worker": int(row.get("requests_per_worker") or 0),
        "total_requests": int(row.get("total_requests") or 0),
        "success_count": int(row.get("success_count") or 0),
        "failure_count": int(row.get("failure_count") or 0),
        "success_rate": float(row.get("success_rate") or 0.0),
        "wall_s": row.get("wall_s"),
        "qps": row.get("qps"),
        "aggregate_tps": row.get("aggregate_tps"),
        "avg_request_tps": row.get("avg_request_tps"),
        "avg_latency_s": row.get("avg_latency_s"),
        "p50_latency_s": row.get("p50_latency_s"),
        "p95_latency_s": row.get("p95_latency_s"),
        "max_latency_s": row.get("max_latency_s"),
        "p50_ttft_ms": ttft_ms,
        "p95_ttft_ms": row.get("p95_ttft_ms"),
        "total_prompt_tokens": row.get("total_prompt_tokens"),
        "total_completion_tokens": row.get("total_completion_tokens"),
        "failures": row.get("failures") or [],
    }

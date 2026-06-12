"""Report export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_report(payload: dict[str, Any], path: Path) -> None:
    """Write a benchmark JSON report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_bench_markdown(payload: dict[str, Any]) -> str:
    """Render one benchmark run as markdown."""
    lines = [
        f"# Inference Benchmark Report — {payload.get('endpoint_id', 'unknown')}",
        "",
        f"- schema_version: `{payload.get('schema_version')}`",
        f"- run_id: `{payload.get('run_id', 'n/a')}`",
        f"- source: `{payload.get('source', 'live')}`",
        f"- model: `{payload.get('model')}`",
        f"- base_url: `{payload.get('base_url')}`",
        f"- stream: `{payload.get('stream')}`",
        f"- max_tokens: `{payload.get('max_tokens')}`",
        "",
        "| concurrency | success | qps | agg_tps | p50_lat | p95_lat | p50_ttft | p95_ttft |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload.get("rounds") or []:
        lines.append(
            "| {concurrency} | {success}/{total} | {qps:.2f} | {agg:.2f} | {p50:.2f}s | {p95:.2f}s | {ttft50} | {ttft95} |".format(
                concurrency=row["concurrency"],
                success=row["success_count"],
                total=row["total_requests"],
                qps=float(row.get("qps") or 0.0),
                agg=float(row.get("aggregate_tps") or 0.0),
                p50=float(row.get("p50_latency_s") or 0.0),
                p95=float(row.get("p95_latency_s") or 0.0),
                ttft50=_fmt_ms(row.get("p50_ttft_ms")),
                ttft95=_fmt_ms(row.get("p95_ttft_ms")),
            )
        )
    failures = []
    for row in payload.get("rounds") or []:
        failures.extend(row.get("failures") or [])
    if failures:
        lines.extend(["", "## Failures (sample)", ""])
        for item in failures[:5]:
            lines.append(f"- `{item.get('request_id', 'unknown')}`: {item.get('error', 'unknown error')}")
    lines.append("")
    return "\n".join(lines)


def write_bench_markdown(payload: dict[str, Any], path: Path) -> None:
    """Write markdown report for one benchmark run."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_bench_markdown(payload), encoding="utf-8")


def _fmt_ms(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}ms"

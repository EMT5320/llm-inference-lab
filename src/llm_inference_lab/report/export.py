"""Report export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HISTORICAL_IMPORTED = "historical/imported"
LIVE_RERUN = "live/rerun"
PENDING_OWNER_RERUN = "pending/owner-rerun"


def write_json_report(payload: dict[str, Any], path: Path) -> None:
    """Write a benchmark JSON report."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_bench_markdown(payload: dict[str, Any]) -> str:
    """Render one benchmark run as markdown."""
    evidence_class = _evidence_class(payload)
    hardware = _hardware_label(payload)
    lines = [
        f"# Inference Benchmark Report — {payload.get('endpoint_id', 'unknown')}",
        "",
        f"- schema_version: `{payload.get('schema_version')}`",
        f"- run_id: `{payload.get('run_id', 'n/a')}`",
        f"- source: `{payload.get('source', 'live')}`",
        f"- evidence_class: `{evidence_class}`",
        f"- model: `{payload.get('model')}`",
        f"- base_url: `{payload.get('base_url')}`",
        f"- stream: `{payload.get('stream')}`",
        f"- max_tokens: `{payload.get('max_tokens')}`",
        "",
        "## Four-axis Evidence",
        "",
        "| axis | fields | status |",
        "|---|---|---|",
        "| throughput | `qps`, `aggregate_tps`, `token_count_coverage` | token TPS requires complete server usage |",
        "| latency | `p50/p90/p95_latency_s`, `p50/p95_ttft_ms` | measured per concurrency round |",
        f"| memory/hardware | `hardware`, `gpu_telemetry` | {hardware} |",
        "| concurrency success | `success_count`, `total_requests`, `success_rate` | measured per concurrency round |",
        "",
        "## Rounds",
        "",
        "| concurrency | success | success_rate | qps | agg_tps | token_usage | p50_lat | p90_lat | p95_lat | p50_ttft | p95_ttft |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload.get("rounds") or []:
        lines.append(
            "| {concurrency} | {success}/{total} | {success_rate} | {qps} | {agg} | {token_usage} | {p50} | {p90} | {p95} | {ttft50} | {ttft95} |".format(
                concurrency=row["concurrency"],
                success=_fmt_count(row.get("success_count")),
                total=_fmt_count(row.get("total_requests")),
                success_rate=_fmt_pct(row.get("success_rate")),
                qps=_fmt_num(row.get("qps")),
                agg=_fmt_num(row.get("aggregate_tps")),
                token_usage=_fmt_pct(row.get("token_count_coverage")),
                p50=_fmt_seconds(row.get("p50_latency_s")),
                p90=_fmt_seconds(row.get("p90_latency_s")),
                p95=_fmt_seconds(row.get("p95_latency_s")),
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


def _fmt_num(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def _fmt_seconds(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}s"


def _fmt_count(value: Any) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    if number <= 1.0:
        number *= 100.0
    return f"{number:.0f}%"


def _evidence_class(payload: dict[str, Any]) -> str:
    evidence_class = str(payload.get("evidence_class") or "").strip().lower()
    if evidence_class in {HISTORICAL_IMPORTED, LIVE_RERUN, PENDING_OWNER_RERUN}:
        return evidence_class

    source = str(payload.get("source") or "live").strip().lower()
    if source in {"history", "historical", "imported"}:
        return HISTORICAL_IMPORTED
    if source == "pending":
        return PENDING_OWNER_RERUN
    return LIVE_RERUN


def _hardware_label(payload: dict[str, Any]) -> str:
    hardware = payload.get("hardware") or payload.get("hardware_profile")
    telemetry = payload.get("gpu_telemetry") or payload.get("telemetry") or {}
    telemetry_status = ""
    if isinstance(telemetry, dict):
        telemetry_status = str(telemetry.get("status") or "").strip()
    elif telemetry:
        telemetry_status = str(telemetry)

    if hardware:
        label = str(hardware)
        if telemetry_status:
            return f"{label}; telemetry {telemetry_status}"
        if _evidence_class(payload) == HISTORICAL_IMPORTED:
            return f"{label}; imported"
        return label
    if str(payload.get("endpoint_id") or "") == "mock_local" or str(payload.get("model") or "") == "mock-model":
        return "CPU mock; no GPU telemetry"
    return PENDING_OWNER_RERUN

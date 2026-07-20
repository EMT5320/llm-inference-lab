"""Markdown leaderboard synthesis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import HISTORICAL_IMPORTED, LIVE_RERUN, PENDING_RERUN, normalize_evidence_class


def load_records(paths: list[Path]) -> list[dict[str, Any]]:
    """Load benchmark or history JSON records."""
    records: list[dict[str, Any]] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            records.append(payload)
    return records


def collect_leaderboard_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten records into leaderboard rows."""
    rows: list[dict[str, Any]] = []
    for record in records:
        model = str(record.get("model") or "unknown")
        evidence_class = normalize_evidence_class(record)
        endpoint_id = str(record.get("endpoint_id") or "unknown")
        test_date = record.get("test_date") or record.get("provenance", {}).get("timestamp_utc", "n/a")
        notes = str(record.get("notes") or "")
        hardware = _hardware_label(record)
        for round_row in record.get("rounds") or []:
            rows.append(
                {
                    "model": model,
                    "endpoint_id": endpoint_id,
                    "evidence_class": evidence_class,
                    "test_date": test_date,
                    "concurrency": round_row.get("concurrency"),
                    "aggregate_tps": round_row.get("aggregate_tps"),
                    "qps": round_row.get("qps"),
                    "p50_latency_s": round_row.get("p50_latency_s"),
                    "p90_latency_s": round_row.get("p90_latency_s"),
                    "p95_latency_s": round_row.get("p95_latency_s"),
                    "p50_ttft_ms": round_row.get("p50_ttft_ms"),
                    "p95_ttft_ms": round_row.get("p95_ttft_ms"),
                    "success_rate": round_row.get("success_rate"),
                    "hardware": hardware,
                    "notes": notes,
                }
            )
    rows.sort(key=lambda item: (item["model"], item.get("concurrency") or 0))
    return rows


def render_leaderboard(records: list[dict[str, Any]], *, pending_models: list[str] | None = None) -> str:
    """Render a markdown leaderboard from records."""
    rows = collect_leaderboard_rows(records)
    lines = [
        "# Inference Leaderboard",
        "",
        "- Claim boundary: `historical/imported` rows come from imported artifacts; `live/rerun` rows come from current `illab-bench` reruns; `pending/rerun` rows carry no numeric claim.",
        "- Four-axis scope: throughput (`agg_tps`, `qps`, `token_count_coverage`), latency (`p50/p90/p95`, `TTFT`), memory/hardware (`hardware/telemetry`), and concurrency success (`success_rate`).",
        "",
        "| model | evidence | concurrency | agg_tps | qps | p50_lat | p90_lat | p95_lat | p50_ttft | success | hardware/telemetry | notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {model} | {evidence} | {concurrency} | {agg} | {qps} | {p50} | {p90} | {p95} | {ttft} | {success} | {hardware} | {notes} |".format(
                model=row["model"],
                evidence=_format_evidence(row),
                concurrency=row.get("concurrency", "n/a"),
                agg=_fmt_num(row.get("aggregate_tps")),
                qps=_fmt_num(row.get("qps")),
                p50=_fmt_latency(row.get("p50_latency_s")),
                p90=_fmt_latency(row.get("p90_latency_s")),
                p95=_fmt_latency(row.get("p95_latency_s")),
                ttft=_fmt_ms(row.get("p50_ttft_ms")),
                success=_fmt_pct(row.get("success_rate")),
                hardware=(row.get("hardware") or PENDING_RERUN)[:80],
                notes=(row.get("notes") or "")[:80],
            )
        )
    for model in pending_models or []:
        lines.append(
            f"| {model} | {PENDING_RERUN} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | {PENDING_RERUN} | planned GPU rerun; no numeric claim |"
        )
    lines.append("")
    return "\n".join(lines)


def write_leaderboard(records: list[dict[str, Any]], output_path: Path, *, pending_models: list[str] | None = None) -> None:
    """Write markdown leaderboard to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_leaderboard(records, pending_models=pending_models), encoding="utf-8")


def discover_json_files(*paths: Path) -> list[Path]:
    """Expand directories and glob patterns into JSON files."""
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        elif path.exists():
            files.append(path)
    return files


def _format_evidence(row: dict[str, Any]) -> str:
    evidence_class = str(row.get("evidence_class") or LIVE_RERUN)
    test_date = row.get("test_date")
    if evidence_class == HISTORICAL_IMPORTED and test_date:
        return f"{HISTORICAL_IMPORTED}/{test_date}"
    return evidence_class


def _hardware_label(record: dict[str, Any]) -> str:
    hardware = record.get("hardware") or record.get("hardware_profile")
    telemetry = record.get("gpu_telemetry") or record.get("telemetry") or {}
    telemetry_status = ""
    if isinstance(telemetry, dict):
        telemetry_status = str(telemetry.get("status") or "").strip()
    elif telemetry:
        telemetry_status = str(telemetry)

    if hardware:
        label = str(hardware)
        if telemetry_status:
            return f"{label}; telemetry {telemetry_status}"
        if normalize_evidence_class(record) == HISTORICAL_IMPORTED:
            return f"{label}; imported"
        return label
    if str(record.get("endpoint_id") or "") == "mock_local" or str(record.get("model") or "") == "mock-model":
        return "CPU mock; no GPU telemetry"
    return PENDING_RERUN


def _fmt_num(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}"


def _fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    if number <= 1.0:
        number *= 100.0
    return f"{number:.0f}%"


def _fmt_latency(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}s"


def _fmt_ms(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.0f}ms"

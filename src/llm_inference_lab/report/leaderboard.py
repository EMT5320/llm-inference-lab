"""Markdown leaderboard synthesis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
        source = str(record.get("source") or "live")
        endpoint_id = str(record.get("endpoint_id") or "unknown")
        test_date = record.get("test_date") or record.get("provenance", {}).get("timestamp_utc", "n/a")
        notes = str(record.get("notes") or "")
        for round_row in record.get("rounds") or []:
            rows.append(
                {
                    "model": model,
                    "endpoint_id": endpoint_id,
                    "source": source,
                    "test_date": test_date,
                    "concurrency": round_row.get("concurrency"),
                    "aggregate_tps": round_row.get("aggregate_tps"),
                    "qps": round_row.get("qps"),
                    "p50_latency_s": round_row.get("p50_latency_s"),
                    "p95_latency_s": round_row.get("p95_latency_s"),
                    "p50_ttft_ms": round_row.get("p50_ttft_ms"),
                    "p95_ttft_ms": round_row.get("p95_ttft_ms"),
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
        "| model | source | concurrency | agg_tps | qps | p50_lat | p95_lat | p50_ttft | notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {model} | {source} | {concurrency} | {agg} | {qps} | {p50} | {p95} | {ttft} | {notes} |".format(
                model=row["model"],
                source=_format_source(row),
                concurrency=row.get("concurrency", "n/a"),
                agg=_fmt_num(row.get("aggregate_tps")),
                qps=_fmt_num(row.get("qps")),
                p50=_fmt_latency(row.get("p50_latency_s")),
                p95=_fmt_latency(row.get("p95_latency_s")),
                ttft=_fmt_ms(row.get("p50_ttft_ms")),
                notes=(row.get("notes") or "")[:80],
            )
        )
    for model in pending_models or []:
        lines.append(f"| {model} | pending | n/a | n/a | n/a | n/a | n/a | n/a | run illab-bench when GPU ready |")
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


def _format_source(row: dict[str, Any]) -> str:
    source = str(row.get("source") or "live")
    test_date = row.get("test_date")
    if source == "history" and test_date:
        return f"history/{test_date}"
    return source


def _fmt_num(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}"


def _fmt_latency(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}s"


def _fmt_ms(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.0f}ms"

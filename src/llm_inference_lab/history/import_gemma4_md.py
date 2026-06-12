"""Import Gemma4 performance reference markdown into history JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .schema import BENCH_RUN_SCHEMA_VERSION, HISTORY_RECORD_SCHEMA_VERSION


def import_gemma4_markdown(path: Path) -> dict[str, Any]:
    """Parse gemma4_perf_reference.md tables into a history record."""
    text = path.read_text(encoding="utf-8")
    test_date_match = re.search(r"测试时间：(\d{4}-\d{2}-\d{2})", text)
    test_date = test_date_match.group(1) if test_date_match else "unknown"

    single_rows = _parse_table_section(text, "4.1 单请求延迟")
    output_rows = _parse_table_section(text, "4.2 不同输出长度 TPS")
    concurrency_rows = _parse_concurrency_section(text)

    rounds = []
    for row in concurrency_rows:
        rounds.append(
            {
                "concurrency": int(row["concurrency"]),
                "requests_per_worker": 20,
                "total_requests": 20,
                "success_count": 20,
                "failure_count": 0,
                "success_rate": 1.0,
                "wall_s": None,
                "qps": _parse_float(row.get("qps")),
                "aggregate_tps": _parse_float(row.get("aggregate_tps")),
                "avg_request_tps": _parse_float(row.get("avg_request_tps")),
                "avg_latency_s": None,
                "p50_latency_s": _parse_seconds(row.get("p50_latency")),
                "p95_latency_s": _parse_seconds(row.get("p90_latency")),
                "max_latency_s": None,
                "p50_ttft_ms": _parse_ms(row.get("p50_ttft")),
                "p95_ttft_ms": None,
                "total_prompt_tokens": None,
                "total_completion_tokens": None,
                "failures": [],
            }
        )

    return {
        "schema_version": HISTORY_RECORD_SCHEMA_VERSION,
        "bench_schema_version": BENCH_RUN_SCHEMA_VERSION,
        "source": "history",
        "source_file": path.name,
        "endpoint_id": "gemma4_a10",
        "model": "google/gemma-4-26B-A4B-it",
        "hardware": "4xA10-22GB",
        "max_model_len": 65536,
        "test_date": test_date,
        "notes": "Imported from gemma4_perf_reference.md §4 concurrency sweep.",
        "single_request_rows": single_rows,
        "output_length_rows": output_rows,
        "concurrency_levels": [row["concurrency"] for row in concurrency_rows],
        "rounds": rounds,
        "provenance": {
            "importer": "illab-import-history",
            "source_path": str(path),
        },
    }


def write_gemma4_history(path: Path, output_path: Path) -> dict[str, Any]:
    """Import markdown and write JSON history artifact."""
    payload = import_gemma4_markdown(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _parse_table_section(text: str, heading: str) -> list[dict[str, str]]:
    start = text.find(heading)
    if start < 0:
        return []
    section = text[start:]
    lines = []
    for line in section.splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in {"场景", "max_tokens", "并发数"}:
                lines.append(cells)
    headers = {
        "场景": "scenario",
        "输出 tokens": "output_tokens",
        "耗时": "latency",
        "TTFT": "ttft",
        "单请求 TPS": "tps",
        "max_tokens": "max_tokens",
        "实际输出": "actual_output",
        "TPS": "tps",
    }
    rows: list[dict[str, str]] = []
    for cells in lines:
        rows.append({"raw": " | ".join(cells)})
    return rows


def _parse_concurrency_section(text: str) -> list[dict[str, str]]:
    start = text.find("4.3 并发吞吐")
    if start < 0:
        return []
    section = text[start:]
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "并发数" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 7:
            continue
        rows.append(
            {
                "concurrency": cells[0],
                "aggregate_tps": cells[1],
                "qps": cells[2],
                "p50_latency": cells[3],
                "p90_latency": cells[4],
                "p50_ttft": cells[5],
                "avg_request_tps": cells[6],
            }
        )
    return rows


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([\d.]+)", value.replace(",", ""))
    return float(match.group(1)) if match else None


def _parse_seconds(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([\d.]+)s", value)
    return float(match.group(1)) if match else _parse_float(value)


def _parse_ms(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([\d.]+)ms", value)
    return float(match.group(1)) if match else _parse_float(value)

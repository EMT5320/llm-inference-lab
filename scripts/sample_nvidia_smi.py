"""Lightweight nvidia-smi JSONL sampler for owner GPU reruns."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

QUERY_FIELDS = [
    "timestamp",
    "index",
    "name",
    "memory.used",
    "memory.total",
    "utilization.gpu",
    "temperature.gpu",
    "power.draw",
]

OUTPUT_KEYS = [
    "nvidia_smi_timestamp",
    "gpu_index",
    "gpu_name",
    "memory_used_mib",
    "memory_total_mib",
    "utilization_gpu_pct",
    "temperature_gpu_c",
    "power_draw_w",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sample nvidia-smi into JSONL without extra dependencies.")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples when --duration is set.")
    parser.add_argument("--duration", type=float, default=0.0, help="Total sample duration in seconds; 0 means one sample.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSONL output path. Defaults to stdout.")
    parser.add_argument("--query-timeout", type=float, default=5.0, help="Per nvidia-smi query timeout in seconds.")
    args = parser.parse_args(argv)

    handle = None
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        handle = args.output.open("a", encoding="utf-8")

    try:
        deadline = time.monotonic() + args.duration if args.duration > 0 else None
        while True:
            payload = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "source": "nvidia-smi",
                "gpus": _sample_once(args.query_timeout),
            }
            _write_jsonl(payload, handle)
            if deadline is None:
                return 0
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return 0
            time.sleep(min(args.interval, remaining))
    except FileNotFoundError:
        _write_jsonl({"status": "error", "error": "nvidia-smi not found"}, handle)
        return 2
    except subprocess.SubprocessError as exc:
        _write_jsonl({"status": "error", "error": str(exc)}, handle)
        return 2
    finally:
        if handle is not None:
            handle.close()


def _sample_once(timeout_s: float) -> list[dict[str, str]]:
    command = [
        "nvidia-smi",
        f"--query-gpu={','.join(QUERY_FIELDS)}",
        "--format=csv,noheader,nounits",
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=timeout_s)
    rows = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        values = [part.strip() for part in line.split(",")]
        rows.append(dict(zip(OUTPUT_KEYS, values)))
    return rows


def _write_jsonl(payload: dict, handle) -> None:  # type: ignore[no-untyped-def]
    line = json.dumps(payload, ensure_ascii=False)
    if handle is None:
        print(line)
    else:
        handle.write(line + "\n")
        handle.flush()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

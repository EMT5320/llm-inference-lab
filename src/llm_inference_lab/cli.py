"""CLI entry points for LLM Inference Lab."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .bench.mock_server import main as mock_main
from .bench.runner import run_benchmark, run_registry_benchmark
from .endpoint_registry import build_endpoint_status, load_endpoint_registry
from .history.import_gemma4_md import write_gemma4_history
from .history.import_qwopus_json import write_qwopus_history
from .report.export import write_bench_markdown, write_json_report
from .report.leaderboard import discover_json_files, load_records, write_leaderboard


def repo_root() -> Path:
    """Best-effort repository root for default paths."""
    return Path(__file__).resolve().parents[2]


def main_mock(argv: list[str] | None = None) -> None:
    raise SystemExit(mock_main(argv))


def main_registry(argv: list[str] | None = None) -> None:
    raise SystemExit(_main_registry(argv))


def main_bench(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(_main_bench(argv)))


def main_import_history(argv: list[str] | None = None) -> None:
    raise SystemExit(_main_import_history(argv))


def main_leaderboard(argv: list[str] | None = None) -> None:
    raise SystemExit(_main_leaderboard(argv))


def _main_registry(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect endpoint registry readiness.")
    parser.add_argument("--registry", type=Path, default=repo_root() / "config" / "endpoints.example.json")
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args(argv)

    registry = load_endpoint_registry(args.registry)
    report = build_endpoint_status(registry)
    report["registry_path"] = str(args.registry)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(_render_registry_markdown(report), encoding="utf-8")
    return 0


async def _main_bench(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run inference benchmark against an OpenAI-compatible endpoint.")
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--endpoint", default="mock_local")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--model", default="mock-model")
    parser.add_argument("--api-key", default="local-dev-key")
    parser.add_argument("--concurrency", default="1,4,8")
    parser.add_argument("--requests-per-worker", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--warmup-requests", type=int, default=1)
    parser.add_argument("--no-stream", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, default=None)
    parser.add_argument("--details-dir", type=Path, default=repo_root() / ".run" / "bench")
    args = parser.parse_args(argv)

    concurrency_levels = [int(item.strip()) for item in args.concurrency.split(",") if item.strip()]
    if args.registry is not None:
        payload = await run_registry_benchmark(
            args.registry,
            args.endpoint,
            concurrency_levels=concurrency_levels,
            requests_per_worker=args.requests_per_worker,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.timeout,
            warmup_requests=args.warmup_requests,
            stream=not args.no_stream,
            details_dir=args.details_dir,
        )
    else:
        if not args.base_url:
            raise SystemExit("--base-url is required when --registry is not set")
        payload = await run_benchmark(
            base_url=args.base_url.rstrip("/"),
            api_key=args.api_key,
            model=args.model,
            endpoint_id=args.endpoint,
            concurrency_levels=concurrency_levels,
            requests_per_worker=args.requests_per_worker,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.timeout,
            warmup_requests=args.warmup_requests,
            stream=not args.no_stream,
            details_dir=args.details_dir,
        )

    write_json_report(payload, args.output)
    md_path = args.markdown_out or args.output.with_suffix(".md")
    write_bench_markdown(payload, md_path)
    print(json.dumps({"status": "ok", "json": str(args.output), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


def _main_import_history(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import historical benchmark artifacts.")
    parser.add_argument("--gemma4-md", type=Path, default=None)
    parser.add_argument("--qwopus-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=repo_root() / "data" / "history")
    args = parser.parse_args(argv)

    if not args.gemma4_md and not args.qwopus_json:
        parser.error("provide --gemma4-md and/or --qwopus-json")

    outputs = []
    if args.gemma4_md:
        out = args.output_dir / "gemma4_a10_20260413.json"
        payload = write_gemma4_history(args.gemma4_md, out)
        outputs.append({"type": "gemma4", "path": str(out), "rounds": len(payload.get("rounds") or [])})
    if args.qwopus_json:
        out = args.output_dir / "qwopus35_a10.json"
        payload = write_qwopus_history(args.qwopus_json, out)
        outputs.append({"type": "qwopus", "path": str(out), "rounds": len(payload.get("rounds") or [])})

    print(json.dumps({"status": "ok", "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


def _main_leaderboard(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build markdown leaderboard from history and live runs.")
    parser.add_argument("--history", type=Path, default=repo_root() / "data" / "history")
    parser.add_argument("--runs", nargs="*", type=Path, default=[repo_root() / "reports" / "eval"])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pending-model", action="append", default=["qwopus35-27b"])
    args = parser.parse_args(argv)

    paths = discover_json_files(args.history, *args.runs)
    records = load_records(paths)
    write_leaderboard(records, args.output, pending_models=args.pending_model)
    print(json.dumps({"status": "ok", "records": len(records), "output": str(args.output)}, ensure_ascii=False))
    return 0


def _render_registry_markdown(report: dict) -> str:
    lines = [
        "# Endpoint Registry Status",
        "",
        f"- schema_version: `{report['schema_version']}`",
        f"- registry: `{report.get('registry_path')}`",
        f"- endpoints: `{report['endpoint_count']}`",
        f"- enabled: `{report['enabled_count']}`",
        f"- ready/mock: `{report['ready_count']}`",
        "",
        "| endpoint | type | enabled | readiness | missing | model |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in report["endpoints"]:
        lines.append(
            "| {endpoint} | {type} | {enabled} | {status} | {missing} | {model} |".format(
                endpoint=row["endpoint_id"],
                type=row["type"],
                enabled=str(row["enabled"]).lower(),
                status=row["readiness_status"],
                missing=", ".join(row.get("missing") or []),
                model=row.get("model") or "",
            )
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main_bench(sys.argv[1:]))

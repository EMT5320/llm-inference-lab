"""Concurrent inference benchmark runner."""

from __future__ import annotations

import asyncio
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..client import post_chat_completion, wait_for_health
from ..endpoint_registry import find_endpoint, load_endpoint_registry, resolve_endpoint_connection
from ..history.schema import BENCH_RUN_SCHEMA_VERSION
from .metrics import aggregate_round


DEFAULT_PROMPT = (
    "You are being benchmarked for concise structured reasoning. "
    "Summarize the trade-offs of using tensor parallelism for inference "
    "in 6 bullet points, then end with a one-sentence recommendation."
)


async def run_benchmark(
    *,
    base_url: str,
    api_key: str,
    model: str,
    endpoint_id: str = "direct",
    concurrency_levels: list[int],
    requests_per_worker: int = 2,
    prompt: str = DEFAULT_PROMPT,
    max_tokens: int = 256,
    temperature: float = 0.2,
    timeout: float = 180.0,
    warmup_requests: int = 1,
    stream: bool = True,
    extra_body: dict[str, Any] | None = None,
    details_dir: Path | None = None,
) -> dict[str, Any]:
    """Run warmup plus concurrency sweeps and return a bench-run payload."""
    await wait_for_health(base_url, timeout=min(timeout, 60.0))

    for index in range(warmup_requests):
        warmup = await post_chat_completion(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
            max_tokens=min(max_tokens, 64),
            temperature=temperature,
            timeout=timeout,
            stream=stream,
            extra_body=extra_body,
        )
        if not warmup.get("ok"):
            raise RuntimeError(f"warmup failed: {warmup.get('error')}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    details_path = None
    if details_dir is not None:
        target = details_dir / run_id
        target.mkdir(parents=True, exist_ok=True)
        details_path = target / "details.jsonl"

    rounds: list[dict[str, Any]] = []
    for concurrency in concurrency_levels:
        round_result, raw_results = await _run_round(
            base_url=base_url,
            api_key=api_key,
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
            concurrency=concurrency,
            requests_per_worker=requests_per_worker,
            stream=stream,
            extra_body=extra_body,
        )
        rounds.append(round_result)
        if details_path is not None:
            _append_details(details_path, raw_results)

    return {
        "schema_version": BENCH_RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "source": "live",
        "evidence_class": "live/rerun",
        "endpoint_id": endpoint_id,
        "model": model,
        "base_url": base_url,
        "hardware": _default_hardware_label(endpoint_id, model),
        "gpu_telemetry": {
            "status": "pending/rerun",
            "note": "Run scripts/sample_nvidia_smi.py during the planned GPU rerun to attach live telemetry.",
        },
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "requests_per_worker": requests_per_worker,
        "concurrency_levels": concurrency_levels,
        "stream": stream,
        "rounds": rounds,
        "provenance": {
            "runner": "illab-bench",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
        },
        "details_path": _portable_details_path(details_path, details_dir),
    }


async def run_registry_benchmark(
    registry_path: Path,
    endpoint_id: str,
    *,
    concurrency_levels: list[int],
    requests_per_worker: int = 2,
    prompt: str = DEFAULT_PROMPT,
    max_tokens: int | None = None,
    temperature: float | None = None,
    timeout: float = 180.0,
    warmup_requests: int = 1,
    stream: bool = True,
    details_dir: Path | None = None,
) -> dict[str, Any]:
    """Resolve one registry endpoint and run a benchmark against it."""
    registry = load_endpoint_registry(registry_path)
    endpoint = find_endpoint(registry, endpoint_id)
    resolved = resolve_endpoint_connection(endpoint)
    if not resolved.get("base_url"):
        raise ValueError(f"endpoint {endpoint_id} is missing base URL configuration")
    return await run_benchmark(
        base_url=resolved["base_url"],
        api_key=resolved["api_key"],
        model=resolved["model"],
        endpoint_id=endpoint_id,
        concurrency_levels=concurrency_levels,
        requests_per_worker=requests_per_worker,
        prompt=prompt,
        max_tokens=int(max_tokens if max_tokens is not None else endpoint.get("max_tokens") or 256),
        temperature=float(temperature if temperature is not None else endpoint.get("temperature") or 0.2),
        timeout=timeout,
        warmup_requests=warmup_requests,
        stream=stream,
        extra_body=endpoint.get("extra_body"),
        details_dir=details_dir,
    )


async def _run_round(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    concurrency: int,
    requests_per_worker: int,
    stream: bool,
    extra_body: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    semaphore = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any]] = []

    async def worker(worker_index: int) -> None:
        for iteration in range(requests_per_worker):
            request_id = f"c{concurrency}-w{worker_index}-r{iteration}"
            async with semaphore:
                result = await post_chat_completion(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout,
                    stream=stream,
                    extra_body=extra_body,
                )
            result["request_id"] = request_id
            results.append(result)

    started = time.perf_counter()
    await asyncio.gather(*(worker(index) for index in range(concurrency)))
    wall_s = time.perf_counter() - started
    return aggregate_round(results, concurrency=concurrency, requests_per_worker=requests_per_worker, wall_s=wall_s), results


def _append_details(path: Path, results: list[dict[str, Any]]) -> None:
    import json

    with path.open("a", encoding="utf-8") as handle:
        for item in results:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def _default_hardware_label(endpoint_id: str, model: str) -> str:
    if endpoint_id == "mock_local" or model == "mock-model":
        return "CPU mock; no GPU telemetry"
    return "pending/rerun"


def _portable_details_path(path: Path | None, base_dir: Path | None) -> str | None:
    """Serialize detail artifacts without leaking a machine-specific absolute path."""
    if path is None or base_dir is None:
        return None
    repo_root = Path(__file__).resolve().parents[3]
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        relative_artifact = path.resolve().relative_to(base_dir.resolve())
        return (Path(base_dir.name) / relative_artifact).as_posix()


def _git_sha() -> str | None:
    try:
        output = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, text=True)
        return output.strip() or None
    except (subprocess.SubprocessError, FileNotFoundError):
        return None

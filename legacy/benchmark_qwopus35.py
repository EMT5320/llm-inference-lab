#!/usr/bin/env python3
"""Benchmark an OpenAI-compatible vLLM endpoint for latency and throughput."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import threading
import time
from typing import Any

import requests


def build_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (len(sorted_values) - 1) * p
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    weight = rank - low
    return sorted_values[low] * (1 - weight) + sorted_values[high] * weight


def build_prompt(repeat: int, prompt_text: str = "") -> str:
    if prompt_text:
        return prompt_text
    base = (
        "You are being benchmarked for concise structured reasoning. "
        "Summarize the trade-offs of using tensor parallelism for inference "
        "in 6 bullet points, then end with a one-sentence recommendation."
    )
    return " ".join([base] * repeat)


def post_chat(
    session: requests.Session,
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    request_id: str,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }
    started = time.perf_counter()
    try:
        response = session.post(url, json=payload, timeout=timeout)
        latency = time.perf_counter() - started
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        completion_tokens = int(usage.get("completion_tokens") or 0)
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        return {
            "ok": True,
            "request_id": request_id,
            "status_code": response.status_code,
            "latency_s": latency,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "tps": (completion_tokens / latency) if latency > 0 else 0.0,
            "text": data["choices"][0]["message"]["content"],
        }
    except Exception as exc:  # noqa: BLE001
        latency = time.perf_counter() - started
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        return {
            "ok": False,
            "request_id": request_id,
            "status_code": status_code,
            "latency_s": latency,
            "error": repr(exc),
        }


def wait_for_health(base_url: str, timeout: float) -> None:
    deadline = time.time() + timeout
    health_url = base_url.replace("/v1", "") + "/health"
    session = build_session()
    while time.time() < deadline:
        try:
            response = session.get(health_url, timeout=5)
            if response.ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise TimeoutError(f"health endpoint not ready within {timeout} seconds: {health_url}")


def run_round(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    concurrency: int,
    requests_per_worker: int,
) -> dict[str, Any]:
    lock = threading.Lock()
    results: list[dict[str, Any]] = []

    def worker(worker_index: int) -> None:
        session = build_session()
        for iteration in range(requests_per_worker):
            request_id = f"c{concurrency}-w{worker_index}-r{iteration}"
            result = post_chat(
                session=session,
                base_url=base_url,
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                request_id=request_id,
            )
            with lock:
                results.append(result)

    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker, idx) for idx in range(concurrency)]
        for future in futures:
            future.result()
    wall_s = time.perf_counter() - started

    successes = [item for item in results if item["ok"]]
    failures = [item for item in results if not item["ok"]]
    latencies = sorted(item["latency_s"] for item in successes)
    total_completion_tokens = sum(item.get("completion_tokens", 0) for item in successes)
    total_prompt_tokens = sum(item.get("prompt_tokens", 0) for item in successes)
    total_requests = len(results)
    success_count = len(successes)
    failure_count = len(failures)

    return {
        "concurrency": concurrency,
        "requests_per_worker": requests_per_worker,
        "total_requests": total_requests,
        "success_count": success_count,
        "failure_count": failure_count,
        "success_rate": (success_count / total_requests) if total_requests else 0.0,
        "wall_s": wall_s,
        "qps": (success_count / wall_s) if wall_s > 0 else 0.0,
        "aggregate_tps": (total_completion_tokens / wall_s) if wall_s > 0 else 0.0,
        "avg_request_tps": statistics.mean(item["tps"] for item in successes) if successes else 0.0,
        "avg_latency_s": statistics.mean(latencies) if latencies else 0.0,
        "p50_latency_s": percentile(latencies, 0.50),
        "p95_latency_s": percentile(latencies, 0.95),
        "max_latency_s": max(latencies) if latencies else 0.0,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "failures": failures[:5],
    }


def format_round(round_result: dict[str, Any]) -> str:
    return (
        f"concurrency={round_result['concurrency']:>2d} | "
        f"success={round_result['success_count']}/{round_result['total_requests']} "
        f"({round_result['success_rate'] * 100:5.1f}%) | "
        f"qps={round_result['qps']:6.2f} | "
        f"agg_tps={round_result['aggregate_tps']:7.2f} | "
        f"avg_tps={round_result['avg_request_tps']:6.2f} | "
        f"p50={round_result['p50_latency_s']:6.2f}s | "
        f"p95={round_result['p95_latency_s']:6.2f}s"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the Qwopus35 vLLM service.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8089/v1")
    parser.add_argument("--model", default="qwopus35")
    parser.add_argument("--prompt-text", default="")
    parser.add_argument("--prompt-repeat", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--health-timeout", type=float, default=300.0)
    parser.add_argument("--warmup-requests", type=int, default=1)
    parser.add_argument("--requests-per-worker", type=int, default=2)
    parser.add_argument("--concurrency", default="1,2,4,8,12,16,20")
    parser.add_argument("--output-json", default="")
    args = parser.parse_args()

    wait_for_health(args.base_url, args.health_timeout)

    prompt = build_prompt(args.prompt_repeat, args.prompt_text)
    warmup_session = build_session()
    for index in range(args.warmup_requests):
        warmup_result = post_chat(
            session=warmup_session,
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            max_tokens=min(args.max_tokens, 64),
            temperature=args.temperature,
            timeout=args.timeout,
            request_id=f"warmup-{index}",
        )
        if not warmup_result["ok"]:
            raise RuntimeError(f"warmup failed: {warmup_result['error']}")
        print(
            f"warmup={index + 1}/{args.warmup_requests} "
            f"latency={warmup_result['latency_s']:.2f}s "
            f"tps={warmup_result['tps']:.2f}",
            flush=True,
        )

    rounds = []
    for raw in args.concurrency.split(","):
        concurrency = int(raw.strip())
        round_result = run_round(
            base_url=args.base_url,
            model=args.model,
            prompt=prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
            timeout=args.timeout,
            concurrency=concurrency,
            requests_per_worker=args.requests_per_worker,
        )
        rounds.append(round_result)
        print(format_round(round_result), flush=True)

    threshold = None
    for round_result in rounds:
        if round_result["success_rate"] < 1.0:
            threshold = round_result["concurrency"]
            break

    summary = {
        "base_url": args.base_url,
        "model": args.model,
        "prompt_repeat": args.prompt_repeat,
        "prompt_text": args.prompt_text,
        "max_tokens": args.max_tokens,
        "temperature": args.temperature,
        "requests_per_worker": args.requests_per_worker,
        "concurrency_levels": [int(item.strip()) for item in args.concurrency.split(",") if item.strip()],
        "threshold_concurrency_with_failure": threshold,
        "rounds": rounds,
    }

    if args.output_json:
        with open(args.output_json, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)

    print("summary_json=" + json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

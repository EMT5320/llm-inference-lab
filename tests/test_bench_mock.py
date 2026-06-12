"""Integration tests with mock server."""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path

import httpx
import uvicorn

from llm_inference_lab.bench.mock_server import create_app
from llm_inference_lab.bench.runner import run_benchmark


def test_bench_against_mock_server(tmp_path: Path) -> None:
    host = "127.0.0.1"
    port = 18081
    config = uvicorn.Config(create_app(token_delay_ms=1.0, startup_delay_ms=5.0), host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            response = httpx.get(f"http://{host}:{port}/health", timeout=1.0)
            if response.is_success:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        raise RuntimeError("mock server did not start")

    payload = asyncio.run(
        run_benchmark(
            base_url=f"http://{host}:{port}/v1",
            api_key="local-dev-key",
            model="mock-model",
            endpoint_id="mock_local",
            concurrency_levels=[1, 2],
            requests_per_worker=2,
            max_tokens=32,
            timeout=30.0,
            warmup_requests=1,
            stream=True,
            details_dir=tmp_path,
        )
    )
    assert payload["schema_version"] == "bench-run-v0.1"
    assert len(payload["rounds"]) == 2
    assert all(row["success_rate"] == 1.0 for row in payload["rounds"])
    assert payload["rounds"][0]["p50_ttft_ms"] is not None
    server.should_exit = True

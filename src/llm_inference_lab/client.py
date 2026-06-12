"""OpenAI-compatible HTTP client helpers."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx


def health_url(base_url: str) -> str:
    """Derive the health endpoint URL from an OpenAI base URL."""
    return base_url.replace("/v1", "").rstrip("/") + "/health"


async def wait_for_health(base_url: str, timeout: float = 30.0) -> None:
    """Poll /health until the endpoint responds or timeout."""
    deadline = time.time() + timeout
    url = health_url(base_url)
    async with httpx.AsyncClient(trust_env=False) as client:
        while time.time() < deadline:
            try:
                response = await client.get(url, timeout=5.0)
                if response.is_success:
                    return
            except httpx.HTTPError:
                pass
            await _sleep(0.5)
    raise TimeoutError(f"health endpoint not ready within {timeout} seconds: {url}")


async def post_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    stream: bool = False,
    extra_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call /chat/completions and return a normalized request result."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
    }
    if extra_body:
        payload.update(extra_body)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{base_url.rstrip('/')}/chat/completions"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
            if stream:
                return await _post_stream(client, url, headers, payload, started)
            response = await client.post(url, headers=headers, json=payload)
            latency_s = time.perf_counter() - started
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") or {}
            completion_tokens = int(usage.get("completion_tokens") or 0)
            prompt_tokens = int(usage.get("prompt_tokens") or 0)
            if completion_tokens == 0:
                text = str(data.get("choices", [{}])[0].get("message", {}).get("content") or "")
                completion_tokens = max(1, len(text.split()))
            return {
                "ok": True,
                "latency_s": latency_s,
                "ttft_s": latency_s,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "tps": (completion_tokens / latency_s) if latency_s > 0 else 0.0,
                "status_code": response.status_code,
            }
    except httpx.HTTPStatusError as exc:
        return _error_result(started, status_code=exc.response.status_code, error=str(exc))
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        return _error_result(started, status_code=None, error=str(exc))


async def _post_stream(
    client: httpx.AsyncClient,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    started: float,
) -> dict[str, Any]:
    """Stream chat completion and measure TTFT plus total latency."""
    ttft_s: float | None = None
    completion_tokens = 0
    async with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            data = json.loads(chunk)
            delta = data.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                if ttft_s is None:
                    ttft_s = time.perf_counter() - started
                completion_tokens += max(1, len(str(content).split()))
    latency_s = time.perf_counter() - started
    if ttft_s is None:
        ttft_s = latency_s
    if completion_tokens == 0:
        completion_tokens = 1
    return {
        "ok": True,
        "latency_s": latency_s,
        "ttft_s": ttft_s,
        "prompt_tokens": 0,
        "completion_tokens": completion_tokens,
        "tps": (completion_tokens / latency_s) if latency_s > 0 else 0.0,
        "status_code": 200,
    }


def _error_result(started: float, *, status_code: int | None, error: str) -> dict[str, Any]:
    latency_s = time.perf_counter() - started
    return {
        "ok": False,
        "latency_s": latency_s,
        "ttft_s": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "tps": 0.0,
        "status_code": status_code,
        "error": error[:1200],
    }


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)

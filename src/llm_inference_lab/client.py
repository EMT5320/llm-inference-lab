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
    if stream:
        payload["stream_options"] = {"include_usage": True}
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
            completion_tokens = _optional_int(usage.get("completion_tokens"))
            prompt_tokens = _optional_int(usage.get("prompt_tokens"))
            return {
                "ok": True,
                "latency_s": latency_s,
                "ttft_s": latency_s,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "tps": (completion_tokens / latency_s)
                if completion_tokens is not None and latency_s > 0
                else None,
                "token_count_source": "server_usage" if completion_tokens is not None else "unavailable",
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
    """Stream chat completion and measure TTFT plus server-reported token usage."""
    ttft_s: float | None = None
    completion_tokens: int | None = None
    prompt_tokens: int | None = None
    async with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line or not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            data = json.loads(chunk)
            usage = data.get("usage")
            if isinstance(usage, dict):
                usage_completion_tokens = _optional_int(usage.get("completion_tokens"))
                usage_prompt_tokens = _optional_int(usage.get("prompt_tokens"))
                if usage_completion_tokens is not None:
                    completion_tokens = usage_completion_tokens
                if usage_prompt_tokens is not None:
                    prompt_tokens = usage_prompt_tokens

            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            if delta.get("content") and ttft_s is None:
                ttft_s = time.perf_counter() - started

    latency_s = time.perf_counter() - started
    if ttft_s is None:
        ttft_s = latency_s
    return {
        "ok": True,
        "latency_s": latency_s,
        "ttft_s": ttft_s,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tps": (completion_tokens / latency_s)
        if completion_tokens is not None and latency_s > 0
        else None,
        "token_count_source": "server_usage" if completion_tokens is not None else "unavailable",
        "status_code": response.status_code,
    }


def _optional_int(value: Any) -> int | None:
    """Return an integer usage value without inventing a token count."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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

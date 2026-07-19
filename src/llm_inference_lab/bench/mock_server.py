"""Lightweight OpenAI-compatible mock server for CPU smoke tests."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[ChatMessage]
    max_tokens: int = Field(default=64, ge=1, le=2048)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    stream: bool = False
    stream_options: dict[str, Any] | None = None


def create_app(*, token_delay_ms: float = 8.0, startup_delay_ms: float = 20.0) -> FastAPI:
    """Create a mock OpenAI-compatible FastAPI app."""
    app = FastAPI(title="LLM Inference Lab mock endpoint")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "model": "mock-model"}

    @app.get("/v1/models")
    def models() -> dict[str, Any]:
        return {
            "object": "list",
            "data": [{"id": "mock-model", "object": "model", "created": 0, "owned_by": "mock"}],
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest) -> Any:
        if not request.messages:
            raise HTTPException(status_code=400, detail="messages must not be empty")
        text = _mock_response(request.messages[-1].content, request.max_tokens)
        if request.stream:
            include_usage = bool((request.stream_options or {}).get("include_usage"))
            return _stream_response(
                text,
                token_delay_ms=token_delay_ms,
                startup_delay_ms=startup_delay_ms,
                include_usage=include_usage,
            )
        await asyncio.sleep(startup_delay_ms / 1000.0)
        await asyncio.sleep(min(request.max_tokens, len(text.split())) * token_delay_ms / 1000.0)
        return _completion_payload(request.model or "mock-model", text)

    return app


def _mock_response(prompt: str, max_tokens: int) -> str:
    words = [
        "Mock",
        "inference",
        "lab",
        "benchmark",
        "response",
        "for",
        "latency",
        "and",
        "throughput",
        "testing.",
    ]
    repeat = max(1, min(max_tokens // 3, 40))
    body = " ".join(words * repeat)
    preview = prompt[:48].replace("\n", " ")
    return f"[mock:{preview}] {body}"


def _completion_payload(model: str, text: str) -> dict[str, Any]:
    completion_tokens = max(1, len(text.split()))
    return {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 16,
            "completion_tokens": completion_tokens,
            "total_tokens": 16 + completion_tokens,
        },
    }


def _stream_response(
    text: str,
    *,
    token_delay_ms: float,
    startup_delay_ms: float,
    include_usage: bool,
) -> Any:
    from starlette.responses import StreamingResponse

    async def event_generator():
        await asyncio.sleep(startup_delay_ms / 1000.0)
        for token in text.split():
            payload = {
                "choices": [{"index": 0, "delta": {"content": token + " "}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(token_delay_ms / 1000.0)
        if include_usage:
            completion_tokens = max(1, len(text.split()))
            usage_payload = {
                "choices": [],
                "usage": {
                    "prompt_tokens": 16,
                    "completion_tokens": completion_tokens,
                    "total_tokens": 16 + completion_tokens,
                },
            }
            yield f"data: {json.dumps(usage_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the LLM Inference Lab mock endpoint.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--token-delay-ms", type=float, default=8.0)
    parser.add_argument("--startup-delay-ms", type=float, default=20.0)
    args = parser.parse_args(argv)
    app = create_app(token_delay_ms=args.token_delay_ms, startup_delay_ms=args.startup_delay_ms)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

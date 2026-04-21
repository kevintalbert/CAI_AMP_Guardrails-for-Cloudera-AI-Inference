"""
Proxy router: intercepts chat completion requests, runs them through NeMo Guardrails,
and forwards to the configured target endpoint using the caller's Bearer token.
"""
import json
import time
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from backend.rails_manager import get_rails
from backend.settings import settings
from backend.token_context import REQUEST_ENDPOINT, REQUEST_TOKEN

router = APIRouter(prefix="/api", tags=["proxy"])


def _get_active_endpoint() -> dict:
    f = settings.endpoints_file
    if not f.exists():
        return {}
    endpoints = json.loads(f.read_text())
    return endpoints[0] if endpoints else {}


def _bearer_from_request(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return auth


def _make_chunk(content: str, model: str, finish: bool = False) -> str:
    chunk = {
        "id": "chatcmpl-" + uuid.uuid4().hex[:8],
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {} if finish else {"content": content},
                "finish_reason": "stop" if finish else None,
            }
        ],
    }
    return "data: " + json.dumps(chunk) + "\n\n"


async def _stream_response(content: str, model: str) -> AsyncIterator[str]:
    chunk_size = 20
    for i in range(0, len(content), chunk_size):
        yield _make_chunk(content[i : i + chunk_size], model)
    yield _make_chunk("", model, finish=True)
    yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    token = _bearer_from_request(request)
    endpoint = _get_active_endpoint()

    if not endpoint:
        raise HTTPException(
            status_code=503,
            detail="No target endpoint configured. Please add one via the Endpoints page.",
        )

    REQUEST_TOKEN.set(token)
    REQUEST_ENDPOINT.set(endpoint)

    rails = await get_rails()

    try:
        result = await rails.generate_async(messages=messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Guardrails error: " + str(exc)) from exc

    if isinstance(result, dict):
        content = result.get("content", "")
    else:
        content = str(result)

    model_id = endpoint.get("model_id", "guardrails-proxy")

    if stream:
        return StreamingResponse(
            _stream_response(content, model_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return JSONResponse(
        {
            "id": "chatcmpl-" + uuid.uuid4().hex[:8],
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )

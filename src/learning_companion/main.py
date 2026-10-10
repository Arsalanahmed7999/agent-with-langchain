import json
import logging
import time
import uuid
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from learning_companion.chain import ConfigError, build_history
from learning_companion.graph import build_graph, run_graph
from learning_companion.settings import get_settings

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="Learning Companion Chatbot")


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[dict] | None = ""


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[Message]
    stream: bool = False


def error_response(message: str, status: int, kind: str, code: str | None = None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {"message": message, "type": kind, "param": None, "code": code}
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return error_response(
        "Invalid request body.", 400, "invalid_request_error", "invalid_request"
    )


def text_of(content) -> str:
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if p.get("type") == "text")
    return content or ""


def chunk(completion_id: str, created: int, model: str, delta: dict, finish):
    payload = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/models")
def list_models():
    name = get_settings().gemini_model_name
    data = (
        [
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": "learning-companion",
            }
        ]
        if name
        else []
    )
    return {"object": "list", "data": data}


@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    settings = get_settings()
    last_user = next(
        (
            i
            for i in range(len(req.messages) - 1, -1, -1)
            if req.messages[i].role == "user"
        ),
        None,
    )
    if last_user is None:
        return error_response(
            "No user message found.", 400, "invalid_request_error", "no_user_message"
        )
    # Earlier user/assistant messages from this request become history; client
    # system messages never replace the application's instruction.
    history = build_history(
        [(m.role, text_of(m.content)) for m in req.messages[:last_user]]
    )
    try:
        graph = build_graph(settings)
    except ConfigError as exc:
        return error_response(str(exc), 500, "configuration_error", "missing_config")
    user_message = text_of(req.messages[last_user].content)

    def log_trace(route: str, trace: dict):
        # Route, decision, count, and node sequence only: never keys or text.
        if settings.app_env == "development":
            logger.info(
                "route=%s decision=%s revisions=%d nodes=%s",
                route,
                trace["decision"],
                trace["revisions"],
                ",".join(trace["nodes"]),
            )

    model = settings.gemini_model_name
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if not req.stream:
        route, pieces = "", []
        try:
            for kind, value in run_graph(graph, user_message, history):
                if kind == "route":
                    route = value
                elif kind == "text":
                    pieces.append(value)
                else:
                    log_trace(route, value)
        except Exception as exc:  # noqa: BLE001
            return error_response(f"Model call failed: {exc}", 502, "api_error")
        text = f"[route: {route}]" + chr(10) * 2 + "".join(pieces)
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
        }

    def events():
        yield chunk(completion_id, created, model, {"role": "assistant"}, None)
        route = ""
        try:
            for kind, value in run_graph(graph, user_message, history):
                if kind == "route":
                    route = value
                    label = f"[route: {route}]" + chr(10) * 2
                    yield chunk(completion_id, created, model, {"content": label}, None)
                elif kind == "text":
                    yield chunk(completion_id, created, model, {"content": value}, None)
                else:
                    log_trace(route, value)
        except Exception as exc:  # noqa: BLE001
            yield chunk(
                completion_id,
                created,
                model,
                {"content": f"[Model call failed: {exc}]"},
                None,
            )
        yield chunk(completion_id, created, model, {}, "stop")
        yield "data: [DONE]" + chr(10) * 2

    return StreamingResponse(events(), media_type="text/event-stream")

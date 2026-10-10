# Learning Companion Chatbot

A small FastAPI service that exposes an OpenAI-compatible chat API. Behind it, one LangChain flow (prompt → Gemini chat model → text output) answers. Open WebUI, already installed on your machine, is the chat window. See [docs/architecture.md](docs/architecture.md).

## Setup

Requires Python 3.12 and `uv`.

```
uv sync
```

## `.env`

The instructor supplies the Gemini model name and API key.

1. Copy `.env.example` to `.env`.
2. Put your real key in `GEMINI_API_KEY` and the model name in `GEMINI_MODEL_NAME`, only in `.env`.

`.env` is untracked (listed in `.gitignore`) and is never committed. The app starts without a key; a chat request then returns a configuration error saying which setting is missing.

LangChain provider package: `langchain-google-genai` (`ChatGoogleGenerativeAI`).

## Run

```
uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000
```

## Endpoints

- `GET /health` returns `{"status": "ok"}`.
- `GET /v1/models` lists the configured `GEMINI_MODEL_NAME` (empty list if blank).
- `POST /v1/chat/completions` takes `model`, `messages`, `stream`. Uses only the latest `user` message. `stream: false` returns JSON; `stream: true` returns SSE chunks ending with `data: [DONE]`.

## Open WebUI connection

Do not change Open WebUI itself. Where your existing connection expects an OpenAI-compatible base URL, enter `http://127.0.0.1:8000/v1` (matches `HOST` and `PORT`), then pick the Gemini model from the model list. Nothing else in Open WebUI is touched.

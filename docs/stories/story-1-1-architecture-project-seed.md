# Story 1.1 — Architecture, LangChain project seed, and Open WebUI connection

Status: ready for implementation

## Purpose

This is the first story of a short, beginner LangChain and LangGraph classroom course. It does two things, in this order:

1. Write `docs/architecture.md` and get the instructor to approve it.
2. After approval, seed one small Python project, the **Learning Companion Chatbot**, and connect it to the Open WebUI that participants already have.

The capstone is one small chatbot. It is not a custom frontend and not a second demonstration application.

Project path: if `docs/config.yaml` names a project path, use it. Otherwise use the repository root. Before starting, read `docs/config.yaml` (if it exists), `docs/architecture.md` (if present), the repository layout, and existing stories. Preserve existing work.

## What this story implements in plain English

After this story, a participant can:

- Start a small chatbot service on their own computer.
- Open the chat window they already use (Open WebUI) and pick the chatbot's model from its list.
- Type a message and see a reply from the Gemini model appear in that window.
- See the reply either all at once or typed out word by word.
- Keep their secret key in a private file that is never shared.

## Prerequisites

- Python 3.12 and `uv` installed.
- Open WebUI is already installed and working on the participant's machine. It is the supplied chat client only. Do not reinstall, reconfigure, modify, or build it.
- A Gemini API key and the Gemini model name, both supplied by the instructor.
- A terminal opened in the project folder.

## Work to do

### Part A — Architecture (do this first, then stop)

1. Create or update `docs/architecture.md`. If it exists, keep its content and add what is missing.
2. Record this single classroom flow:

   `Open WebUI → this local application's OpenAI-compatible chat endpoint → LangChain prompt and Gemini model → answer in Open WebUI`

3. Record that Open WebUI is already installed and working. It is the supplied chat client only. Participants must not reinstall, reconfigure, modify, or build it.
4. Record that the capstone is a small Learning Companion Chatbot, not a custom frontend or a second demo application.
5. Record these light boundaries:
   - API keys stay in an untracked `.env`.
   - Application instructions stay separate from user messages.
   - This course does not cover authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, or extensive tests.
6. Record the three endpoints (`GET /health`, `GET /v1/models`, `POST /v1/chat/completions`) and that Story 2.1 extends this seed.
7. **STOP.** Ask the instructor to approve `docs/architecture.md`. Until approval is explicit, do not create seed files, install dependencies, or scaffold code. Resume this same story at Part B only after explicit approval.

### Part B — Project seed (only after approval)

#### B1. Project files

Create a Python 3.12 and UV project with these files:

- `pyproject.toml` and `uv.lock`
- `src/learning_companion/` (the application package)
- `tests/`
- `.env.example`
- `.gitignore` (must ignore `.env`, `.venv/`, and caches)
- `README.md`

Dependencies: FastAPI, Pydantic settings, `langchain`, the Gemini LangChain provider integration (`langchain-google-genai`; record the package in the README), Uvicorn, Ruff, and a minimal test runner (pytest).

Do not add Claude, alternate-provider, database, or production configuration.

#### B2. `.env.example`

Use exactly these setting names and values:

```
APP_ENV=development
GEMINI_API_KEY=
GEMINI_MODEL_NAME=
HOST=127.0.0.1
PORT=8000
```

In the README, explain: the instructor supplies the model name; participants copy `.env.example` to `.env` and put their real key only in `.env`; `.env` is untracked and is never committed.

#### B3. Startup behavior

The application must start with no real API key. Settings load from the environment, with the key and model name allowed to be blank. If a model call is attempted while the key or model name is missing, return an honest configuration error in the OpenAI-style error shape (for example, a message saying `GEMINI_API_KEY` is not set). Do not crash at startup and do not return a fake answer.

#### B4. Endpoints

Build one minimal FastAPI app with exactly these routes:

- `GET /health`: returns a small fixed payload such as `{"status": "ok"}`. It never shows secrets.
- `GET /v1/models`: returns an OpenAI-style model list that contains the configured `GEMINI_MODEL_NAME`, so Open WebUI can select it. If the name is blank, return an empty list.
- `POST /v1/chat/completions`: accepts the normal OpenAI-compatible request shape: `model`, a list of text `messages` with roles `system`, `user`, or `assistant`, and `stream`.
  - `stream` false: return normal OpenAI-compatible JSON (`chat.completion` with one choice and the reply text).
  - `stream` true: return text-only OpenAI-compatible SSE chunks (`chat.completion.chunk`), then a stop chunk, then `data: [DONE]`.

Do not create custom Open WebUI events, a second chat route, or a custom browser UI.

#### B5. One small LangChain flow

Create one small flow: **prompt → Gemini chat model → text output**.

- The prompt has a fixed Learning Companion instruction (a system message) and the latest user message. The instruction stays separate from the user's text.
- Use this same flow behind the single chat endpoint, for both normal and streaming requests. Streaming uses the chain's streaming output; do not write a second path.
- Take only the latest `user` message. Ignore earlier history. Full prompt construction and conversation history are Story 2.1.

Keep it deliberately small. Do not add a broad test suite, tool calls, LangGraph, agents, MCP, or advanced streaming features.

#### B6. README

Short sections: what this is, setup (`uv sync`), `.env` handling, run command, the three endpoints, and the Open WebUI connection note below.

#### B7. Open WebUI connection note

Open WebUI itself must not be changed. If the participant's existing connection needs a value changed to reach this app, document only the application-side value: the base URL `http://127.0.0.1:8000/v1` (matching `HOST` and `PORT`) and selecting the Gemini model from the model list. Note that the capstone's `/v1` base URL may need to be entered where the existing connection expects an OpenAI-compatible base URL, and that nothing else in Open WebUI is touched.

## Completion checks

Run only these lightweight checks. Do not add more.

1. `uv sync` succeeds and `uv.lock` exists.
2. `uv run ruff format .` and `uv run ruff check .` pass on the changed code.
3. Start the API with no `.env` key. It starts without error.
4. `GET /health` returns the safe payload.
5. With no key set, `POST /v1/chat/completions` returns the honest configuration error.
6. Put the real key and model name in `.env`, then start the API (for example `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`).
7. `GET /v1/models` lists the configured Gemini model.
8. One normal request (`stream: false`) through the existing Open WebUI setup returns one Gemini reply.
9. One streaming request (`stream: true`) through the existing Open WebUI setup shows a Gemini reply that streams in.
10. `git status` shows `.env` untracked and ignored.

Expected classroom result: one Gemini reply visible in Open WebUI.

If a check fails, report the exact output and stop. Do not change Open WebUI to work around it.

## Handover

When the story is done, fill in this section:

- **Files created or changed** (full list).
- **Commands actually run** and what each returned.
- **Open WebUI result**: the model selected and the reply seen, for both the normal and the streaming request.
- **Deviations** from this story, if any, and why.
- **What Story 2.1 will extend**: full prompt construction and conversation history on top of this one prompt → Gemini → text flow, using the same endpoint. Nothing in this story's routes or `.env` names should need renaming.

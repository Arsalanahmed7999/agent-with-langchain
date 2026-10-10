# Story 2.1 — LangChain prompt template

Status: ready for implementation

## Purpose

Story 1.1 seeded a working chatbot with a small fixed prompt. This story makes that LangChain flow reusable and easy to understand: a clear chat prompt with two separate parts, the application's own instruction and the participant's current message.

Nothing the participant sees in Open WebUI changes except that the flow behind it is now explicit and inspectable.

Before starting, read `docs/config.yaml` (if it exists), `docs/architecture.md`, Story 1.1, `.env.example` (if present), the existing code in `src/learning_companion/` (especially `chain.py` and the chat route in `main.py`). Preserve existing work, routes, settings, and the working Open WebUI connection.

## What this story implements in plain English

After this story, a participant using the chatbot gets:

- The same chat window, the same model in the list, and the same replies, either all at once or typed out word by word.
- A tutor that always follows the course's own instruction, however the question is worded.
- A reply based on the latest message they typed.
- A request that contains its own "system" text is treated as ordinary user words. It cannot replace the tutor's built-in instruction.
- A small developer-only log that shows what went into the prompt, without secrets.

## Prerequisites

- Story 1.1 is done: the app starts, `GET /health` works, and Open WebUI shows a Gemini reply for both normal and streaming requests.
- Python 3.12 and `uv` installed.
- A Gemini API key and model name in `.env` (supplied by the instructor).
- Open WebUI already connected to `http://127.0.0.1:8000/v1`. Do not reinstall, reconfigure, modify, or build it.

## Work to do

Keep the routes, response shapes, and settings exactly as they are: `GET /health`, `GET /v1/models`, `POST /v1/chat/completions`, normal JSON and SSE behavior, and `GEMINI_API_KEY` / `GEMINI_MODEL_NAME`. The model is Gemini through `langchain-google-genai`.

1. **Build a two-part chat prompt** in `src/learning_companion/chain.py`.
   - Use LangChain's `ChatPromptTemplate` with a `SystemMessage` (or `("system", ...)`) for the stable Learning Companion instruction owned by the application, and a `{question}` human message placeholder for the current user message.
   - Keep the instruction as one named constant. Do not concatenate a large ad-hoc string.
2. **Choose the user message** in `src/learning_companion/main.py`.
   - Use only the latest supported `user` message from the request.
   - Ignore request-supplied `system` and `assistant` messages for prompt construction. A `system` message from the client is user-provided content and must not replace the application's instruction.
   - Do not add history handling. Story 2.2 does that.
3. **Keep one chain for both paths.** `prompt → Gemini model → text output` serves `stream: false` (`invoke`) and `stream: true` (`stream`). No second chat path.
4. **Add a compact development-only inspection helper.**
   - A small function (for example `describe_messages(...)` in `chain.py`) that formats the prompt and returns message roles and counts only, for example `roles=[system, user] count=2`.
   - Log it only when `APP_ENV=development`.
   - Never log API keys, the full system instruction, or full user text.
5. **Update `docs/architecture.md`.** Add a short "Message flow" section: client request → latest user message selected → prompt (system instruction + user message) → Gemini → text output → OpenAI-compatible response. State the deliberate no-persistence boundary: no history, database, or memory yet.

Do not add: a command-line-only chatbot, a second chat path, conversation history, a database, persistent memory, RAG, tools, MCP, LangGraph, a new frontend, or custom message formats or Open WebUI plugins.

## Files expected to change

- `src/learning_companion/chain.py`
- `src/learning_companion/main.py` (only if needed to select the latest user message or call the helper)
- `docs/architecture.md`

No new dependencies. `pyproject.toml` and `uv.lock` stay unchanged.

## Completion checks

Run only these.

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the app: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`. It starts without error.
3. In the existing Open WebUI chat, select the Gemini model and ask one ordinary question (for example "What is a prompt template?"). Open WebUI renders a Gemini reply, streamed in as before.
4. Check the development log (or call the helper once) and confirm it shows the system message first and the latest user message second, with roles and counts only and no secrets.
5. `git status` shows `.env` still untracked and ignored.

Expected Open WebUI result: the same answer experience as Story 1.1, with the answer following the Learning Companion instruction.

If a check fails, report the exact output and stop. Do not change Open WebUI to work around it. Do not add an evaluation harness, broad test suite, production memory, or security programme.

## Handover

When the story is done, fill in this section:

- **Files created or changed** (full list).
- **Commands actually run** and what each returned.
- **Open WebUI result**: the model selected and the reply seen.
- **Prompt order confirmed**: system instruction first, latest user message second, from the dev log or helper output.
- **Deviations** from this story, if any, and why.
- **What Story 2.2 will extend**: conversation history, added to this same prompt (a placeholder for earlier messages between the system instruction and the latest message), on the same endpoint. No route or `.env` name should need renaming.

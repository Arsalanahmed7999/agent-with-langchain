# Story 3.2 — Visible Python routing between the two chains

Status: implemented

## Purpose

Story 3.1 created a study-helper chain, but only a terminal command can reach it. This story makes both chains reachable from the same Open WebUI chat, through one plain Python `if/else` that participants can read.

This is deterministic application routing. It is not LLM classification, not a LangGraph workflow, and not an autonomous agent. Session 4 will later replace this `if/else` with an explicit LangGraph route.

## What this story implements in plain English

After this story, a participant using the chatbot can:

- Send an ordinary message, such as "Hello!", and get the same general-chat answer as before.
- Start a message with `/study`, such as `/study Explain what an API is`, and get a study-helper answer: a plain explanation and one next step.
- See which path was taken: each answer starts with a short label, `[route: general]` or `[route: study]`.
- Keep one Open WebUI conversation. Both paths use the same endpoint, the same model, and the same earlier messages from the chat.
- Read the whole rule in a few lines of Python: if the latest message begins with `/study`, use the study helper; otherwise use general chat.

## Prerequisites

- Stories 1.1 to 3.1 are done and working.
- `.env` has `GEMINI_API_KEY` and `GEMINI_MODEL_NAME`. Both chains use this same configured Gemini model. No new setting is added.
- Open WebUI is connected to `http://127.0.0.1:8000/v1`. Do not change Open WebUI.

## Work to do

Routes, `.env` names, request and response shapes, the normal JSON and SSE formats, and Story 2.2 history handling stay the same. `build_chain()`, `build_study_chain()`, and both prompts stay untouched.

1. **Add the routing rule** in `src/learning_companion/chain.py`:
   - `STUDY_MARKER = "/study"`.
   - `select_route(question) -> tuple[str, str]` returns `("study", question_without_marker)` when the question, after leading whitespace is ignored, starts with `/study` followed by whitespace or the end of the text. Otherwise it returns `("general", question)`. Only the leading marker is removed. The rest of the text is unchanged. Text like `/studying` is not a marker.
   - Keep it a plain `if/else`. No model call, no scoring, no classification.
2. **Use the rule in the chat route** in `src/learning_companion/main.py`:
   - Find the latest `user` message and build history exactly as in Story 2.2.
   - Call `select_route()` on the latest user text. Build `build_study_chain(settings)` for `study` and `build_chain(settings)` for `general`.
   - If the route is `study` and nothing remains after the marker, return a normal assistant answer (no model call): `[route: study]` followed by `Add a question after /study, for example: /study Explain what an API is.` Keep the usual JSON or SSE shape.
3. **Add the route label to the answer text.** The answer text starts with `[route: general]` or `[route: study]`, a blank line, then the model text. Normal responses prepend it to `message.content`. Streaming responses send it as the first content chunk after the role chunk, then the model chunks, the stop chunk, and `data: [DONE]`. No custom response fields.
4. **Log the route in development.** With `APP_ENV=development`, extend the existing log with the route, for example `route=study roles=['system', 'human'] count=2`. Never log keys, instructions, or message text. `describe_messages()` may take the prompt to use so the log shows the selected prompt.
5. **Update `docs/architecture.md`** with the `/study` rule, the selected-chain path, and the boundary: this is deterministic application routing, not LLM classification, LangGraph, or multi-agent orchestration. Update the "Used by" cells in the chain table and the message flow.
6. **Update `docs/manual-tests.md`** with a Story 3.2 section.

Do not add LLM routing, more specialists, review steps, loops, tools, MCP, LangGraph, retrieval, a database, a new endpoint, a new UI, an Open WebUI plugin, broad tests, or production controls.

Files changed: `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`. No dependency changes. `study_dev.py` is unchanged.

## Completion checks

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the API: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`.
3. In a new Open WebUI chat, send "Hello!".
4. In the same chat, send `/study Explain what an API is`.
5. Read the API log for both messages.

Expected Open WebUI results:

- Message 3: the answer starts with `[route: general]` and is an ordinary chat reply.
- Message 4: the answer starts with `[route: study]`, then a plain explanation of an API, and ends with exactly one next step. It does not claim to have searched or looked anything up.
- Both answers arrive through the same endpoint, `POST /v1/chat/completions`, in the same conversation. Open WebUI uses streaming, so this also covers the SSE path.

Expected log: `route=general ...` for message 3 and `route=study ...` for message 4.

If a check fails, report the exact output and stop.

## Handover

- **Files created or changed**: `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `docs/architecture.md`. `docs/manual-tests.md` still needs its Story 3.2 section.
- **Commands actually run**:
  - `uv run ruff format .` and `uv run ruff check .`: passed.
  - Local server on port 8012 with `APP_ENV=development` and four requests: "Hello!" gave `[route: general]` plus a normal reply; `/study Explain what an API is` gave `[route: study]`, a plain explanation and one next step; bare `/study` gave the `[route: study]` usage hint; a streaming `/study` request sent the role chunk, then the `[route: study]` label chunk.
- **Route log**: `route=general roles=['system', 'human'] count=2` and `route=study roles=['system', 'human'] count=2`.
- **Open WebUI result**: not yet checked by the participant. Run completion checks 3 to 5 in the real chat.
- **Deviations**: the missing-configuration error now appears after the "no user message" check, because the route needs the user message first. `UV_LINK_MODE=copy` was needed for `uv`.
- **What Story 4.1 will extend**: it replaces this `if/else` with an explicit LangGraph route that makes the same choice between the two chains. The `/study` rule and the route label stay as the visible behaviour.

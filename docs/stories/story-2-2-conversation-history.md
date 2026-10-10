# Story 2.2 — Conversation history from Open WebUI

Status: implemented

## Purpose

Story 2.1 gave the chatbot a clear two-part prompt. This story lets a follow-up question use earlier messages from the same chat, so the tutor can answer "what did I just say?" style questions.

Open WebUI already sends the messages of the active chat with every request. The app only reads them. It saves nothing.

## What this story implements in plain English

After this story, a participant using the chatbot gets:

- Follow-up questions that make sense: the tutor sees the recent earlier messages of the same chat.
- Earlier questions and answers are used in the order they were written.
- Only the 10 most recent earlier messages are used, so long chats stay small.
- The tutor's own built-in instruction still comes first. Text a client labels "system" cannot replace it.
- Nothing is remembered once a reply is finished. A new chat starts fresh.

## Prerequisites

- Story 2.1 is done and working.
- `.env` has `GEMINI_API_KEY` and `GEMINI_MODEL_NAME`.
- Open WebUI is connected to `http://127.0.0.1:8000/v1`. Do not change Open WebUI.

## Work to do

Routes, `.env` names, request and response shapes, and the normal JSON and SSE behavior stay the same. The same prompt → Gemini model → text-output chain serves both paths.

1. **Add a history placeholder to the prompt** in `src/learning_companion/chain.py`: system instruction, then `MessagesPlaceholder("history", optional=True)`, then the latest user message.
2. **Add `build_history()` and `MAX_HISTORY_MESSAGES = 10`** in `chain.py`. It keeps only `user` and `assistant` messages that have text, converts them to `HumanMessage` / `AIMessage` in original order, and returns the last 10. Any `system` role or empty content is dropped.
3. **Use the history in the chat route** in `src/learning_companion/main.py`. Find the latest `user` message. Messages before it become the history. Messages after it are ignored.
4. **Keep the development log compact.** `describe_messages()` logs roles and count only, for example `roles=['system', 'human', 'ai', 'human'] count=4`. Never log keys, the system instruction, or message bodies.
5. **Update `docs/architecture.md`** with the history flow, the 10-message limit, and the no-persistence boundary.
6. **Update `docs/manual-tests.md`** with a Story 2.2 section.

Do not add a database, persistent memory, RAG, tools, MCP, routing, LangGraph, a new endpoint, or a new UI.

Files changed: `src/learning_companion/chain.py`, `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`. No dependency changes.

## Completion checks

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the API: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`.
3. In a new Open WebUI chat, send: "My favourite colour is teal. Please remember it." Then send: "What is my favourite colour?"
4. The API log for the second message shows `roles=['system', 'human', 'ai', 'human'] count=4`.

Expected two-turn Open WebUI result: the second answer says teal. A new chat asking the same question does not know the colour.

If a check fails, report the exact output and stop.

## Handover

- **Files created or changed**: the four files above.
- **Commands actually run**:
  - `uv run ruff format .` and `uv run ruff check .`: passed.
  - Local server on port 8011 with a two-turn request body (user, assistant, user): reply "Your favourite colour is teal!", log `roles=['system', 'human', 'ai', 'human'] count=4`.
- **Open WebUI result**: not yet checked by the participant. Run completion checks 3–4 in the real chat.
- **Deviations**: none. The `uv` commands needed `UV_LINK_MODE=copy` because of a OneDrive hardlink error.
- **What Story 3.1 will extend**: it builds on this same endpoint and prompt. The history here is request-only and stays that way until a later story says otherwise.

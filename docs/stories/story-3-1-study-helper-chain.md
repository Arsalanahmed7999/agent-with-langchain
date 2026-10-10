# Story 3.1 — Study-helper LangChain chain

Status: implemented

## Purpose

The Learning Companion has one chain for greetings and ordinary conversation. This story adds a second, separately named chain that explains beginner technical concepts in plain language and ends with one small next learning step.

This story only creates the study-helper capability. Nothing chooses between the two chains yet. Story 3.2 does that.

## What this story implements in plain English

After this story, the implementer can:

- Run the study helper from the terminal with a beginner question, such as "What is a prompt template?".
- Get a short plain-language explanation, a small example when it helps, and exactly one suggested next step.
- Rely on the study helper not claiming to research, browse, look up course data, or guarantee its answer is correct.
- Keep chatting in Open WebUI exactly as before. The general chat answers the same way it did after Story 2.2.

Open WebUI users do not see the study helper yet. It is a second behaviour waiting for the routing rule in Story 3.2.

## Prerequisites

- Stories 1.1 to 2.2 are done and working.
- `.env` has `GEMINI_API_KEY` and `GEMINI_MODEL_NAME`. This repository uses the Gemini model through `langchain-google-genai`. Both chains use this same configured model. No new provider, key, or setting is added.
- Open WebUI is connected to `http://127.0.0.1:8000/v1`. Do not change Open WebUI.

## Work to do

Routes, `.env` names, request and response shapes, JSON and SSE behaviour, history handling, and `src/learning_companion/main.py` stay unchanged. The existing `PROMPT`, `SYSTEM_INSTRUCTION`, and `build_chain()` stay untouched.

1. **Add the study-helper instruction and prompt** in `src/learning_companion/chain.py`:
   - `STUDY_SYSTEM_INSTRUCTION`: a fixed application instruction. It asks for a concise plain-language explanation for a beginner, a small example where useful, and exactly one suggested next learning step. It says the helper does not research, browse, retrieve course data, or guarantee correctness.
   - `STUDY_PROMPT`: system instruction, then `MessagesPlaceholder("history", optional=True)`, then `{question}` as the human message. User text stays in the human message and never goes into the instruction.
2. **Add `build_study_chain(settings)`** in the same file. It raises the same `ConfigError` messages for a missing key or model name, then returns `STUDY_PROMPT | model | StrOutputParser()` using the same configured model. Reuse `build_history()` for history. Do not edit `build_chain()`.
3. **Add a development-only entry point** `src/learning_companion/study_dev.py`. Run it with `uv run python -m learning_companion.study_dev "your question"`. It loads settings, builds the study chain, invokes it once with the question and no history, and prints the text. On `ConfigError` it prints the message and exits with code 1. It is not imported by the app and adds no route.
4. **Update `docs/architecture.md`** with the two chain behaviours and their responsibilities (see below).

Architecture text to add:

- **General-chat chain** (`build_chain`): greetings and ordinary conversation. This is what `POST /v1/chat/completions` uses.
- **Study-helper chain** (`build_study_chain`): beginner technical explanations with one next step. Available in code and through `study_dev.py` only. This story creates the capability. Selecting between chains is Story 3.2.
- Both chains use the same configured model, the same request-only history, the same endpoint, and the same Open WebUI chat.

Do not add routing, LLM-based classification, more specialists, loops, review steps, tools, MCP, LangGraph, retrieval, a database, a second application, endpoint, model provider, or UI. Do not add tests or production controls.

Files changed: `src/learning_companion/chain.py`, `src/learning_companion/study_dev.py` (new), `docs/architecture.md`. No dependency changes.

## Completion checks

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the API: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`. In a new Open WebUI chat, send "Hello!". The reply is a normal general-chat reply with no study-helper structure and no suggested next step.
3. Stop the API (or use a second terminal). Run: `uv run python -m learning_companion.study_dev "What is a prompt template?"`.

Expected result of check 3: a short plain explanation, a small example if useful, and exactly one next step. It does not claim to have searched or looked anything up.

If a check fails, report the exact output and stop.

## Handover

- **Files created or changed**: `src/learning_companion/chain.py`, `src/learning_companion/study_dev.py` (new), `docs/architecture.md`. `docs/manual-tests.md` also has a Story 3.1 section. No dependency changes.
- **Commands actually run**:
  - `uv run ruff format .` and `uv run ruff check .`: passed.
  - `uv run python -m learning_companion.study_dev "What is a prompt template?"`: exit 0. The answer had a plain explanation, a small example, and one next step. It did not claim to research or browse.
  - `uv run python -m learning_companion.study_dev` with no question: printed the usage line, exit 1.
- **Open WebUI result**: not yet checked by the participant. Send "Hello!" in a new chat and confirm it matches earlier general-chat behaviour. `build_chain()` and `main.py` were not changed.
- **Deviations**: none. The `uv` commands needed `UV_LINK_MODE=copy` because of a OneDrive hardlink error. The story text says Grok in the handout, but this repo uses Gemini, so Gemini is used.
- **What Story 3.2 will extend**: it adds the visible `/study` route rule in the chat endpoint. Messages starting with `/study` will use the study-helper chain. Everything else keeps using the general-chat chain. `study_dev.py` stays as a development aid.

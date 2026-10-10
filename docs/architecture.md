# Architecture — Learning Companion Chatbot

## Purpose

A short, beginner LangChain and LangGraph classroom course. The capstone is one small **Learning Companion Chatbot**. It is not a custom frontend and not a second demonstration application.

## Classroom flow

```
Open WebUI → this local application's OpenAI-compatible chat endpoint → LangChain prompt and Gemini model → answer in Open WebUI
```

## Components

- **Open WebUI**: already installed and working on each participant's machine. It is the supplied chat client only. Participants must not reinstall, reconfigure, modify, or build it.
- **Local application**: one small FastAPI service (Python 3.12, managed with `uv`) that exposes an OpenAI-compatible API.
- **LangChain flow**: prompt (fixed Learning Companion instruction as a system message, plus the latest user message) → Gemini chat model → text output. The same flow serves normal and streaming requests.
- **Gemini model**: reached through the `langchain-google-genai` integration. The instructor supplies the model name and API key.

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /health` | Fixed safe payload, no secrets. |
| `GET /v1/models` | OpenAI-style model list containing the configured `GEMINI_MODEL_NAME` (empty if blank). |
| `POST /v1/chat/completions` | OpenAI-compatible chat. `stream: false` returns `chat.completion` JSON. `stream: true` returns text-only SSE `chat.completion.chunk` events, a stop chunk, then `data: [DONE]`. |

Story 2.1 extends this seed (full prompt construction and conversation history) on the same endpoint. No route or `.env` name should need renaming.

## Message flow

1. Open WebUI sends an OpenAI-style request to `POST /v1/chat/completions`.
2. The app picks the latest `user` message. Earlier `user` and `assistant` messages in the same request become history, limited to the most recent 10 (`MAX_HISTORY_MESSAGES` in `chain.py`). Client `system` messages and empty content are ignored.
3. The LangChain prompt is built in order: the app's fixed Learning Companion system instruction, the history (a `MessagesPlaceholder`), then the latest user message.
4. The prompt goes to Gemini, then the text output parser. The same chain serves normal and streaming replies.
5. The text is returned as OpenAI-compatible JSON or SSE chunks.

In development (`APP_ENV=development`) the app logs message roles and counts only, never keys or message text.

Deliberate boundary: no persistence. History exists only inside the current request, as sent by Open WebUI. The app saves nothing after a request ends: no database, cross-session memory, or stored history.

## Chain behaviours

| Chain | Builder | Responsibility | Used by |
| --- | --- | --- | --- |
| General chat | `build_chain` | Greetings and ordinary conversation. | `POST /v1/chat/completions` when the latest user message does not begin with `/study`. |
| Study helper | `build_study_chain` | Beginner technical explanations: concise plain-language explanation, a small example where useful, one next learning step. Does not research, browse, retrieve course data, or guarantee correctness. | `POST /v1/chat/completions` when the latest user message begins with `/study`; also `python -m learning_companion.study_dev "question"`. |

Both chains use the same configured Gemini model, the same request-only history, the same endpoint, and the same Open WebUI chat.

### The `/study` rule and the LangGraph workflow (Stories 3.2 to 4.2)

The `/study` rule is unchanged: if the latest user message begins with `/study` (followed by whitespace or the end), the study-helper chain writes the draft and only that leading marker is removed; otherwise the general-chat chain writes it. The choice runs inside one small LangGraph workflow in `src/learning_companion/graph.py`. `select_route()` in `chain.py` is still the rule itself.

```
START → router ──general──→ general-chat ─┐
                └──study───→ study-helper ─┤
                                           ↓
                              ┌──────→ reviewer ──approve──→ END
                              │           │
                              │        improve (only if revision_count = 0)
                              │           ↓
                              └────── improver
```

State (`RouteState`):

| Field | Meaning |
| --- | --- |
| `user_message` | Latest user message; the router removes the `/study` marker. |
| `messages` | Earlier messages already converted by `build_history()` (newest 10). |
| `route` | `general` or `study`, written by the router. |
| `draft_answer` | Answer written by an answer node (or the improver), not yet reviewed. |
| `review_decision` | `approve` or `improve`, written by the reviewer. |
| `review_reason` | One short sentence from the reviewer. |
| `revision_count` | How many times the improver has run. Maximum 1. |
| `final_answer` | The answer sent to Open WebUI. |

Nodes (a node is a focused piece of work, not automatically an agent):

- **router**: ordinary Python, no model call. Runs `select_route()` and writes `route`. Not an agent.
- **general-chat**: calls the existing general-chat chain and writes `draft_answer`.
- **study-helper**: calls the existing study-helper chain and writes `draft_answer`. A bare `/study` writes a short usage hint and skips review.
- **reviewer**: a small LLM-powered specialist. Checks the draft against a short fixed classroom rule and returns a structured `approve` or `improve` plus one short reason. When `revision_count` is 1 it makes no model call and accepts the draft as final.
- **improver**: a small LLM-powered specialist. Rewrites the draft once using the reviewer reason, then increments `revision_count`. No tools, browsing, retrieval, planning, or routing.

Edge rules: `START → router`; a conditional edge from `router` to `general` or `study`; `general → reviewer` and `study → reviewer`; a conditional edge from `reviewer` to `END` on `approve`, or to `improver` on `improve` only while `revision_count` is 0; `improver → reviewer`. The only cycle is reviewer → improver → reviewer, and it runs at most once: one improvement maximum.

The endpoint builds the graph, runs it, and passes `final_answer` through the same JSON or SSE adapter. The draft is never shown. Because the reviewer may change the draft, streaming sends the reviewed answer after the label as one content chunk. The answer text starts with `[route: general]` or `[route: study]`. In development the log shows `route=<name> decision=<approve|improve> revisions=<0|1> nodes=<sequence>` only, never keys, drafts, or message text.

Scope boundary: no planner, tools, MCP, retrieval, web search, human approval, retries, extra loops, or persistence. The router is ordinary Python; MCP could be a future node and is not part of this course.

## Light boundaries

- API keys stay in an untracked `.env`.
- Application instructions stay separate from user messages.
- Missing key or model name: the app still starts; a model call returns an honest OpenAI-style configuration error.
- Out of scope for this course: authentication, authorization, security hardening, databases, persistent memory, RAG, production deployment, extensive tests.

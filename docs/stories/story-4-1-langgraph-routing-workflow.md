# Story 4.1 — LangGraph routing workflow

Status: implemented

## Purpose

Story 3.2 chooses between the two chains with a plain Python `if/else` inside the chat route. This story moves that same choice into one small LangGraph workflow, so the route, the state, the nodes, and the edges are all visible in code.

Behaviour for participants does not change. `/study` still selects the study helper and everything else still goes to general chat. Only the inside of the application changes.

## What this story implements in plain English

After a question enters the chatbot:

- The question and the earlier chat messages are put into one small record, called the **state**, that travels through the workflow.
- A first step, the **router**, looks at the question. If it begins with `/study` it writes `study` into the state. Otherwise it writes `general`.
- The workflow then follows one of two paths: the general-chat step or the study-helper step. Each one calls the chain that already exists and writes its answer into the state.
- The answer is read from the state and sent back to Open WebUI through the same endpoint, in the same JSON or streaming format, with the same `[route: ...]` label.
- A short development log shows the route and the steps that ran, for example `route=study nodes=router,study`.

## Terms used in this story

- **State**: the shared record that moves through the workflow. Each step reads it and writes to it.
- **Node**: one focused piece of work. A node is not automatically an agent.
- **Edge**: an arrow saying which node runs next. A **conditional edge** picks the next node from a value in the state.
- The **router node** is ordinary application logic. It is not an agent and makes no model call.
- The **general-chat node** and the **study-helper node** are small specialist behaviours. Each calls one existing LangChain chain.
- MCP tools could be placed inside a future node. MCP is not implemented in this course story.

## The state fields

`RouteState` is a `TypedDict` with four fields:

| Field | Meaning in plain English |
| --- | --- |
| `user_message` | The latest user message, as sent. |
| `messages` | The earlier conversation messages already converted by `build_history()` (Story 2.2 rules, newest 10). |
| `route` | `general` or `study`. Empty until the router writes it. |
| `answer` | The final answer text. Empty until an answer node writes it. |

## Prerequisites

- Stories 1.1 to 3.2 are done and working.
- `.env` has `GEMINI_API_KEY` and `GEMINI_MODEL_NAME`. Both chains keep using this configured Gemini model. No new setting is added.
- Open WebUI is connected to `http://127.0.0.1:8000/v1`. Do not change Open WebUI.

## Work to do

Routes, `.env` names, request and response shapes, normal JSON replies, SSE streaming, history conversion, the `[route: ...]` label, and the bare `/study` usage hint stay exactly as they are. `build_chain()`, `build_study_chain()`, both prompts, and `select_route()` stay as they are. Do not create a second application or chat route.

1. **Add the dependency.** Add `langgraph` to `pyproject.toml` dependencies and run `uv sync`. This is the only dependency change.
2. **Create `src/learning_companion/graph.py`** with:
   - `RouteState`, the `TypedDict` above.
   - `router_node(state)`: calls the existing `select_route()` on `user_message`, writes `route`, and writes the question with the marker removed back to `user_message`. No model call.
   - `general_node(state)` and `study_node(state)`: each takes the chain it needs, calls it with `{"history": messages, "question": user_message}`, and writes `answer`.
   - `build_graph(settings)`: builds the two chains, adds the three nodes, and wires the edges below. Build the chains only for the route that runs, so a missing key still gives the existing configuration error through the existing handler.
3. **Wire the explicit edges:**
   - `START → router`
   - conditional edge from `router` to `general` or `study`, chosen by `state["route"]`
   - `general → END`
   - `study → END`

   No reviewer, improver, loop, or retry. Story 4.2 adds the bounded review path.
4. **Use the graph in `src/learning_companion/main.py`.** Replace the direct `select_route()` and chain choice with one graph run. The bare `/study` usage hint still returns without a model call. Keep the response adapter: normal replies return `[route: <route>]`, a blank line, then the answer. Streaming sends the role chunk, the label chunk, text chunks, the stop chunk, then `data: [DONE]`. For streaming, prefer `graph.stream(..., stream_mode="messages")` to forward text from the answer nodes. If that does not stream cleanly, send the final answer as a single content chunk. State which one was used in the Handover.
5. **Add a compact development trace.** With `APP_ENV=development`, log `route=<route> nodes=<router,general|router,study>`. Roles and counts may stay in the same line. Never log keys, instruction text, or message text.
6. **Update `docs/architecture.md`** with the graph diagram, the state fields, node responsibilities, edge rules, and what stays out of scope. Replace the Story 3.2 wording that describes the route as a plain `if/else` in the endpoint.
7. **Update `docs/manual-tests.md`** with a Story 4.1 section.

Graph diagram to add to the architecture file:

```
START → router ──general──→ general-chat ──→ END
                └──study───→ study-helper ──→ END
```

Do not add databases, persistence, RAG, web search, tool execution, MCP, human approval, review steps, loops, additional agents, broad tests, security programmes, observability platforms, or deployment work.

Files changed: `pyproject.toml`, `uv.lock`, `src/learning_companion/graph.py` (new), `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`.

## Completion checks

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the API with `APP_ENV=development`: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`.
3. In a new Open WebUI chat, send "Hello!".
4. In the same chat, send `/study Explain what an API is`.
5. Read the API log for both messages.

Expected Open WebUI results:

- Message 3: the answer starts with `[route: general]` and is an ordinary chat reply.
- Message 4: the answer starts with `[route: study]`, then a plain explanation and exactly one next step.
- Both arrive through the same endpoint in the same conversation, as before.

Expected trace: `route=general nodes=router,general` for message 3 and `route=study nodes=router,study` for message 4.

If a check fails, report the exact output and stop.

## Handover

- **Files created or changed**: `pyproject.toml`, `uv.lock`, `src/learning_companion/graph.py` (new), `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`.
- **Commands actually run**:
  - `uv sync`, `uv run ruff format .`, `uv run ruff check .`: passed.
  - Local server on port 8013 with `APP_ENV=development` and four requests: "Hello!" gave `[route: general]` and a normal reply; `/study Explain what an API is` gave `[route: study]`, an explanation and one next step; bare `/study` gave the usage hint; a streaming `/study` request sent the role chunk, the label chunk, many text chunks, a stop chunk, then `data: [DONE]`.
- **Open WebUI result**: not yet checked by the participant. Run completion checks 3 to 5 in the real chat.
- **Trace**: `route=general nodes=router,general` and `route=study nodes=router,study`.
- **Streaming**: text streamed in pieces using `stream_mode=["updates", "messages"]`, not as one chunk.
- **Deviations**: both chains are built when the graph is built (they need the same settings), so a missing key now also gives the configuration error for a bare `/study`. `langgraph` was already installed through `langchain`; it is now listed explicitly. `UV_LINK_MODE=copy` was needed for `uv`.
- **What Story 4.2 will extend**: it adds one bounded review path to this same graph. The state, router, two answer nodes, and edges stay, and a review step plus its edges are added without a loop that can run forever.

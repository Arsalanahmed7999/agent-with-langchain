# Story 4.2 — Bounded answer review and improvement

Status: implemented

## Purpose

Story 4.1 put the routing choice into a small LangGraph workflow: router, general-chat, study-helper. This story extends that same graph with a review step. The chatbot checks a draft answer once, improves it once when needed, and then stops.

The workflow stays bounded. There is a maximum of one improvement. There is no planner, no tool call, no retry, and no open-ended agent behaviour.

## What this story implements in plain English

After a question enters the chatbot:

- The router and the answer step work as before, except the answer is now a **draft**, not the final answer.
- A **reviewer** reads the draft once against a short fixed classroom rule. It decides `approve` or `improve` and gives one short reason.
- If the decision is `approve`, the draft becomes the final answer and the workflow ends.
- If the decision is `improve`, an **improver** rewrites the draft once, using the reviewer's reason. The reviewer then looks at the new draft one last time and the result is accepted as final.
- Whatever happens, the workflow ends after at most one improvement. It never loops further.

## Terms used in this story

- The **router** is still ordinary Python. It is not an agent.
- The **reviewer** and **improver** are small LLM-powered specialist nodes. For this classroom example they may be called specialist agents.
- There is still no MCP tool call. An MCP call could be a future node, but it is outside this story.

## New state fields

Story 4.1 state (`user_message`, `messages`, `route`, `answer`) stays. Story 4.2 adds only these five fields and renames the role of `answer` as described below:

| Field | Meaning in plain English |
| --- | --- |
| `draft_answer` | The answer the general-chat or study-helper node wrote. It has not been reviewed yet. |
| `review_decision` | `approve` or `improve`. Written by the reviewer. |
| `review_reason` | One short sentence from the reviewer saying why. |
| `revision_count` | How many times the improver has run. Starts at 0. The maximum is 1. |
| `final_answer` | The answer that is sent to Open WebUI. Written when the draft is approved or accepted as final. |

The Story 4.1 `answer` field is replaced by `draft_answer` (written by the answer nodes) and `final_answer` (written by the reviewer). Nothing else in the state changes.

## Prerequisites

- Stories 1.1 to 4.1 are done and working.
- `.env` has `GEMINI_API_KEY` and `GEMINI_MODEL_NAME`. The reviewer and improver use this same configured Gemini model. No new setting is added.
- Open WebUI is connected to `http://127.0.0.1:8000/v1`. Do not change Open WebUI.

## Work to do

Routes, `.env` names, request and response shapes, normal JSON replies, SSE format, history conversion, the `[route: ...]` label, and `/study` routing stay as they are. `select_route()`, both answer chains, and both prompts stay as they are. Extend the existing graph; do not rebuild it.

1. **Add the reviewer and improver instructions and chains** in `src/learning_companion/chain.py`:
   - `REVIEW_INSTRUCTION`: a short fixed classroom rule. The draft is clear, in plain language, suitable for a beginner, and fits its role: a friendly general reply for `general`, or a concise explanation with a small example where useful and exactly one next step for `study`. It must not claim to research, browse, or retrieve data.
   - `build_review_chain(settings)`: prompt (fixed instruction as a system message; route and draft as the human message) → Gemini model with structured output of `ReviewDecision` (a Pydantic model with `decision: Literal["approve", "improve"]` and `reason: str`).
   - `IMPROVE_INSTRUCTION` and `build_improve_chain(settings)`: prompt (fixed instruction; route, draft, and reason as the human message) → Gemini model → text output. It rewrites the answer once. It does not use tools, browse, retrieve information, make a plan, or choose a route.
   - Both builders raise the same `ConfigError` messages as the existing builders.
2. **Extend the graph** in `src/learning_companion/graph.py`:
   - Update `RouteState` with the five fields above. Remove `answer`.
   - `general_node` and `study_node` write `draft_answer` instead of `answer`. A bare `/study` writes the usage hint as the draft and sets `review_decision` to `approve`.
   - `reviewer_node`: if `review_decision` is already `approve` (the usage hint), or `revision_count` is 1, it makes no model call and writes `final_answer = draft_answer` with decision `approve`. Otherwise it calls the review chain and writes `review_decision` and `review_reason`. When the decision is `approve` it also writes `final_answer`.
   - `improver_node`: calls the improve chain with the draft and reason, writes the new text to `draft_answer`, and sets `revision_count` to `revision_count + 1`.
   - `build_graph(settings)` builds the two new chains at the same time as the existing ones.
3. **Wire the bounded edges:**
   - `START → router`, and the conditional edge from `router` to `general` or `study`, as in Story 4.1.
   - `general → reviewer` and `study → reviewer`.
   - Conditional edge from `reviewer`: `approve` goes to `END`; `improve` goes to `improver` only when `revision_count` is 0; anything else goes to `END`.
   - `improver → reviewer`.

   This is one visible cycle, reviewer → improver → reviewer, and the reviewer cannot send the draft to the improver twice. There is no other loop or retry.
4. **Update `src/learning_companion/main.py`** so the endpoint reads `final_answer`. The answer text still starts with `[route: ...]`. The draft is not shown, because the reviewer may change it. Send the final answer after the label as one content chunk in streaming mode. Normal JSON, the role chunk, the stop chunk, and `data: [DONE]` stay as before. State in the Handover that streaming now sends the reviewed answer in one piece.
5. **Add a compact development trace.** With `APP_ENV=development`, log route, reviewer decision, revision count, and node sequence, for example `route=study decision=approve revisions=1 nodes=router,study,reviewer,improver,reviewer`. Never log keys, instructions, drafts, or message text.
6. **Update `docs/architecture.md`** with the two new nodes, the state additions, the full graph diagram, the edge rules, the one-revision limit, and the scope boundary.
7. **Update `docs/manual-tests.md`** with a Story 4.2 section.

Full graph diagram to add to the architecture file:

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

Do not add databases, persistence, RAG, web search, tools, MCP, human approval, a planner, more agents, broad tests, production controls, observability platforms, or deployment work.

Files changed: `src/learning_companion/chain.py`, `src/learning_companion/graph.py`, `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`. No dependency changes.

## Completion checks

1. `uv run ruff format .` and `uv run ruff check .` pass.
2. Start the API with `APP_ENV=development`: `uv run uvicorn learning_companion.main:app --host 127.0.0.1 --port 8000`.
3. In a new Open WebUI chat, send "Hello!". The reviewer should approve it directly.
4. In the same chat, send `/study Explain what LangGraph state, nodes, and edges are`. Pick a question where clearer wording may help. If the reviewer approves it directly, try a more tangled question, such as `/study explain graphs state nodes edges all at once`.
5. Read the API log for both messages.

Expected Open WebUI results:

- Message 3: the answer starts with `[route: general]` and is an ordinary chat reply.
- Message 4: the answer starts with `[route: study]`, then a plain explanation and exactly one next step. It is the final reviewed answer. No draft or review text appears.

Expected trace:

- Message 3: `route=general decision=approve revisions=0 nodes=router,general,reviewer`.
- Message 4, when the reviewer asks for an improvement: `route=study decision=approve revisions=1 nodes=router,study,reviewer,improver,reviewer`. If the reviewer approves directly, the trace is `route=study decision=approve revisions=0 nodes=router,study,reviewer`. The reviewer's decision is the model's choice, so the improve path is not guaranteed for every question. Report which trace you saw.

If a check fails, report the exact output and stop.

## Final capstone outcome

One Learning Companion Chatbot: Open WebUI sends a chat request to one OpenAI-compatible FastAPI endpoint. A small LangGraph workflow routes the question with ordinary Python, one LangChain chain writes a draft, a reviewer checks it, an improver rewrites it at most once, and the final answer returns to Open WebUI as normal JSON or SSE. It uses the same configured Gemini model throughout and keeps nothing after a request ends.

## Handover

- **Files created or changed**: `src/learning_companion/chain.py`, `src/learning_companion/graph.py`, `src/learning_companion/main.py`, `docs/architecture.md`, `docs/manual-tests.md`. No dependency changes.
- **Commands actually run**:
  - `uv run ruff format .` and `uv run ruff check .`: passed.
  - Local server on port 8014 with `APP_ENV=development` and five requests: "Hello!" (general, approved); `/study Explain what LangGraph state, nodes, and edges are` (approved directly); `/study explain graphs state nodes edges all at once in as much jargon as possible` (improved once); bare `/study` (usage hint, no review); a streaming `/study What is an API?`.
- **Open WebUI result**: not yet checked by the participant. Run completion checks 3 to 5 in the real chat.
- **Trace**:
  - `route=general decision=approve revisions=0 nodes=router,general,reviewer`
  - `route=study decision=approve revisions=0 nodes=router,study,reviewer`
  - `route=study decision=approve revisions=1 nodes=router,study,reviewer,improver,reviewer`
  - bare `/study`: `route=study decision=approve revisions=0 nodes=router,study,reviewer`
- **Streaming**: confirmed. The streaming reply was the role chunk, the `[route: study]` label chunk, one chunk with the reviewed answer, a stop chunk, then `data: [DONE]`.
- **Deviations**: the Story 4.1 token-by-token streaming is gone, as this story expects, because the reviewer must see the whole draft first. The `uv` commands needed `UV_LINK_MODE=copy`.

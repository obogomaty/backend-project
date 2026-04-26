# Maths Intelligence Agent (backend)

FastAPI service with **Server-Sent Events** streaming on `POST /chat-stream`, optional SymPy tool routing, and Groq for LLM fallback.

## Requirements

- Python 3.11+ (3.10+ should work)
- A [Groq](https://console.groq.com/) API key (used when the math tool does not handle the query)

## Setup

From this directory:

```bash
python -m venv venv
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`: set `GROQ_API_KEY`, and set `CORS_ORIGINS` to the exact origins of your frontend (comma-separated). Use `*` only for quick local testing.

## Run

```bash
uvicorn App.main:app --reload --host 127.0.0.1 --port 8000
```

The streaming endpoint expects JSON `{"message": "..."}` and returns `text/event-stream` with custom event types `delta`, `error`, and `done` (see frontend `sseReader.js`).

## API contracts

### Request: `POST /chat-stream`

JSON body (validated with Pydantic, `extra` fields forbidden):

```json
{ "message": "string (1 … 200000 chars)" }
```

### HTTP errors (non-2xx before the stream starts)

JSON body shape:

```json
{
  "error": {
    "code": "validation_error | bad_request | not_found | internal_error | …",
    "message": "Human-readable summary",
    "request_id": "uuid-or-client-id",
    "details": null
  }
}
```

`details` is set for `422` validation failures (Pydantic error list). `X-Request-ID` response header matches `request_id` when generated server-side.

### SSE stream

After `200` with `Content-Type: text/event-stream`, each logical event uses the `event` field:

| `event` | `data` |
| --- | --- |
| `delta` | Plain-text assistant fragment |
| `error` | JSON string with the same **`{"error":{...}}`** envelope as HTTP errors (`code` is usually `stream_error`) |
| `done` | Empty string; stream finished |

## Architecture (modular layout)

| Path | Role |
| --- | --- |
| `App/main.py` | App factory, CORS, lifespan, mounts routers |
| `App/api/routes/chat.py` | Chat SSE HTTP surface |
| `App/services/agent_service.py` | Orchestration: guardrails → SymPy → Groq → evaluation log |
| `App/security/guardrails.py` | Input length, code-injection markers, prompt-injection heuristics |
| `App/security/response_eval.py` | Post-output checks (deterministic for SymPy; soft heuristics for LLM) |
| `App/tools/math_tool.py` | SymPy `safe_math` / expression-shape detection |
| `App/core/settings.py` | Typed settings from environment |
| `App/infra/structured_log.py` | JSON-lines file logging |
| `App/infra/tracer.py` | `trace()` → one JSON object per line |
| `App/schemas/` | `ChatRequest`, `ErrorResponse`, SSE payload helpers |
| `App/api/error_handlers.py` | JSON error envelope for 4xx/5xx and validation |
| `App/api/middleware.py` | `X-Request-ID` / `request.state.request_id` |

## Guardrails (input)

- **Max length** — `MAX_INPUT_CHARS` (default 8000).
- **Code / host abuse** — disallowed substrings such as `__import__`, `os.system`, `eval(`, etc. (tuned to reduce false positives vs naive `eval` substring matches).
- **Prompt injection** — regex heuristics for role hijacking, fake system blocks, jailbreak phrasing, and exfiltration asks.
- **Encoding noise** — rejects unusually high density of control / bidi / zero-width characters.

Rejected requests return a short user-facing line and are logged with `agent_blocked`.

## Response evaluation (output)

Runs **after** each completed assistant path and emits `response_evaluation` in the log. This is **not** a guarantee of factual correctness for open-ended LLM text.

- **SymPy path** — Replays `safe_math` on the same user message and requires normalized string equality with the streamed output (strong consistency check).
- **LLM path** — Enforces max output size, scans for obvious secret/key patterns, and applies a **soft** heuristic when the user message looked math-like but the reply is long and lacks a `Final Answer:` line (warning only).
- **Blocked / config-error paths** — Generic structural checks only.

For higher assurance on free-form answers you would add offline eval datasets, model grading, or human review — out of scope for this small service.

## Logging

Structured logs are written as **JSON lines** to `LOG_FILE` (default `logs/app.log`). Logging starts when the app process starts.

Typical `kind` values:

| `component` | `kind` | Meaning |
| --- | --- | --- |
| `http` | `app_startup` / `app_shutdown` | Process lifecycle |
| `http` | `http_request` | New chat request (`request_id`, message length) |
| `http` | `sse_stream_open` / `sse_stream_close` | SSE response lifecycle |
| `http` | `unhandled_exception` | Unhandled error before response (500 path) |
| `agent` | `agent_input` | User message |
| `agent` | `agent_blocked` | Guardrail refusal |
| `agent` | `agent_tool` | SymPy path attempted |
| `agent` | `agent_output` | SymPy-only completion |
| `agent` | `agent_llm_*` | Groq stream lifecycle |
| `agent` | `response_evaluation` | Output checks (`ok`, `checks`, `warnings`) |

Each line includes `ts` (UTC ISO8601), `request_id` when applicable, and `data` (truncated for large payloads).

## Environment variables

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | For LLM path | Groq API key. |
| `GROQ_MODEL` | No | Chat completion model id (default `llama-3.1-8b-instant`). |
| `GROQ_TEMPERATURE` | No | Sampling temperature `0`–`2` (default `0.7`). |
| `GROQ_TOP_P` | No | Nucleus sampling `0`–`1` (default `1.0`). |
| `GROQ_MAX_COMPLETION_TOKENS` | No | Hard cap on generated tokens per completion (default `4096`, max clamped in code). |
| `GROQ_FREQUENCY_PENALTY` | No | OpenAI-style frequency penalty `-2`–`2` (default `0`). |
| `GROQ_PRESENCE_PENALTY` | No | OpenAI-style presence penalty `-2`–`2` (default `0`). |
| `CORS_ORIGINS` | No | Comma-separated allowed origins, or `*` for any origin. |
| `LOG_FILE` | No | Path to JSON-lines log file (default `logs/app.log`). |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, etc. (default `INFO`). |
| `LOG_INCLUDE_PID` | No | `true` / `false` — add `pid` to each log line. |
| `MAX_INPUT_CHARS` | No | Max characters per user message (default 8000). |
| `MAX_LLM_OUTPUT_CHARS` | No | Max characters for assistant text on LLM path (default 48000). |

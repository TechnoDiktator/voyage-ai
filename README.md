# Voyage AI (TripMate AI)

A multi-agent travel planner built with **LangGraph**, **FastAPI** and the **Model Context Protocol (MCP)**. A supervisor agent screens each request, routes it to specialist agents that call live MCP tools, and pauses for **human approval** before producing the final plan. State is checkpointed in **PostgreSQL**.

## Highlights

| Concept | How it is used |
|---|---|
| **Multi-agent orchestration** | A LangGraph `StateGraph` with a supervisor and specialist agents (flights, hotels, weather, budget, itinerary). |
| **Supervisor routing** | The supervisor chooses which specialists run for each request, so a flight-only question skips the rest. |
| **Input guardrail** | Off-topic or harmful requests are blocked before any tool or specialist runs. |
| **Human-in-the-loop (HITL)** | The graph pauses with LangGraph `interrupt()`. The user approves or requests changes, up to **3 revision rounds**. |
| **MCP tool integration** | Tavily (remote), AviationStack (local stdio) and a custom weather server (local stdio) via `langchain-mcp-adapters`. |
| **Durable state** | `PostgresSaver` stores each thread, so a paused plan can resume across requests. |
| **Token-budget control** | Tool outputs are clipped before prompting to stay within Groq's per-request token limit. |
| **Graceful degradation** | If an MCP tool fails, the agent falls back to clearly labelled general guidance instead of failing the run. |

## Architecture

```mermaid
flowchart LR
    U[Browser UI] -->|POST /api/travel| API[FastAPI app.py]
    U -->|POST /api/travel/approve| API
    API --> SVC[services/travel_service.py]
    SVC --> G[LangGraph workflow]
    G <-->|checkpoints| PG[(PostgreSQL)]
    G --> LLM[Groq LLM]
    G --> MCP[MCP client]
    MCP --> T[Tavily MCP - remote]
    MCP --> A[AviationStack MCP - local stdio]
    MCP --> W[Weather MCP - local stdio]
    A -->|HTTPS| AV[(AviationStack API)]
    W -->|HTTPS| OW[(OpenWeather API)]
```

## Agent workflow

```mermaid
flowchart TD
    S([START]) --> SUP[Supervisor: guardrail + routing]
    SUP -->|blocked| GB[Guardrail blocked response]
    GB --> E([END])
    SUP -->|allowed| FL[Flight agent]
    SUP -.->|if selected| HT[Hotel agent]
    FL -.-> HT
    HT -.-> WX[Weather agent]
    WX -.-> BG[Budget agent]
    BG --> IT[Itinerary agent]
    FL -.->|skips unselected agents| IT
    IT --> HA{{Human approval - interrupt}}
    HA -->|approved| FN[Final agent]
    HA -->|changes requested and revisions < 3| IT
    HA -->|revision cap reached| FN
    FN --> E
```

Specialists always run in a fixed order (flight, hotel, weather, budget, itinerary). The supervisor decides which of them are included, and the router skips the rest.

### Human-in-the-loop sequence

```mermaid
sequenceDiagram
    participant User
    participant UI
    participant API as FastAPI
    participant Graph as LangGraph
    participant DB as PostgreSQL

    User->>UI: Describe the trip
    UI->>API: POST /api/travel
    API->>Graph: invoke(new thread)
    Graph->>DB: checkpoint after each node
    Graph-->>API: paused at interrupt (draft itinerary)
    API-->>UI: requires_approval = true
    loop up to 3 revisions
        User->>UI: Request changes with feedback
        UI->>API: POST /api/travel/approve (approved=false)
        API->>Graph: resume(Command)
        Graph-->>API: revised draft, paused again
        API-->>UI: requires_approval = true
    end
    User->>UI: Approve
    UI->>API: POST /api/travel/approve (approved=true)
    API->>Graph: resume(Command)
    Graph-->>API: final plan
    API-->>UI: answer
```

## Agents

| Agent | File | Responsibility | Data source |
|---|---|---|---|
| Supervisor | `agents/supervisor.py` | Runs the input guardrail, extracts trip constraints, picks the specialists to run. Falls back to the full workflow if its JSON cannot be parsed. | Groq LLM |
| Guardrail blocked | `agents/guardrail_blocked.py` | Ends the run with a refusal message for off-topic requests. | None |
| Flight | `agents/flight.py` | Summarises likely airports, airlines, duration and fare guidance. | AviationStack MCP |
| Hotel | `agents/hotel.py` | Searches for accommodation and neighbourhoods. | Tavily MCP |
| Weather | `agents/weather.py` | Gets current weather and forecast for the destination. | Weather MCP |
| Budget | `agents/budget.py` | Judges whether the trip fits the budget and suggests savings. | Groq LLM |
| Itinerary | `agents/itinerary.py` | Builds the draft day-by-day plan, and revises it using human feedback. | Groq LLM |
| Human approval | `agents/human_approval.py` | Pauses via `interrupt()` and records the decision and feedback. | Human |
| Final | `agents/final.py` | Produces the polished plan with the required sections and tables. | Groq LLM |

## MCP servers

| Server | Transport | Location | Used by |
|---|---|---|---|
| Tavily | `streamable_http` | Remote, hosted by Tavily | Hotel agent |
| AviationStack | `stdio` (`uvx aviationstack-mcp`) | Local subprocess that calls the AviationStack API over HTTPS | Flight agent |
| Weather | `stdio` (`custom_weather_mcp_server.py`) | Local FastMCP server that calls OpenWeather over HTTPS | Weather agent |

A `stdio` server is a local process the app starts itself. It still fetches its data from the remote provider over the network.

## Project structure

```text
voyage-ai/
├── app.py                        # FastAPI app and HTTP endpoints
├── config.py                     # Env/SSL setup, model name, limits, agent order
├── llm.py                        # Shared Groq model and JSON/text helpers
├── state.py                      # TravelState (shared LangGraph state)
├── utils.py                      # Text helpers (as_text, clip)
├── mcp_client.py                 # MCP client configuration and tool wrappers
├── custom_weather_mcp_server.py  # Local OpenWeather MCP server
├── agents/                       # One module per agent
│   ├── supervisor.py
│   ├── guardrail_blocked.py
│   ├── flight.py
│   ├── hotel.py
│   ├── weather.py
│   ├── budget.py
│   ├── itinerary.py
│   ├── human_approval.py
│   └── final.py
├── workflow/
│   ├── routing.py                # Conditional edge functions
│   ├── graph.py                  # Graph assembly and compile
│   └── persistence.py            # PostgreSQL checkpointer
├── services/
│   └── travel_service.py         # Start/resume runs and shape API responses
├── templates/index.html          # Web UI
├── static/                       # script.js and style.css
├── tools/                        # Legacy REST helpers (not in the active path)
├── backend_without_mcp.py        # Legacy non-MCP workflow (not in the active path)
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

## Tech stack

- Python 3.10+, FastAPI, Uvicorn, Pydantic, Jinja2
- LangGraph, LangChain, `langchain-groq`
- Groq LLM, default `openai/gpt-oss-120b`
- PostgreSQL with Psycopg and `langgraph-checkpoint-postgres`
- MCP via `langchain-mcp-adapters`
- HTML, CSS and vanilla JavaScript frontend

## Prerequisites

- Python 3.10 or newer
- A PostgreSQL database reachable from the app
- `uv` installed, with `uvx` on the `PATH` (it launches `aviationstack-mcp`)
- API keys for Groq, Tavily, AviationStack and OpenWeather

## Configuration

Create a `.env` file in the project root. Never commit it.

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
# Optional: override the default model
# GROQ_MODEL=openai/gpt-oss-120b
```

`sslmode=require` is added to `DATABASE_URL` when it is missing. If Groq retires a model, set `GROQ_MODEL` to one your account can use.

## Run locally

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvx --version        # must work in this same environment
python app.py
```

Open <http://127.0.0.1:8000>.

## Run with Docker

```bash
docker build -t voyage-ai .
docker run --env-file .env -p 8000:8000 voyage-ai
```

The image runs as a non-root user and has a health check on `/health`. `.dockerignore` keeps `.env` out of the image, so secrets are passed at runtime.

## HTTP API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Web UI |
| POST | `/api/travel` | Start a plan. Pauses for approval. |
| POST | `/api/travel/approve` | Approve, or reject with feedback. |
| GET | `/health` | Liveness check. Does not test the database or providers. |

### `POST /api/travel`

```json
{ "message": "Plan a 5-day trip to Tokyo from Dhaka under 2 lakhs" }
```

Omit `thread_id` to start a new thread. The response includes:

| Field | Meaning |
|---|---|
| `thread_id` | Identifies this plan run. Required to approve or revise it. |
| `requires_approval` | `true` while the draft is waiting for the human. |
| `answer` / `itinerary` | The draft while paused, the final plan once approved. |
| `approval_request` | The message shown with the approval panel. |
| `selected_agents`, `supervisor_reasoning`, `trip_constraints` | What the supervisor decided and why. |
| `guardrail_allowed`, `guardrail_reason` | Result of the input guardrail. |
| `flight_results`, `hotel_results`, `weather_results`, `budget_results` | Raw specialist outputs. |
| `revision_count`, `max_revisions` | Revision progress, capped at 3. |
| `llm_calls` | Number of LLM calls in the run. |

### `POST /api/travel/approve`

```json
{ "thread_id": "user_...", "approved": false, "feedback": "Add more museums" }
```

Rejecting requires non-empty `feedback`. Once `max_revisions` is reached, the next response finalizes the plan.

```bash
curl -X POST http://127.0.0.1:8000/api/travel \
  -H "Content-Type: application/json" \
  -d '{"message":"Plan a 3 day Paris trip from London under 800 GBP"}'
```

## Design notes

- **One thread per plan.** Each request gets a new `thread_id`. There are no user accounts or conversation history yet.
- **Fail open on the guardrail and supervisor.** A model or JSON error falls back to allowing the request and running the full workflow, so a formatting hiccup does not break planning.
- **Clipping.** Prompts truncate each tool output (`CLIP_LIMITS` in `config.py`) to stay under Groq's free-tier limit of 8000 tokens per request.
- **`interrupt()` is never wrapped in try/except,** because LangGraph uses an exception internally to pause the graph.

## Limitations and roadmap

- No automated tests yet. Routing, `clip` and `as_text` are good first candidates.
- No user identity or saved conversation list.
- LLM output is unverified. Check prices and availability with the providers before booking.
- Provider quotas, outages and rate limits can affect results.

## Security notes

- Keep `.env` out of version control and rotate any key that was ever shared.
- Use a restricted PostgreSQL user.
- The free Render PostgreSQL instance expires after a limited time, so check its expiry before relying on it.

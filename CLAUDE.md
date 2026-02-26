# Enterprise AI Analyst

## Architecture

```
Vue 3 SPA  ──ws/http──>  Express BFF (:3000)  ──http──>  FastAPI (:8000)
                              │                              │
                         WebSocket /ws                  Qdrant (vectors)
                         Proxy /api/*                   Neo4j (knowledge graph)
                                                        DuckDB (SQL analytics)
                                                        OpenAI (embeddings)
                                                        Anthropic Claude (LLM)
```

- **Frontend**: Vue 3 + TypeScript + Tailwind CSS, bundled by Vite
- **BFF**: Express.js (Node/TypeScript) — proxies `/api/*` to FastAPI, serves SPA, hosts WebSocket on `/ws`
- **Backend**: FastAPI (Python 3.11+) — RAG pipeline, multi-agent orchestration, document ingestion
- **Infra**: Docker Compose for Qdrant + Neo4j

## Key Paths

| Layer | Path |
|-------|------|
| Python backend | `src/` (api, rag, agents, integrations, models, config) |
| FastAPI routes | `src/api/routes/` (health, query, ingest) |
| Node BFF | `web/server/` (index.ts, ws.ts, routes/) |
| Vue frontend | `web/src/` (views, components, api, types, router) |
| Tests | `tests/` (unit, integration, benchmark) |
| Infrastructure | `infra/` (docker-compose.yml, Dockerfile) |
| Demo data | `demo/sample_data/` |

## Dev Commands

```bash
./run.sh dev          # Full stack (Docker + FastAPI + Vue/BFF)
./run.sh infra        # Docker services only (Qdrant, Neo4j)
./run.sh backend      # FastAPI only
./run.sh frontend     # Vue + BFF dev server only
./run.sh build        # Production build
./run.sh stop         # Stop Docker services

cd web && npm run dev       # Frontend dev server
cd web && npm run build     # Type-check + Vite build
pytest                      # Python tests
pytest -m integration       # Integration tests (needs Docker)
```

## Conventions

- **TypeScript strict mode** enabled for frontend
- **Pydantic models** for all Python request/response types
- **Protocol-based abstractions** for chunkers, LLM providers, stores — easy to swap implementations
- **Async throughout** — Python uses `asyncio`, TypeScript uses `async/await`
- Vue components use `<script setup lang="ts">` with Composition API
- BFF routes proxy to FastAPI at `http://localhost:8000` (configured in `web/server/routes/api.ts`)
- Path alias: `@/` maps to `web/src/` in TypeScript imports
- Structured logging via `structlog` in Python

## WebSocket Protocol

Current state: **echo mode** (BFF echoes messages back, not yet connected to FastAPI).

```
Client sends:  { "type": "chat", "content": "user message" }
Server echoes: { "type": "echo", "content": "user message" }
```

- Server: `web/server/ws.ts` — `attachWebSocket(server)` on path `/ws`
- Client: `web/src/api/ws.ts` — `useWebSocket()` composable with auto-reconnect (exponential backoff)
- Types: `WsMessage` in `web/src/types/index.ts`

## Environment

Copy `.env.example` to `.env` and fill in API keys. Key vars:
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — LLM providers
- `QDRANT_URL` (default `http://localhost:6333`)
- `NEO4J_URI` (default `bolt://localhost:7687`)

## Roadmap

### Completed
- [x] FastAPI backend with RAG pipeline (chunking, embedding, retrieval, generation)
- [x] Multi-agent system (RAG agent, SQL agent, summarizer, orchestrator)
- [x] Knowledge graph integration (Neo4j entity/relationship extraction)
- [x] Vue 3 frontend with chat UI and document ingestion
- [x] Express BFF with API proxy and SPA serving
- [x] WebSocket echo layer (BFF ↔ frontend)

### Next Steps
- [ ] **WebSocket → FastAPI streaming**: BFF forwards WS messages to FastAPI, streams LLM responses back token-by-token
- [ ] **Streaming chat UI**: Render tokens as they arrive (typing effect)
- [ ] **Chat history persistence**: Store conversation history server-side
- [ ] **Authentication**: User auth for multi-tenant support
- [ ] **File upload ingestion**: Drag-and-drop document upload in the UI
- [ ] **Agent status streaming**: Show which agent is active during multi-agent queries

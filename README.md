# Enterprise AI Analyst

Multi-agent enterprise analytics platform with RAG pipeline, knowledge graph, and SQL analytics.

---

## Architecture

```
Browser → Node BFF (:3000) → FastAPI (:8000) → Qdrant (vectors)
                                             → Neo4j (knowledge graph)
                                             → DuckDB (SQL analytics)
```

The Node BFF (Express) proxies all `/api/*` requests to the FastAPI backend, stripping the `/api` prefix before forwarding.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Docker | 24+ (with Compose v2) |
| Python | 3.11+ |
| Node | 18+ |
| OpenAI API key | For embeddings |
| Anthropic API key | For LLM (Claude) |

---

## Quick Start

```bash
# 1. Copy the example env file and fill in your API keys
cp .env.example .env

# 2. Install frontend dependencies
cd web && npm install && cd ..

# 3. Install Python dependencies (preferably in a venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 4. Start the full dev stack
./run.sh dev
```

The dev stack starts:
- Docker services (Qdrant, Neo4j, DuckDB via docker-compose)
- FastAPI backend on `http://localhost:8000`
- Vue SPA + Node BFF on `http://localhost:3000`

Press `Ctrl+C` to stop all processes and clean up.

---

## Manual Setup

### Infrastructure (Docker)

```bash
./run.sh infra
# or directly:
docker compose -f infra/docker-compose.yml up -d
```

This brings up Qdrant (`:6333`), Neo4j (`:7474`/`:7687`), and any other configured services.

### Backend (FastAPI)

```bash
source .venv/bin/activate
./run.sh backend
# or directly:
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Vue 3 + Node BFF)

```bash
cd web
npm install       # first time only
./run.sh frontend
# or directly:
npm run dev
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /query | Ask a question against ingested documents |
| POST | /ingest | Ingest a document into the RAG pipeline |
| GET | /health | Basic liveness check |
| GET | /health/ready | Readiness check (verifies all dependencies) |

> **Note:** The Node BFF proxies `/api/*` to FastAPI, stripping the `/api` prefix. For example, `POST /api/query` from the browser becomes `POST /query` on the FastAPI server.

---

## Project Structure

```
├── src/                  # Python backend
│   ├── api/              # FastAPI app + routes
│   ├── agents/           # Multi-agent orchestration
│   ├── rag/              # Chunking, embedding, retrieval
│   ├── integrations/     # Qdrant, Neo4j, DuckDB, LLM providers
│   ├── evaluation/       # Faithfulness, relevance, hallucination checks
│   └── observability/    # Logging, metrics, tracing
├── web/                  # Frontend (Vue 3 + Node BFF)
│   ├── server/           # Express BFF with proxy to FastAPI
│   └── src/              # Vue SPA
├── infra/                # Docker Compose + Dockerfile
├── tests/                # Unit, integration, benchmark tests
└── demo/                 # Demo scripts
```

---

## NPM Scripts

Run from the `web/` directory (or via `./run.sh`):

| Script | Command | Description |
|--------|---------|-------------|
| dev | concurrently "dev:vue" "dev:server" | Start Vue + BFF together |
| dev:vue | vite | Vite dev server with HMR |
| dev:server | tsx watch server/index.ts | BFF with auto-reload |
| build | vue-tsc && vite build | Type-check + production build |
| start | node --import tsx server/index.ts | Production server |
| preview | build + start | Build then serve |

```bash
# Build frontend for production
./run.sh build
# or:
cd web && npm run build
```

---

## Running Tests

```bash
pytest                          # all tests
pytest tests/unit               # unit only
pytest -m integration           # integration (needs Docker)
pytest -m benchmark             # benchmarks
pytest --cov=src                # with coverage
```

---

## Docker

### Infrastructure (`infra/docker-compose.yml`)

The compose file defines the services the platform depends on:
- **Qdrant** — vector database for semantic search and RAG retrieval
- **Neo4j** — knowledge graph for entity relationships
- Additional services as configured

Use `./run.sh infra` to start and `./run.sh stop` to tear down.

### Backend Container (`infra/Dockerfile`)

The `Dockerfile` containerises the Python FastAPI backend for production deployments. Build and run it with standard Docker commands or integrate it into a larger compose stack.

---

## Environment Variables

Copy `.env.example` to `.env` and populate the required values:

```bash
cp .env.example .env
```

See `.env.example` for the full list of required and optional variables, including API keys, service URLs, and feature flags.

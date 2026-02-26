#!/usr/bin/env bash
set -euo pipefail

# Determine the project root (directory where this script lives)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ---------------------------------------------------------------------------
# Prerequisite checks (warn only, do not exit)
# ---------------------------------------------------------------------------
check_prerequisites() {
  if ! command -v docker &>/dev/null; then
    warn "docker not found — Docker services will not be available"
  fi
  if ! command -v python3 &>/dev/null; then
    warn "python3 not found — backend will not start"
  fi
  if ! command -v node &>/dev/null; then
    warn "node not found — frontend will not start"
  fi
}

# ---------------------------------------------------------------------------
# Python venv activation
# ---------------------------------------------------------------------------
activate_venv() {
  local venv="${PROJECT_ROOT}/.venv/bin/activate"
  if [[ -f "$venv" ]]; then
    # shellcheck disable=SC1090
    source "$venv"
    info "Python venv activated"
  else
    warn ".venv not found at ${venv} — using system Python"
  fi
}

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

cmd_infra() {
  info "Starting Docker infrastructure..."
  docker compose -f "${PROJECT_ROOT}/infra/docker-compose.yml" up -d
  info "Infrastructure started"
}

cmd_backend() {
  activate_venv
  info "Starting FastAPI backend on :8000..."
  uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
}

cmd_frontend() {
  info "Starting frontend dev server..."
  cd "${PROJECT_ROOT}/web"
  npm run dev
}

cmd_build() {
  info "Building frontend for production..."
  cd "${PROJECT_ROOT}/web"
  npm run build
  info "Build complete"
}

cmd_stop() {
  info "Stopping Docker infrastructure..."
  docker compose -f "${PROJECT_ROOT}/infra/docker-compose.yml" down
  info "Infrastructure stopped"
}

cmd_prod() {
  check_prerequisites

  info "Starting infrastructure (production)..."
  docker compose -f "${PROJECT_ROOT}/infra/docker-compose.yml" up -d

  info "Waiting for services..."
  sleep 3

  activate_venv

  info "Starting FastAPI backend (production)..."
  uvicorn src.api.app:app --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!

  info "Starting frontend (production)..."
  cd "${PROJECT_ROOT}/web"
  npm run start &
  FRONTEND_PID=$!

  # Trap to clean up background processes on exit
  trap 'info "Shutting down..."; kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true; wait' EXIT INT TERM

  info "Production stack running. Press Ctrl+C to stop."
  wait
}

cmd_dev() {
  check_prerequisites

  # ---- Infrastructure ----
  info "Starting Docker infrastructure..."
  docker compose -f "${PROJECT_ROOT}/infra/docker-compose.yml" up -d

  # ---- Wait for Qdrant ----
  info "Waiting for services to be ready (up to 30s)..."
  sleep 3
  local qdrant_ready=false
  for i in $(seq 1 9); do
    if curl -sf http://localhost:6333/healthz &>/dev/null; then
      qdrant_ready=true
      break
    fi
    info "  Qdrant not ready yet, retrying (${i}/9)..."
    sleep 3
  done

  if [[ "$qdrant_ready" == true ]]; then
    info "Qdrant is ready"
  else
    warn "Qdrant did not respond on :6333 — continuing anyway"
  fi

  # ---- Wait for Neo4j ----
  local neo4j_ready=false
  for i in $(seq 1 9); do
    if curl -sf http://localhost:7474 &>/dev/null; then
      neo4j_ready=true
      break
    fi
    info "  Neo4j not ready yet, retrying (${i}/9)..."
    sleep 3
  done

  if [[ "$neo4j_ready" == true ]]; then
    info "Neo4j is ready"
  else
    warn "Neo4j did not respond on :7474 — continuing anyway"
  fi

  # ---- Backend ----
  activate_venv
  info "Starting FastAPI backend on :8000..."
  cd "${PROJECT_ROOT}"
  uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000 &
  BACKEND_PID=$!

  # ---- Frontend ----
  info "Starting frontend dev server..."
  cd "${PROJECT_ROOT}/web"
  npm run dev &
  FRONTEND_PID=$!

  # ---- Trap for cleanup ----
  trap 'info "Shutting down dev stack..."; kill "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true; wait' EXIT INT TERM

  info "Dev stack running. Press Ctrl+C to stop."
  wait
}

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  cat <<EOF
Usage: $(basename "$0") <subcommand>

Subcommands:
  dev       Start everything (infra + backend + frontend) with cleanup on exit
  infra     Start Docker services only
  backend   Start FastAPI backend only
  frontend  Start frontend dev server only
  build     Build frontend for production
  prod      Run in production mode (infra + backend + frontend start)
  stop      Stop Docker services

Options:
  -h, --help  Show this help message

Examples:
  ./run.sh dev          # Start the full dev stack
  ./run.sh infra        # Bring up Qdrant, Neo4j, DuckDB via Docker
  ./run.sh backend      # Run only the FastAPI server
  ./run.sh frontend     # Run only the Vue + BFF dev server
  ./run.sh build        # Production build of the web frontend
  ./run.sh stop         # Tear down Docker services
EOF
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if [[ $# -eq 0 ]]; then
  usage
  exit 0
fi

case "$1" in
  dev)      cmd_dev      ;;
  infra)    cmd_infra    ;;
  backend)  cmd_backend  ;;
  frontend) cmd_frontend ;;
  build)    cmd_build    ;;
  prod)     cmd_prod     ;;
  stop)     cmd_stop     ;;
  -h|--help) usage       ;;
  *)
    error "Unknown subcommand: $1"
    echo ""
    usage
    exit 1
    ;;
esac

#!/usr/bin/env bash
# start_mcp_lite.sh — levanta el servidor SSE brain-control-lite (listener)
# Duradillo: reinicia si muere (ver cron ticker del perfil devops_bot) y guarda log.
set -u

REPO_DIR="C:\Users\User\consuconstruct-agents-lite-work"
VENV_PY="C:\Users\User\AppData\Local\hermes\installs\6b17de8c14938a10\environments\35496fede6184152b7efbdd37a90ed13\venv\Scripts\python.exe"
LOG_DIR="$REPO_DIR/mailbox/sent"
LOG="$LOG_DIR/mcp_server.log"
PORT="${MCP_LITE_PORT:-24425}"
DB_URL="${DATABASE_URL:-postgresql://User@127.0.0.1:5432/brain_control_lite}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

mkdir -p "$LOG_DIR"

# Eliminar stale pid? No: el cron ticker decide si reinicia.
export DATABASE_URL="$DB_URL"
export MCP_LITE_PORT="$PORT"
export OLLAMA_URL="$OLLAMA_URL"

echo "[start_mcp_lite] db_url=$DB_URL port=$PORT"; echo "[start_mcp_lite] $$ >> $LOG"
"$VENV_PY" "$REPO_DIR\mcp_server\mcp_lite_server.py" --transport sse --port "$PORT" >> "$LOG" 2>&1

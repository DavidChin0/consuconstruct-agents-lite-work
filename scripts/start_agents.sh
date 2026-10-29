#!/usr/bin/env bash
# start_agents.sh — levanta devops_bot y reviewer en esta PC
#
# Ambos agentes comparten el servidor MCP (brain-control-lite, SSE :24425) y
# se comunican por correo IMAP/SMTP vía mail_bus.py. Cada agente tiene su propia
# carpeta en el vault (NOTES_VAULT_DIR).
#
# Uso:
#   chmod +x scripts/start_agents.sh
#   ./scripts/start_agents.sh
#
# Config env (opcional):
#   NOTES_VAULT_DIR  (default: <repo>/obsidian-vault)
#   MCP_LITE_PORT    (default: 24425)
#   DATABASE_URL     (default: postgresql://devops:devops@localhost:5432/brain_control_lite)
#   OLLAMA_URL       (default: http://localhost:11434)
#   MAIL_IMAP_HOST|USER|PASS
#   MAIL_SMTP_HOST|USER|PASS
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

export NOTES_VAULT_DIR="${NOTES_VAULT_DIR:-$REPO_DIR/obsidian-vault}"
export MCP_LITE_PORT="${MCP_LITE_PORT:-24425}"
export DATABASE_URL="${DATABASE_URL:-postgresql://devops:devops@localhost:5432/brain_control_lite}"
export OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

echo "=== start_agents: repo=$REPO_DIR"
echo "=== vault=$NOTES_VAULT_DIR"
echo "=== mcp_port=$MCP_LITE_PORT"
echo "=== database_url=$DATABASE_URL"

# 0) Garantizar carpetas del vault
mkdir -p "$NOTES_VAULT_DIR/agents/devops_bot"
mkdir -p "$NOTES_VAULT_DIR/agents/reviewer"
mkdir -p "$NOTES_VAULT_DIR/knowledge"

# 1) Servidor MCP (comparte tanto a devops_bot como reviewer)
if [ -z "${MCP_PID:-}" ] || ! kill -0 "$MCP_PID" 2>/dev/null; then
  echo "[start] MCP SSE en :$MCP_LITE_PORT"
  python mcp_server/mcp_lite_server.py --transport sse --port "$MCP_LITE_PORT" > "$REPO_DIR/mailbox/sent/mcp_server.log" 2>&1 &
  MCP_PID=$!
  echo "[start] MCP pid=$MCP_PID"
else
  echo "[start] MCP ya corriendo (pid=$MCP_PID)"
fi

# 2) Poller de correo para devops_bot
if ! pgrep -f "mail_bus.py poll" > /dev/null; then
  echo "[start] poll devops_bot (MAIL_IMAP_* / MAIL_SMTP_* del perfil)"
  nohup python scripts/mail_bus.py poll >> "$REPO_DIR/mailbox/sent/devops_bot.poll.log" 2>&1 &
  echo "[start] devops_bot poll pid=$!"
else
  echo "[start] devops_bot poll ya corriendo"
fi

# 3) Poller de correo para reviewer
if ! pgrep -f "mail_bus.py poll" > /dev/null; then
  echo "[start] poll reviewer (MAIL_IMAP_* / MAIL_SMTP_* del perfil)"
  nohup python scripts/mail_bus.py poll >> "$REPO_DIR/mailbox/sent/reviewer.poll.log" 2>&1 &
  echo "[start] reviewer poll pid=$!"
else
  echo "[start] reviewer poll ya corriendo"
fi

echo "[start] ---- levantado (Ctrl+C para detener) ----"

# Mantener el shell abierto
wait

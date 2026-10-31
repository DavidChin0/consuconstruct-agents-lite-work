# 2026-10-31 · identity-tokens

Que cambia en el MCP lite (rama `feature/identity-tokens`):

- **Identidad por token.** Un token por rol (`claude_code`, `claude_dane`, `codex_hector`,
  `claude_reviewer`, `devops_bot`, `reviewer`) en `brain.mcp_tokens` (solo el hash). El rol sale
  del header `X-MCP-Lite-Token`; el argumento `from_role` de `agent_send` se ignora.
  Desaparece el token compartido `MCP_LITE_TOKEN` del servidor.
- **Permisos por rol** (`mcp_server/policy.py`): `claude_code` manda a todos y es el unico que
  usa `pg_insert`/`pg_update`. Dane y Hector mandan mensajes y piden por goals; no escriben tablas.
  Cada rol solo lee su bandeja y solo responde mensajes dirigidos a el.
- **`pg_select` endurecido**: transaccion de solo lectura, una sentencia, sin palabras de escritura
  (cerraba un hueco: `WITH x AS (DELETE ...)`).
- **Tools nuevas**: `agent_ack`, `heartbeat`, `review_request`, `review_verdict`, `commit_approval`.
- **Rol `claude_reviewer`** (`profiles/claude_reviewer/SOUL.md`, `scripts/review_commit.py`):
  aprueba o rechaza commits completos. El CLI automatico (`--auto`) corre solo sobre un
  `review_request` existente. Gate `scripts/hooks/pre-push` bloquea push sin APPROVE.
- **Listener de notificaciones** (`scripts/inbox_listener.py`): solo avisa, no ejecuta.
- **Hooks de sesion** (`scripts/hooks/session_open.py`, `session_close.py`): inyectan pendientes y
  hacen chunking de la sesion a `brain.agent_memory_chunks`.
- **Disparador de updates** (`scripts/update_trigger.py`) y esta carpeta `updates/`.

Compatibilidad: clientes viejos que mandaban `from_role` siguen funcionando (se ignora), pero
necesitan un token emitido con `scripts/mint_token.py`.

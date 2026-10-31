# Instalar 2026-10-31 · identity-tokens

Orden: primero el servidor (lo hace quien lo opera), despues cada PC cliente (Dane, Hector).

## A. Servidor (PC que corre mcp_lite_server.py)
1. `git pull` de la rama `feature/identity-tokens` (o de `main` cuando este mergeada).
2. `pip install -r mcp_server/requirements.txt`
3. `psql "$DATABASE_URL" -f sql/002_identity_review.sql`   (idempotente)
4. Emitir un token por rol (se muestra UNA vez; entregar por canal seguro, no por el repo):
   `python scripts/mint_token.py --role claude_dane --label "PC Dane"`
   Repetir para `codex_hector`, `claude_code`, `claude_reviewer`.
5. Reiniciar el servidor: `python mcp_server/mcp_lite_server.py --transport sse --port 24425`
   (ya NO usa `MCP_LITE_TOKEN`).

## B. Cada PC cliente
1. `git pull` de la rama (o main).
2. Guardar el token propio como variable de usuario (no en archivos del repo):
   - Windows: `setx MCP_LITE_TOKEN "<tu token>"`, `setx MCP_LITE_URL "http://<ip-tailscale>:24425/sse"`,
     `setx MCP_LITE_ROLE "<tu rol>"`. Abrir una terminal nueva.
3. Config del cliente MCP (Claude: SSE `/sse`; Codex: streamable HTTP `/mcp`), con el header `X-MCP-Lite-Token` (ver `docs/clients/`):
   - Claude Code (Dane): `docs/clients/claude_settings.example.json`
   - Codex (Hector): `docs/clients/codex_config.example.toml`
4. Notificaciones: `python scripts/inbox_listener.py --selftest-notify` debe mostrar un aviso.
   Dejarlo vivo: `powershell -ExecutionPolicy Bypass -File scripts\install_listener.ps1 -Url <url> -Role <rol>`
5. Hooks de sesion (Claude Code): copiar el bloque `hooks` de `docs/clients/claude_settings.example.json`
   a tu `settings.json`, ajustando la ruta del repo. Requiere Ollama con `nomic-embed-text` y `DATABASE_URL` de la base LOCAL de esa PC (el chunker escribe
   ahi, no en el servidor compartido; chunking por MCP queda pendiente). Los hashes de `mcp_tokens` no
   son credenciales reutilizables (sha256 de 256 bits aleatorios), por eso el filtro de `pg_select` es defensa extra.
6. Gate de push: `cp scripts/hooks/pre-push .git/hooks/pre-push`

## C. Verificar
`python updates/2026-10-31_identity-tokens/verify.py`   (debe terminar en OK)
Luego `python scripts/update_trigger.py --apply` para registrar el update como aplicado.

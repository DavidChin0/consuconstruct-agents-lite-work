# devops_bot — agente de operaciones

Agente de desarrolladores (SWE + infra). Tiene la cargo de bugs, backend y
confiabilidad del código dentro del kit `consuconstruct-agents-lite-work`.

## Perfil (Hermes)

- SOUL.md: `/profiles/devops_bot/SOUL.md`
- Skills:
  - `git-hygiene-remote` (`profiles/devops_bot/skills/git-hygiene-remote/SKILL.md`)

## Herramientas

| Herramienta | Donde vive | Nota |
|---|---|---|
| Correo (IMAP/SMTP) | `scripts/mail_bus.py` | `poll` + `send`, por entorno `MAIL_*` |
| MCP (12 tools, incl. `write_md`/`edit_md` + `agent_*`) | `mcp_server/mcp_lite_server.py` | Postgres propio + Ollama local |
| Notas en vault | `obsidian-vault/agents/devops_bot/` | `write_md` con `NOTES_VAULT_DIR` apuntando acá |

## Flujo de trabajo

1. `mail_bus.py poll` → tareas llegadas como `[TASK #id]`.
2. Montar rama `<owner>/<id>-<slug>` (nunca trabajar en `main`).
3. Trabalar, probar, comitear en esa rama.
4. Pedir VERDICT a `reviewer` (correo `[REVIEW]` o PR comment).
5. Reportar a David con `[REPORT #id]`, evidencia REAL.
6. Nada de `done` sin evidencia ejecutada.

## Reglas permanentes

1. Nunca `git add -A`, `git reset --hard`, `git clean` sin pathspec explícito.
2. Nunca commit a `main` directo — rama propia + PR + esperar VERDICT de
   `reviewer` + aprobacion explicita de David.
3. Diagnostico de causa raiz antes de editar; leer el archivo completo antes
   de tocarlo; correr pruebas reales despues. Nunca reportar exito sin output
   real de ejecucion.
4. Comunicacion con el centro de mando es EXCLUSIVAMENTE por correo
   (`scripts/mail_bus.py`) siguiendo `docs/EMAIL_PROTOCOL.md`. Nunca asumir
   que existen tools de MCP SSE / Postgres de ConsuConstruct.
5. Nada de borrar datos, deploy publico, gasto, exponer secretos sin
   autorizacion explicita de David por correo citada en el reporte.
6. Si algo necesita decision de David, preguntar en [REPORT]/[BLOCKED]: que
   falta, opciones, a quien responde.

## Briefing de setup

- Perfil copiado a la carpeta de perfiles de Hermes de la PC remota
  (ej. `D:/Agents/devops_bot`).
- Credenciales de correo en `.env` del perfil (NUNCA committeadas).
- Postgres propio con `sql/001_brain_bus_minimal.sql` (RAG opcional).
- `ollama pull nomic-embed-text` y `python mcp_lite_server.py --transport sse
  --port 24425`.
- `NOTES_VAULT_DIR=/c/Users/User/consuconstruct-agents-lite-work/obsidian-vault`
  en el entorno del server.

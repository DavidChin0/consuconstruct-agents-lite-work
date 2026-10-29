# Vault — obsidian de agentes (devops_bot + reviewer)

Este es el vault de Obsidian donde tanto `devops_bot` como `reviewer` guardan
sus notas de trabajo. Cada agente tiene su propia carpeta para que las notas no
se mezclen.

## Estructuras

```
obsidian-vault/
  agents/
    devops_bot/     <- notas del agente devops operations
    reviewer/       <- notas del agente review
  knowledge/        <- conocimiento compartido (referencia)
    COMMUNICATION_PROTOCOL.md
  README.md         <- este archivo
```

## Propósito

Este repo (`consuconstruct-agents-lite-work`) es el kit de partida para correr
dos agentes Hermes en PCs separadas, comunicándose por CORREO (IMAP/SMTP) y no
por el bus de ConsuConstruct (Postgres + MCP SSE).

- El agente **devops_bot** (operaciones): hace las tareas de ingeniería y
  infraestructura. Responde a `[TASK]` y reporta con `[REPORT]`.
- El agente **reviewer** (revisión): da VERDICT (`APPROVE`,
  `APPROVE (con condiciones)`, `REJECT`) sobre el trabajo de devops_bot. Nunca
  aplica cambios.

## Como funciona el agente

1. `mail_bus.py poll` (manual o por cron) trae correos nuevos a
   `mailbox/inbox/*.json`.
2. El agente lee la tarea `[TASK]`, crea rama `<owner>/<id>-<slug>`.
3. Trabaja, prueba, commitea en esa rama.
4. Pide VERDICT a `reviewer` (correo o PR comment).
5. Reporta a David con `mail_bus.py send` usando `[REPORT #id]`.

## write_md / edit_md

Los dos agentes usan la herramienta `write_md` del servidor `mcp_lite_server.py`
para guardar notas dentro de este vault. El enlace es:

```
NOTES_VAULT_DIR  ->  /c/Users/User/consuconstruct-agents-lite-work/obsidian-vault
```

Eso hace que `write_md("agents/devops_bot/<tarea>.md", ...)` grabe en
`.../obsidian-vault/agents/devops_bot/<tarea>.md`. Sin `NOTES_VAULT_DIR` el
servidor usaria `mcp_server/notes/` (por defecto del kit).

## QR / cierre

- Nada de este repo toca el Postgres de ConsuConstruct.
- Credenciales de correo: NO van en este repo (use .env.example y sus propias
  variables de entorno).

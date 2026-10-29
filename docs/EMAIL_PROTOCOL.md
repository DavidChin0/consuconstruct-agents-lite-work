# Protocolo de correo entre agentes (sin SSE, sin Postgres compartido)

## Por qué correo y no el bus de ConsuConstruct

El bus real (`brain.agent_run_events` + MCP SSE en :24424) requiere que todos
los agentes compartan el mismo Postgres. Los agentes remotos de este kit NO
comparten ese Postgres, así que no pueden usar `agent_send`/`agent_inbox` de
ConsuConstruct. El correo cumple el mismo rol (mensaje persistido,
asíncrono, con remitente/destinatario claros) sin esa dependencia.

## Formato de asunto

- `[TASK #<id>] <titulo corto>` — David asigna trabajo nuevo.
- `[REPORT #<id>] <titulo corto>` — el agente reporta avance/cierre.
- `[REVIEW #<id>] <titulo corto>` — reviewer entrega VERDICT.
- `[BLOCKED #<id>] <titulo corto>` — el agente declara bloqueo, necesita info.

`<id>` es un identificador corto estable por tarea (ej. fecha+contador:
`20261029-01`), para poder encadenar los hilos (`In-Reply-To` / `References`
del correo ya hacen esto si el cliente de correo los respeta).

## Formato de cuerpo (texto plano, sin HTML)

```
TAREA: <id>
AGENTE: <devops|reviewer>
ESTADO: <pending|in_progress|blocked|done>
RESUMEN: <una o dos lineas>

EVIDENCIA:
- <ruta o comando + resultado real, nunca inventado>

SIGUIENTE PASO: <que falta, o "ninguno, cerrado">
```

## Reglas iguales al protocolo interno de ConsuConstruct

- Nunca marcar `done` sin evidencia real ejecutada (mismo principio que
  "reporting a blocker honestly is always better than inventing a result").
- Reviewer nunca aplica cambios, solo da VERDICT (APPROVE/REJECT) por correo
  o comentario de PR.
- Ningún agente hace commit a `main`. Todo pasa por rama propia + PR.
- Si un correo pide algo fuera de alcance (borrar, gastar, exponer secretos),
  el agente responde `[BLOCKED]` pidiendo confirmación explícita de David,
  igual que el gate de mutaciones del repo canónico.

## Transporte técnico sugerido (a implementar en mail_bus.py)

- IMAP IDLE o polling corto (ej. cada 2-5 min) sobre una cuenta dedicada por
  agente (no la personal de David).
- Adjuntos grandes (diffs extensos, logs) van como adjunto de archivo, no en
  el cuerpo, para no romper el parseo de texto plano.
- Todo correo entrante/saliente se guarda también en `mailbox/` como JSON
  (log local), para no depender solo del servidor de correo como fuente de
  verdad histórica.

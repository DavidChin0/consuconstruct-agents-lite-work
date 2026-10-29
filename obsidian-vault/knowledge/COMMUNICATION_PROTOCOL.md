# Communication protocol — protocolo de correo entre agentes

Transporte: **correo (IMAP/SMTP)**. Sin SSE compartido, sin Postgres compartido.

## Asunto (formato exacto)

| Accion | Asunto |
|---|---|
| Tarea nueva (David -> agente) | `[TASK #<id>] <titulo corto>` |
| Reporte de avance (agente -> David) | `[REPORT #<id>] <titulo corto>` |
| Verdict del reviewer | `[REVIEW #<id>] <titulo corto>` |
| Bloqueo | `[BLOCKED #<id>] <titulo corto>` |

`<id>` es un identificador corto y estable por tarea (ej.
`20261029-01`), para encadenar hilos (In-Reply-To / References del cliente de
correo).

## Cuerpo (texto plano, sin HTML)

```
TAREA: <id>
AGENTE: <devops|reviewer>
ESTADO: <pending|in_progress|blocked|done>
RESUMEN: <una o dos lineas>

EVIDENCIA:
- <ruta o comando + resultado real, nunca inventado>

SIGUIENTE PASO: <que falta, o "ninguno, cerrado">
```

## Reglas

- Nunca marcar `done` sin evidencia real ejecutada.
- Reviewer nunca aplica cambios, solo da VERDICT (APPROVE / REJECT) por correo
  o comentario de PR.
- Ningun agente hace commit a `main`. Todo pasa por rama propia + PR.
- Si un correo pide algo fuera de alcance (borrar, gastar, exponer secretos),
  el agente responde `[BLOCKED]` pidiendo confirmacion explicita de David.

## Transporte tecnico (mail_bus.py)

- IMAP polling corto (cada 2-5 min) sobre una cuenta dedicada por agente.
- Adjuntos grandes como adjunto de archivo, no en el cuerpo.
- Todo correo entrante/saliente guardado tambien en `mailbox/` como JSON.

# consuconstruct-agents-lite

Starter kit independiente para correr agentes Hermes `devops_bot` + `reviewer`
en una PC separada, **sin** depender del Postgres ni del MCP SSE de ConsuConstruct.

## Por qué este repo existe

El repo canónico `specialized-consuconstruct-agents` está profundamente acoplado
a `brain.*` en Postgres (goals, bus, RAG). Copiarlo tal cual a una PC nueva sin
ese Postgres deja la mitad del código muerto. Este repo extrae solo lo
reusable (estructura de perfil, skills genéricas, convención SOUL.md) y
sustituye el transporte: en vez de MCP SSE + Postgres compartido, los agentes
se comunican por **correo electrónico** (IMAP/SMTP), que es más simple de
operar entre PCs sin abrir infraestructura compartida.

## Arquitectura

```
Centro de mando (David, ConsuConstruct)       PC remota (owner B)
  lee reportes por email                        devops_bot (clon)
  manda tareas por email            <--email-->  reviewer (clon)
  repo: este, rama <owner>/<tarea>               mismo repo, su copia local
```

- Cada agente remoto tiene su propia cuenta de email (o alias dedicado).
- Las tareas de David llegan como correo con asunto `[TASK] <descripcion>`.
- Los agentes responden con `[REPORT] <goal>` incluyendo diff/evidencia.
- Los commits van a una rama propia (`<owner>/<tarea>`), nunca a `main`.
- `main` solo se actualiza por PR revisado — reviewer da VERDICT por email o
  en el PR mismo; David aprueba antes de mergear.
- Nada de este repo toca el Postgres de ConsuConstruct. Cada instalación usa
  su propio Postgres (o ninguno) para RAG local, si lo necesita.

## Contenido

- `profiles/devops_bot/` — perfil Hermes de ejemplo (SOUL.md, skills base).
- `profiles/reviewer/` — idem, rol de revisión.
- `scripts/mail_bus.py` — mailbox simple: lee INBOX por IMAP, escribe
  `mailbox/inbox/*.json` (uno por correo nuevo), y expone `send_report()`
  para contestar por SMTP. No requiere Postgres ni SSE.
- `docs/SETUP.md` — instalación paso a paso en una PC nueva.
- `docs/EMAIL_PROTOCOL.md` — formato exacto de asunto/cuerpo esperado.

## Estado

Creado localmente, sin remote todavía. Pendiente: GitHub user de David para
agregar `origin` y push de la rama inicial.

# Setup en una PC nueva (owner remoto)

1. Instalar Hermes (mismo runtime que ConsuConstruct usa).
2. Clonar este repo.
3. Copiar `profiles/devops_bot/` y `profiles/reviewer/` a la carpeta de
   perfiles Hermes de esa máquina (ej. `D:/Agents/devops_bot`,
   `D:/Agents/reviewer` o equivalente en su OS).
4. Configurar credenciales de correo propias (variables de entorno o
   `.env` del perfil, NUNCA committeadas a este repo):
   - `MAIL_IMAP_HOST`, `MAIL_IMAP_USER`, `MAIL_IMAP_PASS`
   - `MAIL_SMTP_HOST`, `MAIL_SMTP_USER`, `MAIL_SMTP_PASS`
5. Si quieren RAG local, instalar su propio Postgres y correr las
   migraciones mínimas de `rag/` (pendiente de extraer; por ahora no
   incluidas — este kit no trae esquema de brain.* de ConsuConstruct).
6. `git checkout -b <owner>/<primera-tarea>` antes de tocar nada — nunca
   trabajar directo en `main`.
7. Avisar a David por correo (`[REPORT]`) cuando el setup esté verificado
   (ej. un commit de prueba en su rama, un correo de ida y vuelta real).

## Qué NO viene en este repo (decisión deliberada)

- Nada de `brain.*` SQL, nada de `agent_run_events`, nada del MCP SSE de
  ConsuConstruct — ese Postgres y ese bus son privados de ConsuConstruct.
- Ningún secreto ni credencial real.
- Ningún dato de clientes/proyectos de ConsuConstruct.

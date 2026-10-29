# MCP server lite — setup

Servidor MCP propio, catálogo de runtime **de comunicación** (lo más usado
y necesario para operar devops_bot+reviewer entre PCs), sin NADA de dominio
de ConsuConstruct (sin HUD, Blender, ETABS, voz, CRM, EstimaStruct). Sin
NINGUNA dependencia del repo/Postgres de ConsuConstruct.

## Tools expuestas (12)

**Bus / comunicación entre agentes:**
- `agent_send(from_role, to_role, summary, goal_id=None, message_type="task")`
- `agent_inbox(role_key, pending_only=True, limit=20)`
- `agent_reply(message_id, content, from_role=None)`
- `live_sessions(heartbeat_window_minutes=20)` — quién estuvo activo recientemente
- `get_loop_state(goal_id, events=6)` — estado de un goal + últimos eventos del bus
- `team_directory(active_only=True)` — roster de agentes (role_key, uuid, modelo)

**Postgres (whitelisteado a `brain.*`):**
- `pg_select(sql, limit=100)` — SELECT/WITH de solo lectura
- `pg_insert(schema, table, values, id_col="id")`
- `pg_update(schema, table, id_col, id, patch)`

**Notas locales (propio de esta instalación, nunca el vault de ConsuConstruct):**
- `write_md(note_path, content, create=True)` — en `./notes/`
- `edit_md(note_path, title, body)` — anexa sección numerada

**RAG local:**
- `rag_search(query, limit=5)` — pgvector + Ollama `nomic-embed-text`

## Instalar

```
cd mcp_server
pip install -r requirements.txt
```

## Preparar Postgres (propio de esta PC, vacío)

1. Instalar PostgreSQL local (o usar uno ya existente, dedicado a este bus).
2. Instalar la extensión `pgvector` en esa instancia (paquete
   `postgresql-<version>-pgvector` o compilar desde
   https://github.com/pgvector/pgvector).
3. `psql <tu_dsn> -f ../sql/001_brain_bus_minimal.sql`
4. Exportar `DATABASE_URL=postgresql://user:***@localhost:5432/dbname`.

## Preparar Ollama (embeddings locales, para rag_search)

1. Instalar Ollama (https://ollama.com).
2. `ollama pull nomic-embed-text`
3. Confirmar que responde:
   `curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"hola"}'`
4. Si Ollama corre en otro host/puerto, exportar `OLLAMA_URL`.

## Correr

```
export MCP_LITE_TOKEN=$(python -c "import secrets; print(secrets.token_hex(32))")
python mcp_lite_server.py --transport sse --port 24425
```

**El token es obligatorio** para `--transport sse` — sin `MCP_LITE_TOKEN` el
proceso se niega a arrancar. Guardar el token y compartirlo UNA vez con
ConsuConstruct por un canal seguro (nunca por el repo ni por chat en texto
plano permanente) — lo necesitan para su lado del `config.yaml`.

Puerto **24425** (no 24424) a propósito, para no colisionar si alguna vez
corre en la misma red que el MCP real de ConsuConstruct.

## Exponer el puerto a ConsuConstruct — Tailscale (recomendado)

No abrir el puerto 24425 a internet público. Usar una red privada:

1. Instalar Tailscale (https://tailscale.com) en esta PC y en la PC de
   ConsuConstruct que se va a conectar.
2. `tailscale up` en ambas, autenticando con la misma cuenta/tailnet.
3. Confirmar la IP de Tailscale de esta PC: `tailscale ip -4` (algo como
   `100.x.x.x`).
4. Correr el server bindeado a esa interfaz (o a `0.0.0.0`, que ya es el
   default — Tailscale igual solo lo hace alcanzable desde el tailnet, no
   desde internet, mientras el firewall local no abra 24425 a la LAN/WAN).
5. Compartir la IP de Tailscale (no el token, eso aparte) con ConsuConstruct
   para que la agregue a su `config.yaml`.

## Registrar en el perfil Hermes

En `config.yaml` del perfil (`devops_bot`/`reviewer` de esta PC, o del lado
de ConsuConstruct que se conecta a ESTE server):

```yaml
mcp_servers:
  brain-control-lite:
    enabled: true
    transport: sse
    url: http://<ip-tailscale-de-esta-pc>:24425/sse
    headers:
      X-MCP-Lite-Token: "<el mismo MCP_LITE_TOKEN exportado arriba>"
    tools:
      include:
        - agent_send
        - agent_inbox
        - agent_reply
        - live_sessions
        - get_loop_state
        - team_directory
        - pg_select
        - pg_insert
        - pg_update
        - write_md
        - edit_md
        - rag_search
```

## Crear la identidad de un agente (UUID)

Un agente nuevo se registra UNA vez en `brain.agent_identities`:

```sql
INSERT INTO brain.agent_identities (role_key, model)
VALUES ('devops_bot', 'nombre-del-modelo-usado')
ON CONFLICT (role_key) DO NOTHING;
```

El `agent_uuid` se genera solo (`gen_random_uuid()`), igual que en el
sistema real de ConsuConstruct.

## Pendiente de integrar (fuera de este setup)

- `scripts/mail_bus.py` (ver `../scripts/`) como transporte complementario
  para que el centro de mando (ConsuConstruct) reciba avisos por correo
  cuando haya actividad en este bus, sin necesitar acceso directo a este
  Postgres.
- Session chunker: script que lea las sesiones de Hermes de esta PC y las
  indexe en `brain.agent_memory_chunks` vía `_ollama_embed` — pendiente de
  escribir, adaptando el patrón del chunker real de ConsuConstruct.
- Plugin de memoria de Hermes (`memory_context` hook) apuntando a este
  mismo Postgres — es config pura, no requiere código nuevo.

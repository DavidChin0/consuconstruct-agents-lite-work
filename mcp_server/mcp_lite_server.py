#!/usr/bin/env python3
"""
mcp_lite_server.py — Catalogo de runtime MINIMO, propio, SIN ninguna
dependencia del repo/Postgres de ConsuConstruct. Solo lo mas usado y
necesario para operar devops_bot+reviewer clonados; nada de dominio
(sin HUD, sin Blender, sin ETABS, sin voz, sin CRM). Tools (transporte SSE):

    agent_send(from_role, to_role, summary, goal_id=None, message_type="task")
    agent_inbox(role_key, pending_only=True, limit=20)
    agent_reply(message_id, content, from_role=None)
    pg_select(sql, limit=100)      -- SELECT/WITH de solo lectura
    pg_insert(schema, table, values, id_col="id")   -- whitelisteado a brain.*
    pg_update(schema, table, id_col, id, patch)      -- whitelisteado a brain.*
    team_directory(active_only=True)                 -- lee brain.agent_identities
    rag_search(query, limit=5)     -- pgvector + Ollama nomic-embed-text local

Requiere Postgres PROPIO (no el de ConsuConstruct) con el esquema de
sql/001_brain_bus_minimal.sql ya aplicado, y Ollama local corriendo
nomic-embed-text para rag_search.

Config via variables de entorno:
    DATABASE_URL   (postgresql://user:***@host:port/dbname)
    MCP_LITE_PORT  (default 24425 -- distinto del 24424 de ConsuConstruct)
    OLLAMA_URL     (default http://localhost:11434)

Uso:
    python mcp_lite_server.py --transport sse --port 24425
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

import asyncpg
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("brain-control-lite")

# Tablas en las que pg_insert/pg_update pueden escribir. Todo lo demas se
# rechaza — mismo principio que el pg_insert/pg_update reales de ConsuConstruct.
_WRITE_WHITELIST = {
    ("brain", "goals"),
    ("brain", "agent_run_events"),
    ("brain", "agent_identities"),
}

_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError("Falta DATABASE_URL en el entorno")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
    return _pool


_SELECT_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


@mcp.tool()
async def agent_send(
    from_role: str,
    to_role: str,
    summary: str,
    goal_id: int | None = None,
    message_type: str = "task",
) -> dict:
    """Persiste un mensaje inter-agente. Si no hay goal_id, crea un goal nuevo
    asignado a to_role (goal-first), igual que el bus canonico."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if goal_id is None:
                goal_id = await conn.fetchval(
                    "INSERT INTO brain.goals (goal, assigned_role_key) "
                    "VALUES ($1, $2) RETURNING id",
                    summary,
                    to_role,
                )
            usage = {"from_role": from_role, "to_role": to_role, "message_type": message_type}
            msg_id = await conn.fetchval(
                "INSERT INTO brain.agent_run_events (event_type, goal_id, content, usage) "
                "VALUES ('agent_message', $1, $2, $3::jsonb) RETURNING id",
                goal_id,
                summary,
                json.dumps(usage),
            )
    return {"ok": True, "message_id": msg_id, "goal_id": goal_id}


@mcp.tool()
async def agent_inbox(role_key: str, pending_only: bool = True, limit: int = 20) -> dict:
    """Lista mensajes dirigidos a role_key. pending_only=True excluye los que
    ya tienen un agent_reply enlazado (reply_to)."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        if pending_only:
            rows = await conn.fetch(
                """
                SELECT e.id, e.goal_id, e.content, e.created_at
                FROM brain.agent_run_events e
                WHERE e.event_type = 'agent_message'
                  AND e.usage->>'to_role' = $1
                  AND NOT EXISTS (
                      SELECT 1 FROM brain.agent_run_events r
                      WHERE r.event_type = 'agent_reply'
                        AND r.usage->>'reply_to' = e.id::text
                  )
                ORDER BY e.id DESC LIMIT $2
                """,
                role_key,
                limit,
            )
        else:
            rows = await conn.fetch(
                "SELECT id, goal_id, content, created_at FROM brain.agent_run_events "
                "WHERE event_type='agent_message' AND usage->>'to_role'=$1 "
                "ORDER BY id DESC LIMIT $2",
                role_key,
                limit,
            )
    return {"ok": True, "messages": [dict(r) for r in rows]}


@mcp.tool()
async def agent_reply(message_id: int, content: str, from_role: str | None = None) -> dict:
    """Responde a un mensaje, enlazado por reply_to (unica senal de cierre)."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT goal_id, usage->>'from_role' as orig_from FROM brain.agent_run_events WHERE id=$1",
            message_id,
        )
        if row is None:
            return {"ok": False, "error": f"message_id {message_id} no existe"}
        usage = {"reply_to": str(message_id), "from_role": from_role or row["orig_from"]}
        reply_id = await conn.fetchval(
            "INSERT INTO brain.agent_run_events (event_type, goal_id, content, usage) "
            "VALUES ('agent_reply', $1, $2, $3::jsonb) RETURNING id",
            row["goal_id"],
            content,
            json.dumps(usage),
        )
    return {"ok": True, "reply_id": reply_id, "reply_to": message_id}


@mcp.tool()
async def pg_select(sql: str, limit: int = 100) -> dict:
    """SELECT/WITH de solo lectura sobre brain.*. Rechaza cualquier otra cosa."""
    if not _SELECT_RE.match(sql):
        return {"ok": False, "error": "Solo se permite SELECT/WITH"}
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
    rows = rows[:limit]
    return {"ok": True, "rows": [dict(r) for r in rows], "count": len(rows)}


def _check_write_target(schema: str, table: str) -> dict | None:
    if not _IDENT_RE.match(schema) or not _IDENT_RE.match(table):
        return {"ok": False, "error": "schema/table con caracteres invalidos"}
    if (schema, table) not in _WRITE_WHITELIST:
        return {"ok": False, "error": f"{schema}.{table} no esta en la whitelist de escritura"}
    return None


@mcp.tool()
async def pg_insert(schema: str, table: str, values: dict, id_col: str = "id") -> dict:
    """INSERT de una fila en una tabla whitelisteada de brain.*, devuelve el id_col."""
    err = _check_write_target(schema, table)
    if err:
        return err
    cols = list(values.keys())
    if not all(_IDENT_RE.match(c) for c in cols):
        return {"ok": False, "error": "nombre de columna invalido"}
    placeholders = ", ".join(f"${i+1}" for i in range(len(cols)))
    col_list = ", ".join(cols)
    sql = (
        f"INSERT INTO {schema}.{table} ({col_list}) VALUES ({placeholders}) "
        f"RETURNING {id_col}"
    )
    pool = await _get_pool()
    async with pool.acquire() as conn:
        new_id = await conn.fetchval(sql, *values.values())
    return {"ok": True, "id": new_id}


@mcp.tool()
async def pg_update(schema: str, table: str, id_col: str, id: int, patch: dict) -> dict:
    """UPDATE de una fila por id_col=id en una tabla whitelisteada de brain.*."""
    err = _check_write_target(schema, table)
    if err:
        return err
    cols = list(patch.keys())
    if not all(_IDENT_RE.match(c) for c in cols):
        return {"ok": False, "error": "nombre de columna invalido"}
    if not _IDENT_RE.match(id_col):
        return {"ok": False, "error": "id_col invalido"}
    set_clause = ", ".join(f"{c} = ${i+2}" for i, c in enumerate(cols))
    sql = f"UPDATE {schema}.{table} SET {set_clause} WHERE {id_col} = $1"
    pool = await _get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(sql, id, *patch.values())
    rowcount = int(result.split()[-1]) if result else 0
    if rowcount == 0:
        return {"ok": False, "error": f"0 filas afectadas para {id_col}={id}"}
    return {"ok": True, "rowcount": rowcount}


@mcp.tool()
async def team_directory(active_only: bool = True) -> dict:
    """Lista agentes (role_key, uuid, modelo) desde brain.agent_identities."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT to_regclass('brain.agent_identities') IS NOT NULL"
        )
        if not exists:
            return {"ok": True, "agents": [], "note": "brain.agent_identities no existe aun"}
        where = "WHERE active = true" if active_only else ""
        rows = await conn.fetch(f"SELECT role_key, agent_uuid, model FROM brain.agent_identities {where}")
    return {"ok": True, "agents": [dict(r) for r in rows]}


def _ollama_embed(text: str) -> list[float]:
    """Pide un embedding a Ollama local (nomic-embed-text). Sin libreria HTTP
    extra: urllib stdlib alcanza para un POST simple."""
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embeddings"
    body = json.dumps({"model": "nomic-embed-text", "prompt": text}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["embedding"]


@mcp.tool()
async def rag_search(query: str, limit: int = 5) -> dict:
    """Busqueda semantica sobre brain.agent_memory_chunks (pgvector) usando
    embeddings de Ollama nomic-embed-text, generados localmente."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT to_regclass('brain.agent_memory_chunks') IS NOT NULL"
        )
        if not exists:
            return {"ok": True, "chunks": [], "note": "brain.agent_memory_chunks no existe aun"}
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(None, _ollama_embed, query)
        rows = await conn.fetch(
            "SELECT id, content, 1 - (embedding <=> $1::vector) AS similarity "
            "FROM brain.agent_memory_chunks ORDER BY embedding <=> $1::vector LIMIT $2",
            str(embedding),
            limit,
        )
    return {"ok": True, "chunks": [dict(r) for r in rows]}


@mcp.tool()
async def live_sessions(heartbeat_window_minutes: int = 20) -> dict:
    """Agentes con heartbeat reciente, segun brain.agent_identities (si una
    columna last_heartbeat existe) y actividad reciente en agent_run_events."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT usage->>'from_role' AS role_key, max(created_at) AS last_seen
            FROM brain.agent_run_events
            WHERE created_at > now() - ($1 || ' minutes')::interval
            GROUP BY usage->>'from_role'
            ORDER BY last_seen DESC
            """,
            str(heartbeat_window_minutes),
        )
    return {"ok": True, "live": [dict(r) for r in rows]}


@mcp.tool()
async def get_loop_state(goal_id: int, events: int = 6) -> dict:
    """Estado de un goal: fila de brain.goals + ultimos eventos del bus."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        goal = await conn.fetchrow("SELECT * FROM brain.goals WHERE id = $1", goal_id)
        if goal is None:
            return {"ok": False, "error": f"goal {goal_id} no existe"}
        bus = await conn.fetch(
            "SELECT id, event_type, usage->>'from_role' AS from_role, "
            "usage->>'to_role' AS to_role, content, created_at "
            "FROM brain.agent_run_events WHERE goal_id = $1 "
            "ORDER BY id DESC LIMIT $2",
            goal_id,
            events,
        )
    return {"ok": True, "goal": dict(goal), "bus_last": [dict(r) for r in bus]}


# Las notas .md de este kit viven en ./notes/ (relativo a este archivo), NO en
# el vault de Obsidian de ConsuConstruct — cada instalacion tiene su propio
# espacio de notas local, sin mezclar con el vault real.
_NOTES_DIR = Path(__file__).resolve().parent / "notes"


def _safe_note_path(note_path: str) -> Path:
    target = (_NOTES_DIR / note_path).resolve()
    if _NOTES_DIR.resolve() not in target.parents and target != _NOTES_DIR.resolve():
        raise ValueError("note_path se sale de ./notes/")
    return target


@mcp.tool()
async def write_md(note_path: str, content: str, create: bool = True) -> dict:
    """Escribe/crea una nota .md local en ./notes/ (propio de esta instalacion,
    nunca el vault de ConsuConstruct)."""
    target = _safe_note_path(note_path)
    if not create and not target.exists():
        return {"ok": False, "error": f"{note_path} no existe y create=False"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(target)}


@mcp.tool()
async def edit_md(note_path: str, title: str, body: str) -> dict:
    """Anexa una seccion numerada al final de una nota .md local en ./notes/."""
    target = _safe_note_path(note_path)
    if not target.exists():
        return {"ok": False, "error": f"{note_path} no existe; usa write_md primero"}
    existing = target.read_text(encoding="utf-8")
    section_n = existing.count("\n# ") + existing.count("\n## ") + 1
    addendum = f"\n\n# {section_n}. {title}\n\n{body}\n"
    target.write_text(existing + addendum, encoding="utf-8")
    return {"ok": True, "path": str(target), "section": section_n}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="sse", choices=["sse", "stdio"])
    parser.add_argument("--port", type=int, default=int(os.environ.get("MCP_LITE_PORT", "24425")))
    args = parser.parse_args()

    if args.transport == "sse":
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

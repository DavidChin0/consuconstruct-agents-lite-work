#!/usr/bin/env python3
"""Hook SessionEnd/PreCompact (Claude Code): chunker de sesion.

Lee el transcript JSONL (payload del hook: transcript_path, session_id), arma
trozos de turnos humano/asistente, calcula embeddings con Ollama
(nomic-embed-text) y los guarda en brain.agent_memory_chunks. Sin LLM.

Env: DATABASE_URL, MCP_LITE_ROLE (role_key), OLLAMA_URL (default localhost:11434).
No bloquea el cierre: ante cualquier error sale 0 y deja el motivo en stderr.
Sesiones triviales (<2 turnos humanos) no se guardan.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import urllib.request

CHUNK_CHARS = 1500
MAX_CHUNKS = 40


def _turns(path: str) -> list[str]:
    turns: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("isSidechain") or ev.get("isMeta") or ev.get("type") not in ("user", "assistant"):
                continue
            content = (ev.get("message") or {}).get("content")
            if isinstance(content, list):
                content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            if isinstance(content, str) and content.strip():
                turns.append(f"{ev['type']}: {content.strip()}")
    return turns


def _chunks(turns: list[str]) -> list[str]:
    out, cur = [], ""
    for t in turns:
        if cur and len(cur) + len(t) > CHUNK_CHARS:
            out.append(cur)
            cur = ""
        cur += t[:CHUNK_CHARS] + "\n"
    if cur:
        out.append(cur)
    return out[-MAX_CHUNKS:]


def _embed(text: str) -> list[float]:
    req = urllib.request.Request(
        os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/api/embeddings",
        data=json.dumps({"model": "nomic-embed-text", "prompt": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["embedding"]


async def _store(role: str, session_id: str, chunks: list[str]) -> None:
    import asyncpg

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute("DELETE FROM brain.agent_memory_chunks WHERE source_session_id=$1", session_id)
        for c in chunks:
            vec = "[" + ",".join(f"{x:.6f}" for x in _embed(c)) + "]"
            await conn.execute(
                "INSERT INTO brain.agent_memory_chunks (role_key, content, embedding, source_session_id) "
                "VALUES ($1,$2,$3::vector,$4)", role, c, vec, session_id)
    finally:
        await conn.close()


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        turns = _turns(payload["transcript_path"])
        if sum(t.startswith("user:") for t in turns) < 2:
            return
        asyncio.run(_store(os.environ.get("MCP_LITE_ROLE", "unknown"),
                           payload.get("session_id", "unknown"), _chunks(turns)))
    except Exception as exc:  # el hook nunca debe trabar el cierre
        print(f"[session_close] {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()

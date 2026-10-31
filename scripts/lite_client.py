"""lite_client.py — cliente minimo del MCP lite (SSE + token del rol).

Env: MCP_LITE_URL, MCP_LITE_TOKEN. Uso:  result = asyncio.run(call("tool", {...}))
"""
from __future__ import annotations

import json
import os


async def call(tool: str, arguments: dict | None = None) -> dict:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url, token = os.environ.get("MCP_LITE_URL"), os.environ.get("MCP_LITE_TOKEN")
    if not (url and token):
        raise SystemExit("Faltan MCP_LITE_URL o MCP_LITE_TOKEN")
    async with sse_client(url, headers={"X-MCP-Lite-Token": token}) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            res = await session.call_tool(tool, arguments or {})
    for block in res.content or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"ok": False, "error": text[:300]}
    return {"ok": False, "error": "respuesta vacia"}

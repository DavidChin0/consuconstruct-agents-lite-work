#!/usr/bin/env python3
"""Verifica la instalacion local de identity-tokens. Sale 0 solo si todo pasa."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
fails = []


def check(name: str, ok: bool, hint: str = "") -> None:
    print(("OK   " if ok else "FALLA"), name, ("" if ok else f"-> {hint}"))
    if not ok:
        fails.append(name)


for var in ("MCP_LITE_URL", "MCP_LITE_TOKEN", "MCP_LITE_ROLE"):
    check(f"variable {var}", bool(os.environ.get(var)), "definirla (INSTALL.md B.2)")
for rel in ("mcp_server/policy.py", "scripts/inbox_listener.py", "scripts/update_trigger.py",
            "profiles/claude_reviewer/SOUL.md"):
    check(f"archivo {rel}", (ROOT / rel).exists(), "git pull")
r = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=ROOT, capture_output=True, text=True)
check("tests de policy", r.returncode == 0, r.stderr[-200:])

if os.environ.get("MCP_LITE_URL") and os.environ.get("MCP_LITE_TOKEN"):
    sys.path.insert(0, str(ROOT / "scripts"))
    import asyncio

    import lite_client

    try:
        res = asyncio.run(lite_client.call("heartbeat"))
        check("heartbeat contra el servidor (token valido)", bool(res.get("ok")), str(res.get("error")))
    except Exception as exc:
        check("conexion al servidor", False, str(exc)[:150])

print("\nRESULTADO:", "OK" if not fails else f"{len(fails)} falla(s)")
sys.exit(1 if fails else 0)

#!/usr/bin/env python3
"""inbox_listener.py — listener SOLO DE NOTIFICACION para Dane/Hector.

Cada N segundos consulta agent_inbox por el MCP lite con el token de este
rol. Por cada mensaje nuevo: lo anota en inbox/pending.md, lanza una
notificacion local y llama agent_ack. NO ejecuta nada: el agente (o la
persona) decide si toma el mensaje y responde con agent_reply.

    MCP_LITE_URL=http://100.x.x.x:24425/sse MCP_LITE_TOKEN=<tu token> \
    MCP_LITE_ROLE=claude_dane python scripts/inbox_listener.py
    python scripts/inbox_listener.py --selftest-notify    # prueba la notificacion
    python scripts/inbox_listener.py --once               # una vuelta y sale

Mantenerlo vivo: scripts/install_listener.ps1 (Windows, tarea programada) o
systemd --user / cron @reboot en Linux/Mac. Lockfile evita duplicados.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INBOX_DIR = ROOT / "inbox"
PENDING = INBOX_DIR / "pending.md"
LOCK = INBOX_DIR / "listener.lock"
MAX_BODY = 400  # recorte para notificacion/pending; el mensaje completo vive en el bus


def notify(title: str, body: str) -> None:
    """Toast local. El texto viaja por variables de entorno, nunca interpolado
    en el comando, para que un mensaje no pueda inyectar codigo."""
    env = {**os.environ, "NOTIF_TITLE": title[:80], "NOTIF_BODY": body[:MAX_BODY]}
    try:
        if sys.platform == "win32":
            ps = (
                "[void][Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime];"
                "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent('ToastText02');"
                "$t=$x.GetElementsByTagName('text');"
                "[void]$t.Item(0).AppendChild($x.CreateTextNode($env:NOTIF_TITLE));"
                "[void]$t.Item(1).AppendChild($x.CreateTextNode($env:NOTIF_BODY));"
                "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
                "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('consuconstruct-lite').Show($n)"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], env=env, timeout=15, check=True,
                           capture_output=True)
        elif sys.platform == "darwin":
            subprocess.run(["osascript", "-e",
                            'display notification (system attribute "NOTIF_BODY") with title (system attribute "NOTIF_TITLE")'],
                           env=env, timeout=15, check=True)
        else:
            subprocess.run(["notify-send", title[:80], body[:MAX_BODY]], timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[listener] notificacion fallo ({exc}); {title}: {body}", file=sys.stderr)


def _parse(result) -> dict:
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"ok": False, "error": text[:200]}
    return {"ok": False, "error": "respuesta vacia"}


def _append_pending(msg: dict) -> None:
    INBOX_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (msg.get("content") or "").strip()
    entry = (
        f"\n## #{msg['id']} · de {msg.get('from_role') or '?'} · {msg.get('message_type') or 'task'} · {stamp}\n\n"
        f"{body}\n\nResponder: agent_reply(message_id={msg['id']}, content=...)\n"
    )
    with PENDING.open("a", encoding="utf-8") as fh:
        fh.write(entry)


def _pid_alive(pid: int) -> bool:
    """Sin os.kill: en Windows os.kill(pid, 0) envia CTRL_C_EVENT y puede matar procesos."""
    if sys.platform == "win32":
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _acquire_lock() -> None:
    INBOX_DIR.mkdir(exist_ok=True)
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().strip())
        except ValueError:
            pid = 0  # lock huerfano
        if pid and pid != os.getpid() and _pid_alive(pid):
            raise SystemExit(f"listener ya corre (pid {pid})")
    LOCK.write_text(str(os.getpid()))


async def poll_once(session, role: str, seen: set[int]) -> int:
    res = _parse(await session.call_tool("agent_inbox", {"role_key": role, "pending_only": True, "limit": 20}))
    if not res.get("ok"):
        print(f"[listener] inbox error: {res.get('error')}", file=sys.stderr)
        return 0
    fresh = [m for m in reversed(res["messages"]) if m["id"] not in seen and not m.get("acked")]
    for msg in fresh:
        _append_pending(msg)
        notify(f"Mensaje de {msg.get('from_role') or '?'} (#{msg['id']})", (msg.get("content") or "")[:MAX_BODY])
        ack = _parse(await session.call_tool("agent_ack", {"message_id": msg["id"]}))
        if ack.get("ok"):
            seen.add(msg["id"])
    await session.call_tool("heartbeat", {})
    return len(fresh)


async def run(args: argparse.Namespace) -> None:
    from mcp import ClientSession
    from mcp.client.sse import sse_client

    url = os.environ.get("MCP_LITE_URL")
    token = os.environ.get("MCP_LITE_TOKEN")
    role = os.environ.get("MCP_LITE_ROLE")
    if not (url and token and role):
        raise SystemExit("Faltan MCP_LITE_URL, MCP_LITE_TOKEN o MCP_LITE_ROLE")
    seen: set[int] = set()
    backoff = 5
    while True:
        try:
            async with sse_client(url, headers={"X-MCP-Lite-Token": token}) as (r, w):
                async with ClientSession(r, w) as session:
                    await session.initialize()
                    backoff = 5
                    while True:
                        await poll_once(session, role, seen)
                        if args.once:
                            return
                        await asyncio.sleep(args.interval)
        except Exception as exc:  # red caida: reintento con backoff, no muere
            if args.once:
                raise
            print(f"[listener] conexion perdida: {exc}; reintento en {backoff}s", file=sys.stderr)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 120)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=20)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--selftest-notify", action="store_true")
    args = ap.parse_args()
    if args.selftest_notify:
        notify("consuconstruct-lite", "Prueba de notificacion: el listener puede avisarte.")
        print("notificacion enviada")
        return
    _acquire_lock()
    try:
        asyncio.run(run(args))
    finally:
        LOCK.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

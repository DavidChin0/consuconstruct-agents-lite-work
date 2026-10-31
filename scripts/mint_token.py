#!/usr/bin/env python3
"""mint_token.py — emite un token por rol para el MCP lite.

Guarda solo el sha256 en brain.mcp_tokens; el token en claro se imprime UNA
vez. Entregarlo por canal seguro, nunca por el repo ni por correo en claro.

    DATABASE_URL=postgresql://... python scripts/mint_token.py --role claude_dane --label "PC Dane"
    python scripts/mint_token.py --revoke-role claude_dane
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp_server"))
import policy  # noqa: E402


async def run(args: argparse.Namespace) -> None:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Falta DATABASE_URL")
    conn = await asyncpg.connect(dsn)
    try:
        if args.revoke_role:
            res = await conn.execute(
                "UPDATE brain.mcp_tokens SET active=false WHERE role_key=$1 AND active", args.revoke_role
            )
            print(f"revocados: {res}")
            return
        if args.role not in policy.ALL_ROLES:
            raise SystemExit(f"rol invalido; validos: {', '.join(sorted(policy.ALL_ROLES))}")
        token = secrets.token_hex(32)
        await conn.execute(
            "INSERT INTO brain.mcp_tokens (token_hash, role_key, label) VALUES ($1,$2,$3)",
            policy.hash_token(token),
            args.role,
            args.label,
        )
        print(f"rol={args.role}\ntoken={token}\n(guardalo ahora: no se vuelve a mostrar)")
    finally:
        await conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role")
    ap.add_argument("--label", default="")
    ap.add_argument("--revoke-role")
    args = ap.parse_args()
    if not args.role and not args.revoke_role:
        ap.error("--role o --revoke-role")
    asyncio.run(run(args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""verify_approval.py — gate: sale con codigo 0 solo si el commit tiene APPROVE.

    python scripts/verify_approval.py --repo consuconstruct-agents-lite --sha HEAD

Instalar como pre-push:  scripts/hooks/pre-push  (copiar a .git/hooks/pre-push).
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lite_client  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sha", default="HEAD")
    args = ap.parse_args()
    sha = subprocess.run(["git", "rev-parse", args.sha], capture_output=True, text=True, check=True).stdout.strip()
    res = asyncio.run(lite_client.call("commit_approval", {"repo": args.repo, "commit_sha": sha}))
    appr = res.get("approval") if res.get("ok") else None
    if appr and appr["verdict"] == "APPROVE":
        print(f"OK {sha[:12]} aprobado por {appr['reviewer']}")
        sys.exit(0)
    print(f"BLOQUEADO {sha[:12]}: {'sin veredicto' if not appr else appr['verdict']} "
          f"(pedir review_request y esperar APPROVE)", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()

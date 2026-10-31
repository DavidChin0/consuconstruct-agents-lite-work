#!/usr/bin/env python3
"""update_trigger.py — disparador de updates de esta instalacion.

Las novedades viven en updates/<AAAA-MM-DD>_<slug>/ (INSTALL.md, CHANGES.md,
verify.py). updates/LATEST dice cual es la ultima. El estado local de lo ya
aplicado esta en updates/.applied (ignorado por git).

  python scripts/update_trigger.py --check          # git fetch + lista lo pendiente (solo avisa)
  python scripts/update_trigger.py --notify         # igual, y manda notificacion si hay algo
  python scripts/update_trigger.py --show <carpeta> # imprime INSTALL.md
  python scripts/update_trigger.py --apply          # pide OK por cada update pendiente, corre su
                                                    # verify.py y lo marca aplicado

Nunca aplica solo: --apply pregunta antes de cada update. El INSTALL.md lo
ejecuta una persona o su agente; este script solo verifica y registra.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATES = ROOT / "updates"
APPLIED = UPDATES / ".applied"


def _applied() -> set[str]:
    return set(APPLIED.read_text(encoding="utf-8").split()) if APPLIED.exists() else set()


def _fetch() -> None:
    subprocess.run(["git", "-C", str(ROOT), "fetch", "--quiet", "origin"], capture_output=True, timeout=60)


def _upstream_updates() -> list[str]:
    """Carpetas en origin/main:updates/ aun no presentes en el arbol local."""
    r = subprocess.run(["git", "-C", str(ROOT), "ls-tree", "--name-only", "origin/main", "updates/"],
                       capture_output=True, text=True)
    return sorted(Path(p).name for p in r.stdout.split() if Path(p).name[:4].isdigit())


def pending() -> tuple[list[str], list[str]]:
    local = sorted(p.name for p in UPDATES.iterdir() if p.is_dir() and p.name[:4].isdigit()) if UPDATES.exists() else []
    not_applied = [n for n in local if n not in _applied()]
    not_pulled = [n for n in _upstream_updates() if n not in local]
    return not_applied, not_pulled


def report() -> str:
    not_applied, not_pulled = pending()
    lines = []
    if not_pulled:
        lines.append("Updates nuevos en origin/main (haz `git pull` de main a tu rama): " + ", ".join(not_pulled))
    if not_applied:
        lines.append("Updates sin aplicar: " + ", ".join(not_applied)
                     + "  -> update_trigger.py --show <carpeta> / --apply")
    return "\n".join(lines) or "al dia"


def apply() -> int:
    for name in pending()[0]:
        d = UPDATES / name
        print(f"\n=== {name} ===\n{(d / 'INSTALL.md').read_text(encoding='utf-8')}")
        if input(f"¿Ya hiciste los pasos de {name}? Correr verify.py ahora [s/N] ").strip().lower() != "s":
            print("saltado")
            continue
        v = d / "verify.py"
        if v.exists() and subprocess.run([sys.executable, str(v)]).returncode != 0:
            print(f"verify.py fallo; {name} NO queda marcado como aplicado")
            return 1
        with APPLIED.open("a", encoding="utf-8") as fh:
            fh.write(name + "\n")
        print(f"{name} aplicado")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if args.show:
        print((UPDATES / args.show / "INSTALL.md").read_text(encoding="utf-8"))
    elif args.apply:
        sys.exit(apply())
    else:
        if args.check or args.notify:
            _fetch()
        out = report()
        print(out)
        if args.notify and out != "al dia":
            sys.path.insert(0, str(ROOT / "scripts"))
            from inbox_listener import notify
            notify("Updates disponibles", out)


if __name__ == "__main__":
    main()

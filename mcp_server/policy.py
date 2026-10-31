"""policy.py — identidad y permisos por rol del MCP lite (sin I/O, testeable).

El rol sale del token del header, nunca de un argumento del modelo.
"""
from __future__ import annotations

import hashlib
import re

ORCHESTRATOR = "claude_code"
REVIEWER = "claude_reviewer"
MANAGERS = frozenset({"claude_dane", "codex_hector"})
WORKERS = frozenset({"devops_bot", "reviewer"})
ALL_ROLES = frozenset({ORCHESTRATOR, REVIEWER}) | MANAGERS | WORKERS

# A quien puede mandar cada rol con agent_send. None = cualquiera.
_SEND_TARGETS: dict[str, frozenset[str] | None] = {
    ORCHESTRATOR: None,
    "claude_dane": ALL_ROLES - {"claude_dane"},
    "codex_hector": ALL_ROLES - {"codex_hector"},
    REVIEWER: frozenset({ORCHESTRATOR}) | MANAGERS,
    "devops_bot": frozenset({ORCHESTRATOR, REVIEWER, "reviewer"}) | MANAGERS,
    "reviewer": frozenset({ORCHESTRATOR, "devops_bot"}) | MANAGERS,
}

VERDICTS = frozenset({"APPROVE", "REJECT"})
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_WRITE_WORDS = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|do|vacuum)\b",
    re.IGNORECASE,
)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def can_send(caller: str, to_role: str) -> bool:
    if caller not in _SEND_TARGETS or to_role not in ALL_ROLES:
        return False
    targets = _SEND_TARGETS[caller]
    return targets is None or to_role in targets


def can_write_pg(caller: str) -> bool:
    """Managers piden por goals/mensajes; no escriben tablas directo."""
    return caller == ORCHESTRATOR


def can_read_inbox(caller: str, role_key: str) -> bool:
    return caller == role_key or caller == ORCHESTRATOR


def can_give_verdict(caller: str) -> bool:
    return caller == REVIEWER


def valid_sha(sha: str) -> bool:
    return bool(_SHA_RE.match(sha or ""))


def select_is_safe(sql: str, caller: str) -> str | None:
    """None si el SELECT es aceptable; si no, el motivo del rechazo."""
    if ";" in sql.strip().rstrip(";"):
        return "una sola sentencia"
    if _WRITE_WORDS.search(sql):
        return "palabra de escritura no permitida"
    if "mcp_tokens" in sql.lower() and caller != ORCHESTRATOR:
        return "mcp_tokens solo lo lee claude_code"
    return None


def sha_matches(stored: str, query: str) -> bool:
    """Un sha corto y uno largo del mismo commit cuentan como igual (prefijo, min 7)."""
    if not (valid_sha(stored) and valid_sha(query)):
        return False
    a, b = stored.lower(), query.lower()
    return a.startswith(b) or b.startswith(a)

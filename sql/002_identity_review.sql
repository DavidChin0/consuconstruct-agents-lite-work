-- Identidad por token, heartbeat y aprobacion de commits (feature/identity-tokens).
-- Idempotente. Correr despues de 001_brain_bus_minimal.sql.

CREATE TABLE IF NOT EXISTS brain.mcp_tokens (
    token_hash TEXT PRIMARY KEY,           -- sha256 hex; el token en claro nunca se guarda
    role_key   TEXT NOT NULL,
    label      TEXT,
    active     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE brain.agent_identities ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS brain.commit_approvals (
    id         BIGSERIAL PRIMARY KEY,
    commit_sha TEXT NOT NULL,
    repo       TEXT NOT NULL,
    verdict    TEXT NOT NULL CHECK (verdict IN ('APPROVE','REJECT')),
    reviewer   TEXT NOT NULL,
    requester  TEXT NOT NULL,
    evidence   TEXT NOT NULL,
    request_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (reviewer <> requester)
);
CREATE INDEX IF NOT EXISTS idx_ca_sha ON brain.commit_approvals(commit_sha, repo);

INSERT INTO brain.agent_identities (role_key, model) VALUES
    ('claude_code','claude'),('claude_dane','claude'),
    ('codex_hector','codex'),('claude_reviewer','claude')
ON CONFLICT (role_key) DO NOTHING;

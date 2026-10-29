-- Esquema minimo para el bus propio (brain-control-lite), independiente del
-- Postgres de ConsuConstruct. Correr una sola vez contra el Postgres propio
-- de la PC remota (Hector/Dane). Vacio al inicio, sin datos de ConsuConstruct.
-- Requiere la extension pgvector instalada en esa base.

CREATE SCHEMA IF NOT EXISTS brain;

-- CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS brain.goals (
    id BIGSERIAL PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    assigned_role_key TEXT,
    priority INTEGER NOT NULL DEFAULT 2,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brain.agent_run_events (
    id BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,          -- agent_message | agent_reply | agent_ack
    goal_id BIGINT REFERENCES brain.goals(id),
    content TEXT NOT NULL,
    usage JSONB NOT NULL DEFAULT '{}'::jsonb,  -- from_role, to_role, reply_to
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_are_goal_id ON brain.agent_run_events(goal_id);
CREATE INDEX IF NOT EXISTS idx_are_reply_to ON brain.agent_run_events((usage->>'reply_to'));
CREATE INDEX IF NOT EXISTS idx_are_to_role ON brain.agent_run_events((usage->>'to_role'));

-- Identidad de agente: UUID estable por role_key, igual que
-- brain.agent_identities del sistema real de ConsuConstruct.
CREATE TABLE IF NOT EXISTS brain.agent_identities (
    role_key TEXT PRIMARY KEY,
    agent_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    model TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- 
-- -- Memoria/RAG local: chunks de sesion con embedding de Ollama nomic-embed-text
-- -- (768 dims). Vacio hasta que el session chunker indexe contenido propio.
-- CREATE TABLE IF NOT EXISTS brain.agent_memory_chunks (
--     id BIGSERIAL PRIMARY KEY,
--     role_key TEXT,
--     content TEXT NOT NULL,
--     embedding VECTOR(768),
--     source_session_id TEXT,
--     created_at TIMESTAMPTZ NOT NULL DEFAULT now()
-- );
-- 
CREATE INDEX IF NOT EXISTS idx_amc_embedding
    ON brain.agent_memory_chunks USING hnsw (embedding vector_cosine_ops);

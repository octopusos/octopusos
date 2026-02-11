-- Phase 3: Chat injection queue (card -> chat message) with idempotency.

CREATE TABLE IF NOT EXISTS chat_injection_queue (
  injection_id TEXT PRIMARY KEY,
  card_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL, -- queued|applied|failed|cancelled
  message_id TEXT, -- populated when applied
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  error_json TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_chat_injection_queue_session_idempotency
  ON chat_injection_queue(session_id, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_chat_injection_queue_status_created
  ON chat_injection_queue(status, created_at_ms);


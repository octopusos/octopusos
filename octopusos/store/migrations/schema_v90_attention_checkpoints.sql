-- Phase 2: checkpoints for ledger polling (to avoid reprocessing)

CREATE TABLE IF NOT EXISTS attention_checkpoints (
  name TEXT PRIMARY KEY,
  last_created_at_ms INTEGER NOT NULL DEFAULT 0,
  last_event_id TEXT NOT NULL DEFAULT ''
);


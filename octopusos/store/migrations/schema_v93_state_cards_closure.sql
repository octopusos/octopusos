-- Phase 4: State Card closure semantics (resolution fields)

PRAGMA foreign_keys = OFF;

ALTER TABLE state_cards ADD COLUMN resolution_status TEXT NOT NULL DEFAULT 'open'; -- open|acknowledged|resolved|dismissed|deferred
ALTER TABLE state_cards ADD COLUMN resolution_reason TEXT; -- short reason code or freeform
ALTER TABLE state_cards ADD COLUMN resolved_at_ms INTEGER;
ALTER TABLE state_cards ADD COLUMN resolved_by TEXT; -- user|system
ALTER TABLE state_cards ADD COLUMN resolution_note TEXT;
ALTER TABLE state_cards ADD COLUMN linked_task_id TEXT;

CREATE INDEX IF NOT EXISTS idx_state_cards_resolution
  ON state_cards(resolution_status, last_seen_ms);

PRAGMA foreign_keys = ON;


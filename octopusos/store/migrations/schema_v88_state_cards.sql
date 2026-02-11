-- Phase 2: State Cards (signal shaping output)

CREATE TABLE IF NOT EXISTS state_cards (
  card_id TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL, -- global|project|session|resource
  scope_id TEXT NOT NULL,
  card_type TEXT NOT NULL,
  severity TEXT NOT NULL, -- info|warn|high|critical
  status TEXT NOT NULL, -- open|snoozed|closed
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  first_seen_ms INTEGER NOT NULL,
  last_seen_ms INTEGER NOT NULL,
  last_event_id TEXT,
  merge_key TEXT NOT NULL,
  cooldown_until_ms INTEGER,
  metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_state_cards_scope_status_seen
  ON state_cards(scope_type, scope_id, status, last_seen_ms);

CREATE INDEX IF NOT EXISTS idx_state_cards_status_severity_seen
  ON state_cards(status, severity, last_seen_ms);

CREATE INDEX IF NOT EXISTS idx_state_cards_merge_key
  ON state_cards(merge_key);

-- Ensure we don't spam multiple open cards for the same merge_key.
CREATE UNIQUE INDEX IF NOT EXISTS ux_state_cards_open_merge_key
  ON state_cards(merge_key)
  WHERE status = 'open';

CREATE TABLE IF NOT EXISTS state_card_events (
  card_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  added_at_ms INTEGER NOT NULL,
  PRIMARY KEY(card_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_state_card_events_event
  ON state_card_events(event_id);


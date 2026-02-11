-- Phase 3: Session presence for UI-aware injection gating.

CREATE TABLE IF NOT EXISTS session_presence (
  session_id TEXT PRIMARY KEY,
  last_seen_ms INTEGER NOT NULL
);


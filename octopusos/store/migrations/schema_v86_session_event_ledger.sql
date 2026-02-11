-- Migration v86: session_event_ledger (Phase 1 groundwork)
--
-- Purpose:
-- - Append-only ledger for session events (observability + idempotency boundary in later phases)
-- - Phase 1: legacy/dual_write record observed events; writer takeover will use pending/applied.

CREATE TABLE IF NOT EXISTS session_event_ledger (
  event_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  ordering_key INTEGER, -- Phase 1 allow NULL (legacy/dual_write observed)
  event_type TEXT NOT NULL,
  source TEXT NOT NULL,
  idempotency_key TEXT,
  causation_id TEXT,
  correlation_id TEXT,
  payload_json TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  apply_status TEXT NOT NULL DEFAULT 'observed',
  applied_at_ms INTEGER,
  apply_error_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_sel_session_created
  ON session_event_ledger(session_id, created_at_ms);

CREATE INDEX IF NOT EXISTS idx_sel_session_ordering
  ON session_event_ledger(session_id, ordering_key);

CREATE INDEX IF NOT EXISTS idx_sel_apply_status
  ON session_event_ledger(apply_status, created_at_ms);


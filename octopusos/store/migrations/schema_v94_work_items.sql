-- Phase 4: Work List (user-visible background work items)
-- NOTE: "work_items" already exists in the recovery subsystem (v30). Use a new table name.

CREATE TABLE IF NOT EXISTS work_list_items (
  work_id TEXT PRIMARY KEY,
  type TEXT NOT NULL, -- investigation|repair|summary|recovery|maintenance
  title TEXT NOT NULL,
  status TEXT NOT NULL, -- queued|running|succeeded|failed|cancelled
  priority INTEGER NOT NULL DEFAULT 3, -- 1-5
  scope_type TEXT NOT NULL, -- global|project|session|resource
  scope_id TEXT NOT NULL,
  source_card_id TEXT, -- optional
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  started_at_ms INTEGER,
  finished_at_ms INTEGER,
  summary TEXT NOT NULL DEFAULT '',
  detail_json TEXT NOT NULL DEFAULT '{}',
  evidence_ref_json TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_work_items_status_updated
  ON work_list_items(status, updated_at_ms);

CREATE INDEX IF NOT EXISTS idx_work_items_scope_status_updated
  ON work_list_items(scope_type, scope_id, status, updated_at_ms);

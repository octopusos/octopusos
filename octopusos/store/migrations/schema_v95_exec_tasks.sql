-- Phase 4: Execution Tasks (transparent background execution pipeline)

CREATE TABLE IF NOT EXISTS exec_tasks (
  task_id TEXT PRIMARY KEY,
  work_id TEXT,
  card_id TEXT,
  task_type TEXT NOT NULL, -- context_repair_assist|writer_recovery_assist|diagnostic_bundle|refresh_context_pack
  status TEXT NOT NULL, -- queued|running|succeeded|failed|cancelled
  risk_level TEXT NOT NULL, -- low|medium|high
  requires_confirmation INTEGER NOT NULL DEFAULT 0,
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  started_at_ms INTEGER,
  finished_at_ms INTEGER,
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT NOT NULL DEFAULT '{}',
  error_json TEXT,
  evidence_paths_json TEXT NOT NULL DEFAULT '[]',
  idempotency_key TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_exec_tasks_status_updated
  ON exec_tasks(status, updated_at_ms);

CREATE UNIQUE INDEX IF NOT EXISTS ux_exec_tasks_idempotency
  ON exec_tasks(idempotency_key);


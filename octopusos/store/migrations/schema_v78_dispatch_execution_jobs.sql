-- Schema v78: Dispatch Execution Jobs (v3.3)
--
-- Purpose:
-- - Track execution jobs for approved dispatch proposals
-- - Enforce idempotency via unique key
-- - Support rollback jobs
-- - Store agent pause state for v3.3 actions
--
-- Created: 2026-02-05

CREATE TABLE IF NOT EXISTS dispatch_execution_jobs (
    job_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    status TEXT NOT NULL, -- queued|running|succeeded|failed|cancelled|rolled_back
    idempotency_key TEXT NOT NULL,
    resource_key TEXT NOT NULL,
    execution_mode TEXT NOT NULL, -- auto|manual
    started_at INTEGER,
    ended_at INTEGER,
    attempt INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    last_error_code TEXT,
    last_error_message TEXT,
    evidence_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dispatch_jobs_idempotency
ON dispatch_execution_jobs(idempotency_key);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dispatch_jobs_resource_active
ON dispatch_execution_jobs(resource_key)
WHERE status IN ('queued', 'running');

CREATE INDEX IF NOT EXISTS idx_dispatch_jobs_status
ON dispatch_execution_jobs(status, created_at DESC);

CREATE TABLE IF NOT EXISTS dispatch_rollback_jobs (
    rollback_job_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    status TEXT NOT NULL, -- queued|running|succeeded|failed|cancelled
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dispatch_rollback_job
ON dispatch_rollback_jobs(job_id, created_at DESC);

CREATE TABLE IF NOT EXISTS dispatch_agent_state (
    agent_id TEXT PRIMARY KEY,
    status TEXT NOT NULL, -- active|paused
    updated_at_ms INTEGER NOT NULL
);

-- Optional columns for dispatch_proposals (auto execute flags)
ALTER TABLE dispatch_proposals ADD COLUMN auto_execute_eligible INTEGER DEFAULT 0;
ALTER TABLE dispatch_proposals ADD COLUMN auto_execute_policy TEXT DEFAULT 'never';
ALTER TABLE dispatch_proposals ADD COLUMN approved_then_auto_execute INTEGER DEFAULT 0;

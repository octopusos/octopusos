-- Schema v77: Dispatch Proposals (v3.2)
--
-- Purpose:
-- - Persist dispatch proposals created by Frontdesk
-- - Track approvals, rejections, and execution lifecycle
-- - Record audit decisions for replay
--
-- Created: 2026-02-04

CREATE TABLE IF NOT EXISTS dispatch_proposals (
    proposal_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    proposal_type TEXT NOT NULL,
    status TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    scope_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at INTEGER NOT NULL,
    reviewed_by TEXT,
    reviewed_at INTEGER,
    review_comment TEXT,
    execution_ref TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dispatch_proposals_status
ON dispatch_proposals(status, created_at DESC);

CREATE TABLE IF NOT EXISTS dispatch_decisions_audit (
    event_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    at INTEGER NOT NULL,
    details_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dispatch_audit_proposal
ON dispatch_decisions_audit(proposal_id, at DESC);

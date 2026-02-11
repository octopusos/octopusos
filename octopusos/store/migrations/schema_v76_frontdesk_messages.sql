-- Schema v76: Frontdesk Chat Messages (v3.1 MVP)
--
-- Purpose:
-- - Persist Frontdesk chat messages for history replay
-- - Keep evidence references and meta for auditability
--
-- Design Principles:
-- 1. Separate channel: frontdesk_messages table
-- 2. Epoch ms timestamps (ADR-011)
-- 3. Evidence refs always present (JSON array)
--
-- Created: 2026-02-04

CREATE TABLE IF NOT EXISTS frontdesk_messages (
    id TEXT PRIMARY KEY,                 -- Message ID (fdm_*)
    role TEXT NOT NULL,                  -- user | assistant | system
    text TEXT NOT NULL,                  -- Message content
    created_at INTEGER NOT NULL,         -- epoch ms
    evidence_json TEXT NOT NULL,         -- JSON array (string)
    meta_json TEXT,                      -- JSON object
    scope_json TEXT,                     -- JSON object

    CHECK(role IN ('user', 'assistant', 'system')),
    CHECK(created_at > 0)
);

CREATE INDEX IF NOT EXISTS idx_frontdesk_messages_created_at
ON frontdesk_messages(created_at DESC);

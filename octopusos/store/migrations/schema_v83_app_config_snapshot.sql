-- schema_v83_app_config_snapshot.sql
-- Snapshot and timeline tables for config replay and diff.

BEGIN;

CREATE TABLE IF NOT EXISTS app_config_snapshot (
    snapshot_id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    project_id TEXT,
    actor TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'db',
    note TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_config_timeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    module TEXT,
    config_key TEXT,
    project_id TEXT,
    decision_id TEXT,
    risk_level TEXT,
    reason TEXT,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_config_timeline_created_at ON app_config_timeline(created_at);

COMMIT;

-- schema_v81_app_config_registry.sql
-- App-level configuration registry (non-secret and secret_ref metadata)

BEGIN;

CREATE TABLE IF NOT EXISTS app_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value_json TEXT NOT NULL,
    value_type TEXT NOT NULL,
    module TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    is_secret INTEGER NOT NULL DEFAULT 0,
    is_hot_reload INTEGER NOT NULL DEFAULT 1,
    schema_version INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT 'db',
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_config_key ON app_config(key);
CREATE INDEX IF NOT EXISTS idx_app_config_module ON app_config(module);
CREATE INDEX IF NOT EXISTS idx_app_config_scope ON app_config(scope);

CREATE TABLE IF NOT EXISTS app_config_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL,
    module TEXT NOT NULL,
    actor TEXT NOT NULL,
    op TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT NOT NULL,
    old_preview TEXT,
    new_preview TEXT,
    schema_version INTEGER NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_app_config_audit_key ON app_config_audit(config_key);
CREATE INDEX IF NOT EXISTS idx_app_config_audit_created_at ON app_config_audit(created_at);

COMMIT;

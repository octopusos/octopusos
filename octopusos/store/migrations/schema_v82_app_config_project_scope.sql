-- schema_v82_app_config_project_scope.sql
-- Project-scope support for app_config and app_config_audit.

BEGIN;

ALTER TABLE app_config ADD COLUMN project_id TEXT;
ALTER TABLE app_config_audit ADD COLUMN project_id TEXT;
ALTER TABLE app_config_audit ADD COLUMN decision_id TEXT;
ALTER TABLE app_config_audit ADD COLUMN reason TEXT;
ALTER TABLE app_config_audit ADD COLUMN risk_level TEXT;

CREATE INDEX IF NOT EXISTS idx_app_config_project_id ON app_config(project_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_app_config_project_key ON app_config(COALESCE(project_id, ''), key);
CREATE INDEX IF NOT EXISTS idx_app_config_audit_project_id ON app_config_audit(project_id);

COMMIT;

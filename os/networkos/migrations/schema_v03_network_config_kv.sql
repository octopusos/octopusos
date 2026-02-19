-- NetworkOS schema v03: network_config_kv (non-secret config persistence)
--
-- Hard boundary:
-- - Non-sensitive config only (hostname/account_id/zone_id/team_name/enforce_access/health_path)
-- - service_token_id is non-secret and may be persisted for diagnostics
-- - Secrets must stay in SecretStore (secret:// refs)

CREATE TABLE IF NOT EXISTS network_config_kv (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL,
  updated_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_network_config_kv_updated_at ON network_config_kv(updated_at DESC);

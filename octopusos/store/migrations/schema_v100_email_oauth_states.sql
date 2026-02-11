-- schema_v100_email_oauth_states.sql

CREATE TABLE IF NOT EXISTS email_oauth_states (
  state TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL,
  provider_type TEXT NOT NULL,
  code_verifier TEXT NOT NULL,
  redirect_uri TEXT NOT NULL,
  scopes TEXT NOT NULL,
  created_at_ms INTEGER NOT NULL,
  expires_at_ms INTEGER NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_email_oauth_states_instance_expires
  ON email_oauth_states(instance_id, expires_at_ms);

INSERT INTO schema_version (version, applied_at)
VALUES ('0.100.0-v100', datetime('now'));


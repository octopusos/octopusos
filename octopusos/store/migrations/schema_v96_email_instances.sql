-- Email instances (multi-mailbox / multi-config support)

CREATE TABLE IF NOT EXISTS email_instances (
  instance_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  provider_type TEXT NOT NULL, -- imap_smtp|mock (tests)
  config_json TEXT NOT NULL DEFAULT '{}',
  secret_ref TEXT NOT NULL DEFAULT '',
  created_at_ms INTEGER NOT NULL,
  updated_at_ms INTEGER NOT NULL,
  last_test_ok INTEGER NOT NULL DEFAULT 0,
  last_test_at_ms INTEGER,
  last_test_error TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_instances_updated
  ON email_instances(updated_at_ms DESC);


-- schema_v99_email_snoozes.sql

CREATE TABLE IF NOT EXISTS email_snoozes (
  instance_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  until_ms INTEGER NOT NULL,
  PRIMARY KEY (instance_id, message_id)
);

CREATE INDEX IF NOT EXISTS idx_email_snoozes_instance_until
  ON email_snoozes(instance_id, until_ms);

INSERT INTO schema_version (version, applied_at)
VALUES ('0.99.0-v99', datetime('now'));


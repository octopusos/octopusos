-- Email drafts + confirmation tokens (prevents accidental send)

CREATE TABLE IF NOT EXISTS email_drafts (
  draft_id TEXT PRIMARY KEY,
  instance_id TEXT NOT NULL,
  message_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  body_md TEXT NOT NULL,
  confirm_token TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft', -- draft|sent|cancelled
  created_at_ms INTEGER NOT NULL,
  expires_at_ms INTEGER NOT NULL,
  sent_at_ms INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_email_drafts_confirm_token
  ON email_drafts(confirm_token);

CREATE INDEX IF NOT EXISTS idx_email_drafts_instance_created
  ON email_drafts(instance_id, created_at_ms DESC);


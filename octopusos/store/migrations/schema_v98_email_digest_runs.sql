-- Daily digest schedule lock (per instance/day) to avoid duplicate runs

CREATE TABLE IF NOT EXISTS email_digest_runs (
  instance_id TEXT NOT NULL,
  run_key TEXT NOT NULL, -- YYYY-MM-DD in schedule timezone
  last_run_ms INTEGER NOT NULL,
  PRIMARY KEY (instance_id, run_key)
);


-- Migration v85: task_sessions compatibility table
--
-- Some legacy paths still query task_sessions directly.
-- Keep a compatibility table in octopusos DB to avoid runtime 500.

CREATE TABLE IF NOT EXISTS task_sessions (
    session_id TEXT PRIMARY KEY,
    channel TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_task_sessions_channel ON task_sessions(channel);
CREATE INDEX IF NOT EXISTS idx_task_sessions_created ON task_sessions(created_at DESC);


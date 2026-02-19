-- CommunicationOS schema v01

CREATE TABLE IF NOT EXISTS channel_configs (
    channel_id TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'needs_setup',
    enabled INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_heartbeat_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS channel_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    performed_by TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (channel_id) REFERENCES channel_configs(channel_id)
);

CREATE TABLE IF NOT EXISTS channel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message_id TEXT,
    status TEXT NOT NULL,
    error TEXT,
    metadata TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (channel_id) REFERENCES channel_configs(channel_id)
);

CREATE TABLE IF NOT EXISTS channel_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    user_key TEXT NOT NULL,
    conversation_key TEXT NOT NULL,
    scope TEXT NOT NULL,
    active_session_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(channel_id, user_key, conversation_key)
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    user_key TEXT NOT NULL,
    conversation_key TEXT NOT NULL,
    scope TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    message_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS session_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

CREATE TABLE IF NOT EXISTS message_dedupe (
    message_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    first_seen_ms INTEGER NOT NULL,
    last_seen_ms INTEGER NOT NULL,
    count INTEGER DEFAULT 1,
    metadata TEXT,
    PRIMARY KEY (message_id, channel_id)
);

CREATE TABLE IF NOT EXISTS rate_limit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL,
    user_key TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS message_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    user_key TEXT NOT NULL,
    conversation_key TEXT,
    session_id TEXT,
    timestamp_ms INTEGER NOT NULL,
    processing_status TEXT,
    metadata TEXT,
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS email_cursors (
    channel_id TEXT PRIMARY KEY,
    last_poll_time INTEGER NOT NULL,
    last_message_id TEXT,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_channel_events_channel_id ON channel_events(channel_id);
CREATE INDEX IF NOT EXISTS idx_channel_events_created_at ON channel_events(created_at);
CREATE INDEX IF NOT EXISTS idx_channel_audit_log_channel_id ON channel_audit_log(channel_id);
CREATE INDEX IF NOT EXISTS idx_channel_sessions_lookup ON channel_sessions(channel_id, user_key, conversation_key);
CREATE INDEX IF NOT EXISTS idx_sessions_channel_user ON sessions(channel_id, user_key, status);
CREATE INDEX IF NOT EXISTS idx_session_history_session_id ON session_history(session_id);
CREATE INDEX IF NOT EXISTS idx_message_dedupe_last_seen ON message_dedupe(last_seen_ms);
CREATE INDEX IF NOT EXISTS idx_rate_limit_channel_user_time ON rate_limit_events(channel_id, user_key, timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_audit_message_id ON message_audit(message_id);
CREATE INDEX IF NOT EXISTS idx_audit_channel_user ON message_audit(channel_id, user_key, timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_audit_session ON message_audit(session_id, timestamp_ms DESC);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON message_audit(created_at_ms DESC);


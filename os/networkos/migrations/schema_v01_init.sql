-- NetworkOS schema v01

CREATE TABLE IF NOT EXISTS network_tunnels (
    tunnel_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    name TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 0,
    public_hostname TEXT NOT NULL,
    local_target TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'http',
    health_status TEXT NOT NULL DEFAULT 'unknown',
    last_heartbeat_at INTEGER,
    last_error_code TEXT,
    last_error_message TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(provider, name)
);

CREATE TABLE IF NOT EXISTS network_routes (
    route_id TEXT PRIMARY KEY,
    tunnel_id TEXT NOT NULL,
    path_prefix TEXT NOT NULL,
    local_target TEXT NOT NULL,
    is_enabled INTEGER NOT NULL DEFAULT 1,
    priority INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (tunnel_id) REFERENCES network_tunnels(tunnel_id) ON DELETE CASCADE,
    UNIQUE(tunnel_id, path_prefix)
);

CREATE TABLE IF NOT EXISTS network_events (
    event_id TEXT PRIMARY KEY,
    tunnel_id TEXT NOT NULL,
    level TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    data_json TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (tunnel_id) REFERENCES network_tunnels(tunnel_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tunnel_secrets (
    tunnel_id TEXT PRIMARY KEY,
    token TEXT,
    secret_ref TEXT,
    is_migrated INTEGER DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    FOREIGN KEY (tunnel_id) REFERENCES network_tunnels(tunnel_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_network_tunnels_provider ON network_tunnels(provider);
CREATE INDEX IF NOT EXISTS idx_network_tunnels_enabled ON network_tunnels(is_enabled);
CREATE INDEX IF NOT EXISTS idx_network_tunnels_health ON network_tunnels(health_status);
CREATE INDEX IF NOT EXISTS idx_network_tunnels_updated ON network_tunnels(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_network_routes_tunnel ON network_routes(tunnel_id, priority DESC);
CREATE INDEX IF NOT EXISTS idx_network_routes_enabled ON network_routes(is_enabled);

CREATE INDEX IF NOT EXISTS idx_network_events_tunnel ON network_events(tunnel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_events_level ON network_events(level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_events_tunnel_time ON network_events(tunnel_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_events_level_time ON network_events(level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_events_type_time ON network_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_events_recent ON network_events(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tunnel_secrets_ref ON tunnel_secrets(secret_ref);
CREATE INDEX IF NOT EXISTS idx_tunnel_secrets_migrated ON tunnel_secrets(is_migrated) WHERE is_migrated = 0;
CREATE INDEX IF NOT EXISTS idx_tunnel_secrets_tunnel ON tunnel_secrets(tunnel_id);


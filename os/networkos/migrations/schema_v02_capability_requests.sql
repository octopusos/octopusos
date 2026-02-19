-- NetworkOS schema v02: capability requests + audit log (isolated from CommunicationOS message_audit)

CREATE TABLE IF NOT EXISTS network_capability_requests (
    id TEXT PRIMARY KEY,
    capability TEXT NOT NULL,
    params_json TEXT NOT NULL DEFAULT '{}',
    requested_by TEXT NOT NULL DEFAULT 'unknown',
    decision TEXT NOT NULL DEFAULT 'explain_confirm', -- silent_allow|explain_confirm|block
    decision_reason TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending', -- pending|approved|active|failed|revoked
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_network_capability_requests_capability ON network_capability_requests(capability);
CREATE INDEX IF NOT EXISTS idx_network_capability_requests_status ON network_capability_requests(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_capability_requests_created ON network_capability_requests(created_at DESC);

CREATE TABLE IF NOT EXISTS network_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- REQUESTED|APPROVED|EXECUTED|FAILED|REVOKED
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    FOREIGN KEY (request_id) REFERENCES network_capability_requests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_network_audit_log_request ON network_audit_log(request_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_network_audit_log_created ON network_audit_log(created_at DESC);


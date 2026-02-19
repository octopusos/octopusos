-- BrainOS schema v01

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    attrs_json TEXT DEFAULT '{}',
    created_at REAL NOT NULL,
    UNIQUE(type, key)
);

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src_entity_id INTEGER NOT NULL,
    dst_entity_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    key TEXT NOT NULL,
    attrs_json TEXT DEFAULT '{}',
    confidence REAL DEFAULT 1.0,
    created_at REAL NOT NULL,
    FOREIGN KEY(src_entity_id) REFERENCES entities(id),
    FOREIGN KEY(dst_entity_id) REFERENCES entities(id),
    UNIQUE(key)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    edge_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    span_json TEXT DEFAULT '{}',
    attrs_json TEXT DEFAULT '{}',
    created_at REAL NOT NULL,
    FOREIGN KEY(edge_id) REFERENCES edges(id),
    UNIQUE(edge_id, source_type, source_ref, span_json)
);

CREATE TABLE IF NOT EXISTS build_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    graph_version TEXT NOT NULL,
    source_commit TEXT NOT NULL,
    repo_path TEXT NOT NULL,
    built_at REAL NOT NULL,
    duration_ms INTEGER NOT NULL,
    entity_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    evidence_count INTEGER NOT NULL,
    enabled_extractors TEXT NOT NULL,
    errors TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS _schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS brain_snapshots (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    description TEXT,
    entity_count INTEGER NOT NULL,
    edge_count INTEGER NOT NULL,
    evidence_count INTEGER NOT NULL,
    coverage_percentage REAL NOT NULL,
    git_coverage REAL NOT NULL,
    doc_coverage REAL NOT NULL,
    code_coverage REAL NOT NULL,
    blind_spot_count INTEGER NOT NULL,
    high_risk_blind_spot_count INTEGER NOT NULL,
    graph_version TEXT NOT NULL,
    created_by TEXT,
    UNIQUE(timestamp)
);

CREATE TABLE IF NOT EXISTS brain_snapshot_entities (
    snapshot_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    evidence_count INTEGER NOT NULL,
    coverage_sources TEXT NOT NULL,
    is_blind_spot INTEGER NOT NULL,
    blind_spot_severity REAL,
    PRIMARY KEY (snapshot_id, entity_id),
    FOREIGN KEY (snapshot_id) REFERENCES brain_snapshots(id)
);

CREATE TABLE IF NOT EXISTS brain_snapshot_edges (
    snapshot_id TEXT NOT NULL,
    edge_id TEXT NOT NULL,
    src_entity_id TEXT NOT NULL,
    dst_entity_id TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    evidence_count INTEGER NOT NULL,
    evidence_types TEXT NOT NULL,
    PRIMARY KEY (snapshot_id, edge_id),
    FOREIGN KEY (snapshot_id) REFERENCES brain_snapshots(id)
);

CREATE TABLE IF NOT EXISTS decision_records (
    decision_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    seed TEXT NOT NULL,
    inputs TEXT NOT NULL,
    outputs TEXT NOT NULL,
    rules_triggered TEXT NOT NULL,
    final_verdict TEXT NOT NULL,
    confidence_score REAL NOT NULL,
    timestamp TEXT NOT NULL,
    snapshot_ref TEXT,
    signed_by TEXT,
    sign_timestamp TEXT,
    sign_note TEXT,
    status TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    CHECK (status IN ('PENDING', 'APPROVED', 'BLOCKED', 'SIGNED', 'FAILED'))
);

CREATE TABLE IF NOT EXISTS decision_signoffs (
    signoff_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    signed_by TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    note TEXT NOT NULL,
    FOREIGN KEY (decision_id) REFERENCES decision_records(decision_id)
);

CREATE TABLE IF NOT EXISTS brain_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS classifier_versions (
    version_id TEXT PRIMARY KEY,
    version_number TEXT NOT NULL,
    parent_version_id TEXT,
    version_type TEXT NOT NULL DEFAULT 'active',
    change_log TEXT NOT NULL,
    source_proposal_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS version_rollback_history (
    rollback_id TEXT PRIMARY KEY,
    from_version_id TEXT NOT NULL,
    to_version_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_key ON entities(key);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src_entity_id);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst_entity_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
CREATE INDEX IF NOT EXISTS idx_evidence_edge ON evidence(edge_id);

CREATE INDEX IF NOT EXISTS idx_brain_snapshots_timestamp ON brain_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_brain_snapshot_entities_snapshot ON brain_snapshot_entities(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_brain_snapshot_edges_snapshot ON brain_snapshot_edges(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_decision_records_seed ON decision_records(seed);
CREATE INDEX IF NOT EXISTS idx_decision_records_type ON decision_records(decision_type);
CREATE INDEX IF NOT EXISTS idx_decision_records_timestamp ON decision_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_decision_records_status ON decision_records(status);
CREATE INDEX IF NOT EXISTS idx_decision_signoffs_decision_id ON decision_signoffs(decision_id);

CREATE INDEX IF NOT EXISTS idx_brain_cache_expires ON brain_cache(expires_at);

CREATE INDEX IF NOT EXISTS idx_classifier_versions_type ON classifier_versions(version_type);
CREATE INDEX IF NOT EXISTS idx_classifier_versions_active ON classifier_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_classifier_versions_created ON classifier_versions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_classifier_versions_parent ON classifier_versions(parent_version_id);
CREATE INDEX IF NOT EXISTS idx_classifier_versions_proposal ON classifier_versions(source_proposal_id);
CREATE INDEX IF NOT EXISTS idx_versions_type ON classifier_versions(version_type);
CREATE INDEX IF NOT EXISTS idx_versions_created ON classifier_versions(created_at);

CREATE INDEX IF NOT EXISTS idx_rollback_history_from_version ON version_rollback_history(from_version_id);
CREATE INDEX IF NOT EXISTS idx_rollback_history_to_version ON version_rollback_history(to_version_id);
CREATE INDEX IF NOT EXISTS idx_rollback_history_performed_at ON version_rollback_history(performed_at DESC);


CREATE TABLE classifier_versions (
    version_id TEXT PRIMARY KEY,

    -- ===== 【语义层】Shadow Evaluation / Decision Semantics =====
    -- Used by: decision_candidate_store.py, shadow_registry.py
    version_type TEXT NOT NULL CHECK (version_type IN ('active', 'shadow')),
    change_description TEXT,

    -- ===== 【治理层】Version Management / Evolution Governance =====
    -- Used by: classifier_version_manager.py, classifier_migrate.py
    version_number TEXT,             -- Semantic version: "1.0", "2.0"
    parent_version_id TEXT,          -- For rollback chain
    change_log TEXT,                 -- Detailed change log
    source_proposal_id TEXT,         -- Source ImprovementProposal ID
    is_active INTEGER DEFAULT 0,     -- 1 if currently active version
    created_by TEXT,                 -- Creator (user/system)

    -- ===== 【通用】Shared metadata =====
    created_at TEXT NOT NULL,
    promoted_from TEXT,              -- If promoted from shadow to active
    deprecated_at TEXT,              -- When this version was deprecated
    metadata TEXT DEFAULT '{}',      -- JSON metadata

    -- Constraints
    CONSTRAINT valid_version_type CHECK (version_type IN ('active', 'shadow')),
    CONSTRAINT valid_is_active CHECK (is_active IN (0, 1)),
    FOREIGN KEY (parent_version_id) REFERENCES classifier_versions(version_id),
    FOREIGN KEY (source_proposal_id) REFERENCES improvement_proposals(proposal_id)
);
CREATE INDEX idx_classifier_versions_active
    ON classifier_versions(is_active, created_at DESC)
    WHERE is_active = 1;
CREATE INDEX idx_classifier_versions_type
    ON classifier_versions(version_type, created_at DESC);
CREATE INDEX idx_classifier_versions_created
    ON classifier_versions(created_at DESC);
CREATE INDEX idx_classifier_versions_parent
    ON classifier_versions(parent_version_id)
    WHERE parent_version_id IS NOT NULL;
CREATE INDEX idx_classifier_versions_proposal
    ON classifier_versions(source_proposal_id)
    WHERE source_proposal_id IS NOT NULL;
CREATE INDEX idx_classifier_versions_active
    ON classifier_versions(is_active, created_at DESC)
    WHERE is_active = 1;
CREATE INDEX idx_classifier_versions_type
    ON classifier_versions(version_type, created_at DESC);
CREATE INDEX idx_classifier_versions_created
    ON classifier_versions(created_at DESC);
CREATE INDEX idx_classifier_versions_parent
    ON classifier_versions(parent_version_id)
    WHERE parent_version_id IS NOT NULL;
CREATE INDEX idx_classifier_versions_proposal
    ON classifier_versions(source_proposal_id)
    WHERE source_proposal_id IS NOT NULL;

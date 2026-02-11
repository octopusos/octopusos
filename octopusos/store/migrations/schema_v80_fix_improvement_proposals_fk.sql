-- schema_v80_fix_improvement_proposals_fk.sql
-- Fix foreign key on improvement_proposals.affected_version_id
-- v43 renames classifier_versions to _classifier_versions_v43_backup and recreates it,
-- which can leave improvement_proposals FK pointing to the backup table.

PRAGMA foreign_keys = OFF;
BEGIN;

-- Repair task project_id FK validation triggers to use projects.project_id
DROP TRIGGER IF EXISTS check_tasks_project_id_insert;
DROP TRIGGER IF EXISTS check_tasks_project_id_update;

CREATE TRIGGER IF NOT EXISTS check_tasks_project_id_insert
BEFORE INSERT ON tasks
FOR EACH ROW
WHEN NEW.project_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (SELECT 1 FROM projects WHERE project_id = NEW.project_id)
        THEN RAISE(ABORT, 'Foreign key constraint failed: project_id must reference existing project')
    END;
END;

CREATE TRIGGER IF NOT EXISTS check_tasks_project_id_update
BEFORE UPDATE OF project_id ON tasks
FOR EACH ROW
WHEN NEW.project_id IS NOT NULL
BEGIN
    SELECT CASE
        WHEN NOT EXISTS (SELECT 1 FROM projects WHERE project_id = NEW.project_id)
        THEN RAISE(ABORT, 'Foreign key constraint failed: project_id must reference existing project')
    END;
END;

-- Backup existing data
ALTER TABLE improvement_proposals RENAME TO _improvement_proposals_v80_backup;

-- Recreate improvement_proposals with correct FK target
CREATE TABLE improvement_proposals (
    proposal_id TEXT PRIMARY KEY,

    -- Scope and change details
    scope TEXT NOT NULL,
    change_type TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Evidence (stored as JSON)
    evidence TEXT NOT NULL,  -- JSON: ProposalEvidence

    -- Recommendation
    recommendation TEXT NOT NULL,
    reasoning TEXT NOT NULL,

    -- Affected components
    affected_version_id TEXT NOT NULL,
    shadow_version_id TEXT,

    -- Lifecycle management
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    review_notes TEXT,
    implemented_at TEXT,

    -- Metadata
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON

    -- Constraints
    CONSTRAINT valid_proposal_id CHECK (proposal_id LIKE 'BP-%'),
    CONSTRAINT valid_change_type CHECK (
        change_type IN (
            'expand_keyword',
            'adjust_threshold',
            'add_signal',
            'remove_signal',
            'refine_rule',
            'promote_shadow'
        )
    ),
    CONSTRAINT valid_recommendation CHECK (
        recommendation IN (
            'Promote to v2',
            'Reject',
            'Defer',
            'Test in staging'
        )
    ),
    CONSTRAINT valid_status CHECK (
        status IN ('pending', 'accepted', 'rejected', 'deferred', 'implemented')
    ),
    CONSTRAINT reviewed_proposals_have_reviewer CHECK (
        status = 'pending' OR (
            reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL
        )
    ),
    CONSTRAINT implemented_proposals_have_timestamp CHECK (
        status != 'implemented' OR implemented_at IS NOT NULL
    ),
    FOREIGN KEY (affected_version_id) REFERENCES classifier_versions(version_id)
);

-- Restore data
INSERT INTO improvement_proposals (
    proposal_id, scope, change_type, description,
    evidence, recommendation, reasoning,
    affected_version_id, shadow_version_id,
    status, created_at, reviewed_by, reviewed_at,
    review_notes, implemented_at, metadata
)
SELECT
    proposal_id, scope, change_type, description,
    evidence, recommendation, reasoning,
    affected_version_id, shadow_version_id,
    status, created_at, reviewed_by, reviewed_at,
    review_notes, implemented_at, metadata
FROM _improvement_proposals_v80_backup;

DROP TABLE _improvement_proposals_v80_backup;

-- Rebuild proposal_history to refresh FK target after table rename
ALTER TABLE proposal_history RENAME TO _proposal_history_v80_backup;

CREATE TABLE proposal_history (
    history_id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,

    -- Change details
    action TEXT NOT NULL,  -- 'created', 'accepted', 'rejected', 'deferred', 'implemented'
    actor TEXT,  -- User who performed the action
    timestamp TEXT NOT NULL,

    -- State snapshot (before the change)
    previous_status TEXT,
    new_status TEXT,
    notes TEXT,

    CONSTRAINT valid_action CHECK (
        action IN ('created', 'accepted', 'rejected', 'deferred', 'implemented', 'modified')
    ),
    FOREIGN KEY (proposal_id) REFERENCES improvement_proposals(proposal_id) ON DELETE CASCADE
);

INSERT INTO proposal_history (
    history_id, proposal_id, action, actor, timestamp,
    previous_status, new_status, notes
)
SELECT
    history_id, proposal_id, action, actor, timestamp,
    previous_status, new_status, notes
FROM _proposal_history_v80_backup;

DROP TABLE _proposal_history_v80_backup;

-- Rebuild version_rollback_history to refresh FK target after v43 rename
CREATE TABLE IF NOT EXISTS version_rollback_history (
    rollback_id TEXT PRIMARY KEY,
    from_version_id TEXT NOT NULL,
    to_version_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}'
);

ALTER TABLE version_rollback_history RENAME TO _version_rollback_history_v80_backup;

CREATE TABLE version_rollback_history (
    rollback_id TEXT PRIMARY KEY,

    -- Rollback details
    from_version_id TEXT NOT NULL,  -- Version being rolled back from
    to_version_id TEXT NOT NULL,    -- Version being restored

    -- Reason and metadata
    reason TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    performed_at TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',  -- JSON

    CONSTRAINT valid_rollback_id CHECK (rollback_id LIKE 'rollback-%'),
    FOREIGN KEY (from_version_id) REFERENCES classifier_versions(version_id),
    FOREIGN KEY (to_version_id) REFERENCES classifier_versions(version_id)
);

INSERT INTO version_rollback_history (
    rollback_id, from_version_id, to_version_id,
    reason, performed_by, performed_at, metadata
)
SELECT
    rollback_id, from_version_id, to_version_id,
    reason, performed_by, performed_at, metadata
FROM _version_rollback_history_v80_backup;

DROP TABLE _version_rollback_history_v80_backup;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_proposals_status
    ON improvement_proposals(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_proposals_affected_version
    ON improvement_proposals(affected_version_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_proposals_shadow_version
    ON improvement_proposals(shadow_version_id)
    WHERE shadow_version_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_proposals_pending
    ON improvement_proposals(created_at DESC)
    WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_proposals_reviewed
    ON improvement_proposals(reviewed_at DESC)
    WHERE reviewed_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_proposals_change_type
    ON improvement_proposals(change_type, status);

CREATE INDEX IF NOT EXISTS idx_proposal_history_proposal
    ON proposal_history(proposal_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_history_timestamp
    ON proposal_history(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_rollback_history_performed_at
    ON version_rollback_history(performed_at DESC);

CREATE INDEX IF NOT EXISTS idx_rollback_history_from_version
    ON version_rollback_history(from_version_id, performed_at DESC);

CREATE INDEX IF NOT EXISTS idx_rollback_history_to_version
    ON version_rollback_history(to_version_id, performed_at DESC);

COMMIT;
PRAGMA foreign_keys = ON;

-- Update schema version
INSERT INTO schema_version (version, applied_at)
VALUES (
    '0.80.0',
    CURRENT_TIMESTAMP
);

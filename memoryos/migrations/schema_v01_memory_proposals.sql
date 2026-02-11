-- MemoryOS schema v01: memory_proposals workflow table

CREATE TABLE IF NOT EXISTS memory_proposals (
    proposal_id TEXT PRIMARY KEY,
    proposed_by TEXT NOT NULL,
    proposed_at_ms INTEGER NOT NULL,
    memory_item TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at_ms INTEGER,
    review_reason TEXT,
    resulting_memory_id TEXT,
    metadata TEXT,
    CHECK (status IN ('pending', 'approved', 'rejected')),
    CHECK (proposed_at_ms > 0),
    CHECK (
        (status = 'pending' AND reviewed_by IS NULL AND reviewed_at_ms IS NULL) OR
        (status IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at_ms IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_proposal_status
    ON memory_proposals(status, proposed_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_agent
    ON memory_proposals(proposed_by, proposed_at_ms DESC);

CREATE INDEX IF NOT EXISTS idx_proposal_reviewed
    ON memory_proposals(reviewed_at_ms DESC)
    WHERE reviewed_at_ms IS NOT NULL;


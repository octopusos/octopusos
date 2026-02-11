-- MemoryOS schema v02: memory_items base store

CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    project_id TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5(
    id UNINDEXED,
    summary
);

CREATE TRIGGER IF NOT EXISTS memory_items_ai AFTER INSERT ON memory_items BEGIN
    INSERT INTO memory_items_fts(rowid, id, summary)
    VALUES (new.rowid, new.id, json_extract(new.content, '$.summary'));
END;

CREATE TRIGGER IF NOT EXISTS memory_items_ad AFTER DELETE ON memory_items BEGIN
    DELETE FROM memory_items_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_items_au AFTER UPDATE ON memory_items BEGIN
    DELETE FROM memory_items_fts WHERE rowid = old.rowid;
    INSERT INTO memory_items_fts(rowid, id, summary)
    VALUES (new.rowid, new.id, json_extract(new.content, '$.summary'));
END;


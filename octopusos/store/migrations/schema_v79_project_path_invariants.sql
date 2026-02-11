-- Schema v79: Enforce project.path invariant
--
-- Ensures project.path is non-empty when present.
-- Uses triggers as SQLite cannot add CHECK constraints to existing tables easily.

CREATE TRIGGER IF NOT EXISTS validate_projects_path_insert
BEFORE INSERT ON projects
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.path IS NULL OR length(trim(NEW.path)) = 0
        THEN RAISE(ABORT, 'projects.path must be non-empty')
    END;
END;

CREATE TRIGGER IF NOT EXISTS validate_projects_path_update
BEFORE UPDATE OF path ON projects
FOR EACH ROW
BEGIN
    SELECT CASE
        WHEN NEW.path IS NULL OR length(trim(NEW.path)) = 0
        THEN RAISE(ABORT, 'projects.path must be non-empty')
    END;
END;

-- Update schema version
INSERT OR REPLACE INTO schema_version (version, applied_at_ms, description)
VALUES ('0.79.0', (strftime('%s', 'now') * 1000), 'Enforce projects.path invariant');

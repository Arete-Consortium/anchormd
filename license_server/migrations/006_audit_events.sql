-- Strict-tier audit log.
-- One row per command run by a licensed client. 1-year retention enforced
-- by prune_old_events() called from FastAPI lifespan startup.

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id TEXT NOT NULL REFERENCES licenses(id),
    machine_id TEXT,
    event_type TEXT NOT NULL DEFAULT 'scan',
    command TEXT NOT NULL,
    repo_fingerprint TEXT,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_events_license_created
    ON audit_events(license_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_events_created
    ON audit_events(created_at);

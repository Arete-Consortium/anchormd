-- Strict-tier seat management.
-- One license_key can be claimed by up to metadata.seats distinct machine_ids.
-- Seat count comes from licenses.metadata.seats; defaults to 1 (single-seat Pro behavior).

CREATE TABLE IF NOT EXISTS seats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id TEXT NOT NULL REFERENCES licenses(id),
    machine_id TEXT NOT NULL,
    claimed_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(license_id, machine_id)
);

CREATE INDEX IF NOT EXISTS idx_seats_license
    ON seats(license_id);

CREATE INDEX IF NOT EXISTS idx_seats_last_seen
    ON seats(last_seen_at);

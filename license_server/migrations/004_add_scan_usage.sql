-- Track scan usage per license per billing period for tiered rate limiting.
-- Free: 1 audit/repo, 0 deep scans. Pro: unlimited audits, 10 deep scans/mo.

CREATE TABLE IF NOT EXISTS scan_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id TEXT NOT NULL REFERENCES licenses(id),
    scan_type TEXT NOT NULL,         -- 'audit' or 'deep_scan'
    repo_fingerprint TEXT,           -- hash of repo URL or path for per-repo tracking
    period TEXT NOT NULL,            -- 'YYYY-MM' billing period
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_scan_usage_license_period
    ON scan_usage(license_id, period, scan_type);

CREATE INDEX IF NOT EXISTS idx_scan_usage_repo
    ON scan_usage(license_id, scan_type, repo_fingerprint);

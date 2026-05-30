"""Tests for the audit-log endpoint — Strict-tier audit trail."""

from __future__ import annotations

import json
import uuid

from license_server.key_gen import generate_key, hash_key
from license_server.routes.audit import prune_old_events


def _activate_strict_key(db, *, seats: int = 5, active: int = 1):
    key = generate_key()
    key_h = hash_key(key)
    license_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO licenses (id, key_hash, license_key_masked, tier, email, "
        "active, metadata, product) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            license_id,
            key_h,
            f"ANMD-****-****-{key.split('-')[3]}",
            "strict",
            "team@example.com",
            active,
            json.dumps({"seats": seats}),
            "anchormd",
        ),
    )
    db.commit()
    return key, license_id


class TestAuditLog:
    def test_log_success(self, client, db) -> None:
        key, _ = _activate_strict_key(db)
        resp = client.post(
            "/v1/audit/log",
            json={
                "license_key": key,
                "machine_id": "m1",
                "command": "audit",
                "repo_fingerprint": "abc123",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["logged"] is True
        assert isinstance(body["event_id"], int)

    def test_log_unknown_license_returns_404(self, client, db) -> None:
        """Unknown licenses 404 so the client stops retrying."""
        resp = client.post(
            "/v1/audit/log",
            json={
                "license_key": "ANMD-AAAA-BBBB-XXXX",
                "command": "audit",
            },
        )
        assert resp.status_code == 404

    def test_log_revoked_license_returns_404(self, client, db) -> None:
        key, _ = _activate_strict_key(db, active=0)
        resp = client.post(
            "/v1/audit/log",
            json={"license_key": key, "command": "audit"},
        )
        assert resp.status_code == 404


class TestAuditExport:
    def test_export_requires_admin_bearer(self, client, db) -> None:
        key, _ = _activate_strict_key(db)
        resp = client.get("/v1/audit/export", params={"license_key": key})
        assert resp.status_code in (401, 422)

    def test_export_csv_format(self, client, db, admin_token) -> None:
        key, _ = _activate_strict_key(db)
        client.post(
            "/v1/audit/log",
            json={
                "license_key": key,
                "machine_id": "m1",
                "command": "fleet",
                "repo_fingerprint": "repo-xyz",
            },
        )
        resp = client.get(
            "/v1/audit/export",
            params={"license_key": key},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        # Header row + data row.
        lines = resp.text.strip().split("\n")
        assert lines[0].startswith("id,license_key_masked")
        assert "fleet" in lines[1]
        assert "repo-xyz" in lines[1]

    def test_export_json_format(self, client, db, admin_token) -> None:
        key, _ = _activate_strict_key(db)
        client.post(
            "/v1/audit/log",
            json={"license_key": key, "command": "audit"},
        )
        resp = client.get(
            "/v1/audit/export",
            params={"license_key": key, "format": "json"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["events"][0]["command"] == "audit"


class TestRetention:
    def test_retention_deletes_old_events(self, db) -> None:
        """prune_old_events drops rows older than the retention window."""
        _, license_id = _activate_strict_key(db)
        # Insert one fresh event and one ancient event.
        db.execute(
            "INSERT INTO audit_events (license_id, command, created_at) "
            "VALUES (?, ?, datetime('now'))",
            (license_id, "fresh"),
        )
        db.execute(
            "INSERT INTO audit_events (license_id, command, created_at) "
            "VALUES (?, ?, datetime('now', '-400 days'))",
            (license_id, "ancient"),
        )
        db.commit()

        deleted = prune_old_events(db, retention_days=365)
        assert deleted == 1

        remaining = db.execute(
            "SELECT command FROM audit_events WHERE license_id = ?",
            (license_id,),
        ).fetchall()
        commands = {r["command"] for r in remaining}
        assert commands == {"fresh"}

"""Tests for the seats endpoint — Strict-tier seat management."""

from __future__ import annotations

import json
import uuid

from license_server.key_gen import generate_key, hash_key


def _activate_strict_key(
    db,
    *,
    seats: int = 5,
    tier: str = "strict",
    email: str = "team@example.com",
    active: int = 1,
):
    """Insert a Strict license with a seat cap. Returns the plaintext key."""
    key = generate_key()
    key_h = hash_key(key)
    db.execute(
        "INSERT INTO licenses (id, key_hash, license_key_masked, tier, email, active, "
        "metadata, product) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            key_h,
            f"ANMD-****-****-{key.split('-')[3]}",
            tier,
            email,
            active,
            json.dumps({"seats": seats}),
            "anchormd",
        ),
    )
    db.commit()
    return key


class TestSeatClaim:
    def test_claim_success(self, client, db) -> None:
        key = _activate_strict_key(db, seats=5)
        resp = client.post(
            "/v1/seats/claim",
            json={"license_key": key, "machine_id": "machine-A"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["claimed"] is True
        assert body["seats_used"] == 1
        assert body["seats_total"] == 5

    def test_claim_idempotent_for_same_machine(self, client, db) -> None:
        """Re-claiming with the same machine_id refreshes last_seen, not seat count."""
        key = _activate_strict_key(db, seats=2)
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        resp = client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        assert resp.status_code == 200
        assert resp.json()["seats_used"] == 1

    def test_claim_over_cap_returns_409(self, client, db) -> None:
        """The (cap+1)th distinct machine must be rejected."""
        key = _activate_strict_key(db, seats=2)
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m2"})
        resp = client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m3"})
        assert resp.status_code == 409
        assert "Seat cap" in resp.json()["detail"]

    def test_claim_invalid_checksum_returns_404(self, client, db) -> None:
        # Valid format but wrong checksum.
        resp = client.post(
            "/v1/seats/claim",
            json={"license_key": "ANMD-AAAA-BBBB-XXXX", "machine_id": "m1"},
        )
        assert resp.status_code == 404


class TestSeatRelease:
    def test_release_success(self, client, db) -> None:
        key = _activate_strict_key(db, seats=3)
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        resp = client.post("/v1/seats/release", json={"license_key": key, "machine_id": "m1"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["released"] is True
        assert body["seats_used"] == 0

    def test_release_unknown_machine_idempotent(self, client, db) -> None:
        """Releasing a never-claimed machine returns released=False, not error."""
        key = _activate_strict_key(db, seats=3)
        resp = client.post("/v1/seats/release", json={"license_key": key, "machine_id": "ghost"})
        assert resp.status_code == 200
        assert resp.json()["released"] is False


class TestSeatList:
    def test_list_requires_admin_bearer(self, client, db) -> None:
        key = _activate_strict_key(db, seats=2)
        resp = client.get(
            "/v1/seats/list",
            params={"license_key": key},
        )
        # FastAPI's Header(...) returns 422 when missing the required header.
        assert resp.status_code in (401, 422)

    def test_list_returns_claimed_seats(self, client, db, admin_token) -> None:
        key = _activate_strict_key(db, seats=3)
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m2"})
        resp = client.get(
            "/v1/seats/list",
            params={"license_key": key},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["seats_total"] == 3
        assert len(body["seats"]) == 2
        machine_ids = {s["machine_id"] for s in body["seats"]}
        assert machine_ids == {"m1", "m2"}


class TestValidateIncludesSeatInfo:
    def test_validate_returns_seats_for_strict_license(self, client, db) -> None:
        key = _activate_strict_key(db, seats=5)
        client.post("/v1/seats/claim", json={"license_key": key, "machine_id": "m1"})
        resp = client.post("/v1/validate", json={"license_key": key})
        assert resp.status_code == 200
        body = resp.json()
        assert body["seats_total"] == 5
        assert body["seats_used"] == 1

    def test_validate_returns_null_seats_for_legacy_pro(self, client, db) -> None:
        """Pre-Strict Pro licenses have no seats metadata → response carries None."""
        key = generate_key()
        key_h = hash_key(key)
        db.execute(
            "INSERT INTO licenses (id, key_hash, license_key_masked, tier, email, "
            "active, metadata, product) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                key_h,
                f"ANMD-****-****-{key.split('-')[3]}",
                "pro",
                "solo@example.com",
                1,
                "{}",
                "anchormd",
            ),
        )
        db.commit()
        resp = client.post("/v1/validate", json={"license_key": key})
        body = resp.json()
        assert body["seats_used"] is None
        assert body["seats_total"] is None

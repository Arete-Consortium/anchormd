"""Tests for the client-side seat claim — Gap 2 of pre-Day-6 cleanup.

The seat-claim module MUST be fire-and-forget. Any condition that would
otherwise raise must silently return so the CLI never blocks on seat-claim
posting.
"""

from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from anchormd.seats import (
    _load_seat_cache,
    _save_seat_cache,
    claim_seat_on_startup,
)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    """Redirect the seat-cache file to a per-test tmp dir."""
    monkeypatch.setattr("anchormd.seats._CACHE_DIR", tmp_path)
    monkeypatch.setattr("anchormd.seats._SEAT_CACHE_FILE", tmp_path / "seat_claim.json")


class TestSeatClaimOptOut:
    def test_no_audit_env_skips_claim(self, monkeypatch) -> None:
        monkeypatch.setenv("ANCHORMD_NO_AUDIT", "1")
        with patch("httpx.post") as mock_post:
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
            mock_post.assert_not_called()

    def test_no_server_url_skips_claim(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.delenv("ANCHORMD_LICENSE_SERVER", raising=False)
        with patch("httpx.post") as mock_post:
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
            mock_post.assert_not_called()


class TestSeatClaimSuccess:
    def test_claim_posts_to_seats_endpoint(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        mock_resp = MagicMock(status_code=200)
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="machine-X"),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
            assert mock_post.called
            url = mock_post.call_args.args[0]
            assert url.endswith("/v1/seats/claim")
            payload = mock_post.call_args.kwargs["json"]
            assert payload["license_key"] == "ANMD-ABCD-EFGH-32E3"
            assert payload["machine_id"] == "machine-X"

    def test_claim_caches_after_success(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        mock_resp = MagicMock(status_code=200)
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="m1"),
            patch("httpx.post", return_value=mock_resp),
        ):
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
        # Second call within 24h should NOT POST again.
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="m1"),
            patch("httpx.post") as mock_post_2,
        ):
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
            mock_post_2.assert_not_called()


class TestSeatClaim409:
    def test_cap_reached_logs_warning_but_does_not_raise(self, monkeypatch, caplog) -> None:
        """Server 409 = team has more machines than seats. CLI keeps working."""
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        mock_resp = MagicMock(
            status_code=409,
            json=MagicMock(return_value={"detail": "Seat cap reached: 5/5."}),
        )
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="m6"),
            patch("httpx.post", return_value=mock_resp),
            caplog.at_level("WARNING"),
        ):
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
        assert any("Seat cap" in rec.message for rec in caplog.records)

    def test_cap_reached_does_not_cache_claim(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        mock_resp = MagicMock(
            status_code=409,
            json=MagicMock(return_value={"detail": "cap"}),
        )
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="m6"),
            patch("httpx.post", return_value=mock_resp),
        ):
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")
        # Cache should not exist — we want to retry next invocation.
        assert _load_seat_cache("ANMD-ABCD-EFGH-32E3", "m6") is False


class TestSeatClaimSilentErrors:
    def test_network_error_is_silent(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        with (
            patch("anchormd.machine_id.get_machine_id", return_value="m1"),
            patch("httpx.post", side_effect=ConnectionError("offline")),
        ):
            # Must not raise.
            claim_seat_on_startup("ANMD-ABCD-EFGH-32E3")


class TestSeatCachePrimitive:
    def test_save_then_load(self, tmp_path, monkeypatch) -> None:
        # Already isolated by the autouse fixture.
        _save_seat_cache("ANMD-ABCD-EFGH-32E3", "machine-A")
        assert _load_seat_cache("ANMD-ABCD-EFGH-32E3", "machine-A") is True

    def test_load_wrong_machine_id_misses(self, tmp_path) -> None:
        _save_seat_cache("ANMD-ABCD-EFGH-32E3", "machine-A")
        assert _load_seat_cache("ANMD-ABCD-EFGH-32E3", "different-machine") is False

    def test_load_expired_misses(self, tmp_path, monkeypatch) -> None:
        # Write a stale cache file directly.
        cache_file = tmp_path / "seat_claim.json"
        cache_file.write_text(
            json.dumps(
                {
                    "license_key": "ANMD-ABCD-EFGH-32E3",
                    "machine_id": "m1",
                    "claimed_at": time.time() - 86400 - 60,  # >24h ago
                }
            )
        )
        assert _load_seat_cache("ANMD-ABCD-EFGH-32E3", "m1") is False


class TestLicenseInfoRoundTrip:
    """LicenseInfo must carry seats_used/seats_total through cache + server flows."""

    def test_validate_response_populates_seats_fields(self) -> None:
        """When the server returns seat info, LicenseInfo carries it."""
        from anchormd.licensing import Tier, _validate_with_server

        mock_resp = MagicMock(
            status_code=200,
            json=MagicMock(
                return_value={
                    "valid": True,
                    "tier": "strict",
                    "email": "t@t.com",
                    "metadata": {},
                    "seats_used": 3,
                    "seats_total": 5,
                }
            ),
        )
        with (
            patch(
                "anchormd.licensing._get_license_server_url",
                return_value="https://example.com",
            ),
            patch("httpx.post", return_value=mock_resp),
        ):
            info = _validate_with_server("ANMD-ABCD-EFGH-32E3")
        assert info is not None
        assert info.tier == Tier.STRICT
        assert info.seats_used == 3
        assert info.seats_total == 5

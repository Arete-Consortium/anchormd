"""Tests for the client-side audit logger.

The logger MUST be fire-and-forget. Any condition that would otherwise raise
must instead silently return so the CLI never blocks on audit posting.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from anchormd.audit_logger import log_command
from anchormd.licensing import LicenseInfo, Tier


def _strict_info() -> LicenseInfo:
    return LicenseInfo(
        tier=Tier.STRICT,
        license_key="ANMD-ABCD-EFGH-32E3",
        valid=True,
    )


def _pro_info() -> LicenseInfo:
    return LicenseInfo(
        tier=Tier.PRO,
        license_key="ANMD-ABCD-EFGH-32E3",
        valid=True,
    )


class TestAuditLoggerOptOut:
    def test_no_audit_env_var_skips_post(self, monkeypatch) -> None:
        monkeypatch.setenv("ANCHORMD_NO_AUDIT", "1")
        with patch("httpx.post") as mock_post:
            log_command("audit")
            mock_post.assert_not_called()

    def test_skips_when_tier_not_strict(self, monkeypatch) -> None:
        """Pro users should never post audit events."""
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        with (
            patch(
                "anchormd.licensing._find_license_key",
                return_value="ANMD-ABCD-EFGH-32E3",
            ),
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_pro_info(),
            ),
            patch("httpx.post") as mock_post,
        ):
            log_command("audit")
            mock_post.assert_not_called()


class TestAuditLoggerStrict:
    def test_posts_when_strict_license_present(self, monkeypatch) -> None:
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        mock_resp = MagicMock(status_code=200)
        with (
            patch(
                "anchormd.licensing._find_license_key",
                return_value="ANMD-ABCD-EFGH-32E3",
            ),
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_strict_info(),
            ),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            log_command("fleet", repo_fingerprint="abc123", metadata={"score": 87})
            assert mock_post.called
            call_args = mock_post.call_args
            assert call_args.args[0].endswith("/v1/audit/log")
            payload = call_args.kwargs["json"]
            assert payload["command"] == "fleet"
            assert payload["repo_fingerprint"] == "abc123"
            assert payload["metadata"] == {"score": 87}


class TestAuditLoggerSwallowsErrors:
    def test_network_error_is_silent(self, monkeypatch) -> None:
        """A network error inside the POST must never propagate."""
        monkeypatch.delenv("ANCHORMD_NO_AUDIT", raising=False)
        monkeypatch.setenv("ANCHORMD_LICENSE_SERVER", "https://example.com")
        with (
            patch(
                "anchormd.licensing._find_license_key",
                return_value="ANMD-ABCD-EFGH-32E3",
            ),
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_strict_info(),
            ),
            patch("httpx.post", side_effect=ConnectionError("offline")),
        ):
            # Must not raise.
            log_command("audit")


class TestCliWireUp:
    """Regression: the audit CLI command must actually call log_command.

    This tripped a Day-3 spec gap where log_command existed but was never
    called from any command — the procurement-grade "every command logged"
    promise on StrictPage was aspirational. These tests prove the wire-up.
    """

    def test_audit_command_calls_log_command(self, tmp_path, monkeypatch) -> None:
        from typer.testing import CliRunner

        from anchormd.cli import app

        # A minimal CLAUDE.md so the audit command doesn't bail before track_command.
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Test\n## Project Overview\nTest project.\n")

        with patch("anchormd.cli._audit_log") as mock_log:
            runner = CliRunner()
            runner.invoke(app, ["audit", str(claude_md)])
            # Audit may exit non-zero due to score thresholds, but log must fire.
            mock_log.assert_called_with("audit")

    def test_fleet_command_calls_log_command(self, tmp_path) -> None:
        from typer.testing import CliRunner

        from anchormd.cli import app

        # fleet --json is Strict-gated; we mock _audit_log to confirm the call
        # happens before the gate. Without --json the gate doesn't trip.
        with patch("anchormd.cli._audit_log") as mock_log:
            runner = CliRunner()
            runner.invoke(app, ["fleet", str(tmp_path)])
            mock_log.assert_called_with("fleet")

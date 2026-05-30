"""Tests for the Strict tier — Day 1 of v0.6.0.

Covers:
1. Tier.STRICT exists and parses
2. STRICT_FEATURES exposes the moved + new features
3. has_feature gates strict-only features by tier
4. require_strict decorator blocks Free
5. require_strict blocks Pro (the no-grandfather decision)
6. require_strict allows Strict
7. get_upgrade_message routes Strict-only features to /strict URL
8. require_pro still works for Pro-only features after refactor
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import typer
from rich.console import Console

from anchormd.gates import require_pro, require_strict
from anchormd.licensing import (
    PRO_FEATURES,
    STRICT_FEATURES,
    TIER_DEFINITIONS,
    LicenseInfo,
    Tier,
    get_upgrade_message,
    has_feature,
    tier_at_least,
)


def _info(tier: Tier) -> LicenseInfo:
    """Build a LicenseInfo at the given tier for mocking."""
    return LicenseInfo(tier=tier, license_key="ANMD-ABCD-EFGH-32E3", valid=True)


class TestStrictTierExists:
    def test_strict_enum_member(self) -> None:
        assert Tier.STRICT == "strict"
        assert Tier("strict") is Tier.STRICT

    def test_strict_in_tier_definitions(self) -> None:
        config = TIER_DEFINITIONS[Tier.STRICT]
        assert config.name == "Strict"
        assert "$49/seat/mo" in config.price_label


class TestStrictFeaturesMembership:
    def test_strict_features_exposes_moved_features(self) -> None:
        # These were Pro features in v0.5.x and moved to Strict.
        for feature in ("ci_integration", "drift_generate", "drift_fix"):
            assert feature in STRICT_FEATURES
            assert feature not in PRO_FEATURES

    def test_strict_features_exposes_new_features(self) -> None:
        for feature in (
            "strict_validation",
            "fleet_json",
            "audit_log",
            "team_seats",
        ):
            assert feature in STRICT_FEATURES


class TestHasFeatureTierGating:
    def test_pro_does_not_have_strict_features(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.PRO),
        ):
            assert has_feature("strict_validation") is False
            assert has_feature("ci_integration") is False
            assert has_feature("drift_generate") is False
            assert has_feature("fleet_json") is False

    def test_strict_has_strict_features(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.STRICT),
        ):
            assert has_feature("strict_validation") is True
            assert has_feature("ci_integration") is True
            assert has_feature("drift_generate") is True
            assert has_feature("fleet_json") is True

    def test_strict_inherits_pro_features(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.STRICT),
        ):
            # Strict subscribers retain everything Pro had.
            assert has_feature("diff") is True
            assert has_feature("tech_debt") is True
            assert has_feature("init_interactive") is True


class TestTierAtLeast:
    def test_free_below_pro(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.FREE),
        ):
            assert tier_at_least(Tier.PRO) is False
            assert tier_at_least(Tier.STRICT) is False

    def test_pro_meets_pro_but_not_strict(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.PRO),
        ):
            assert tier_at_least(Tier.PRO) is True
            assert tier_at_least(Tier.STRICT) is False

    def test_strict_meets_both(self) -> None:
        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.STRICT),
        ):
            assert tier_at_least(Tier.PRO) is True
            assert tier_at_least(Tier.STRICT) is True


class TestRequireStrictDecorator:
    def test_blocks_free(self) -> None:
        @require_strict("ci_integration")
        def gated() -> str:
            return "ran"

        with (
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_info(Tier.FREE),
            ),
            pytest.raises(typer.Exit) as exc,
        ):
            gated()
        assert exc.value.exit_code == 1

    def test_blocks_pro_no_grandfather(self) -> None:
        """v0.6.0 strips ci/drift from Pro. Active Pro subs hit this gate."""

        @require_strict("ci_integration")
        def gated() -> str:
            return "ran"

        with (
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_info(Tier.PRO),
            ),
            pytest.raises(typer.Exit) as exc,
        ):
            gated()
        assert exc.value.exit_code == 1

    def test_allows_strict(self) -> None:
        @require_strict("ci_integration")
        def gated() -> str:
            return "ran"

        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.STRICT),
        ):
            assert gated() == "ran"


class TestUpgradeMessageRouting:
    def test_strict_feature_routes_to_strict_url(self) -> None:
        msg = get_upgrade_message("ci_integration")
        assert "Strict" in msg
        assert "anchormd.dev/strict" in msg
        assert "$49/seat/mo" in msg

    def test_pro_feature_routes_to_pro_url(self) -> None:
        msg = get_upgrade_message("diff")
        assert "Pro" in msg
        assert "anchormd.dev/pro" in msg
        assert "$8/mo" in msg


class TestRequireProStillWorks:
    """Regression: refactor must not break Pro-only gates."""

    def test_pro_gate_allows_pro_user(self, capsys: pytest.CaptureFixture) -> None:
        @require_pro("diff")
        def gated() -> str:
            return "ran"

        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.PRO),
        ):
            assert gated() == "ran"

    def test_pro_gate_blocks_free_user(self) -> None:
        @require_pro("diff")
        def gated() -> str:
            return "ran"

        with (
            patch(
                "anchormd.licensing.get_license_info",
                return_value=_info(Tier.FREE),
            ),
            pytest.raises(typer.Exit),
        ):
            # Silence the Rich console output during the expected exit.
            Console(quiet=True)
            gated()

    def test_pro_gate_allows_strict_user(self) -> None:
        """Strict is a superset of Pro — Strict subs must pass Pro gates."""

        @require_pro("diff")
        def gated() -> str:
            return "ran"

        with patch(
            "anchormd.licensing.get_license_info",
            return_value=_info(Tier.STRICT),
        ):
            assert gated() == "ran"

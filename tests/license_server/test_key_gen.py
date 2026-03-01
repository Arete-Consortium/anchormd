"""Tests for license key generation and hashing utilities."""

from __future__ import annotations

from license_server.key_gen import (
    _compute_check_segment,
    generate_key,
    hash_key,
    mask_key,
    validate_key_checksum,
    validate_key_format,
)


class TestGenerateKey:
    def test_format_valid(self) -> None:
        key = generate_key()
        assert validate_key_format(key)

    def test_checksum_valid(self) -> None:
        key = generate_key()
        assert validate_key_checksum(key)

    def test_starts_with_prefix(self) -> None:
        key = generate_key()
        assert key.startswith("CMDF-")

    def test_four_segments(self) -> None:
        key = generate_key()
        assert len(key.split("-")) == 4

    def test_each_segment_four_chars(self) -> None:
        key = generate_key()
        for part in key.split("-"):
            assert len(part) == 4

    def test_uniqueness(self) -> None:
        keys = {generate_key() for _ in range(50)}
        assert len(keys) == 50

    def test_uppercase(self) -> None:
        key = generate_key()
        assert key == key.upper()


class TestHashKey:
    def test_deterministic(self) -> None:
        h1 = hash_key("CMDF-ABCD-EFGH-54EF")
        h2 = hash_key("CMDF-ABCD-EFGH-54EF")
        assert h1 == h2

    def test_hex_string(self) -> None:
        h = hash_key("CMDF-ABCD-EFGH-54EF")
        int(h, 16)  # raises ValueError if not hex

    def test_64_chars(self) -> None:
        h = hash_key("CMDF-ABCD-EFGH-54EF")
        assert len(h) == 64

    def test_different_keys_different_hashes(self) -> None:
        h1 = hash_key("CMDF-ABCD-EFGH-54EF")
        h2 = hash_key("CMDF-WXYZ-QRST-1234")
        assert h1 != h2

    def test_strips_whitespace(self) -> None:
        h1 = hash_key("CMDF-ABCD-EFGH-54EF")
        h2 = hash_key("  CMDF-ABCD-EFGH-54EF  ")
        assert h1 == h2


class TestMaskKey:
    def test_masks_middle_segments(self) -> None:
        assert mask_key("CMDF-ABCD-EFGH-54EF") == "CMDF-****-****-54EF"

    def test_preserves_last_segment(self) -> None:
        masked = mask_key("CMDF-XXXX-YYYY-ZZZZ")
        assert masked.endswith("ZZZZ")

    def test_invalid_format_gives_full_mask(self) -> None:
        masked = mask_key("garbage")
        assert masked == "CMDF-****-****-****"

    def test_strips_whitespace(self) -> None:
        masked = mask_key("  CMDF-ABCD-EFGH-54EF  ")
        assert masked == "CMDF-****-****-54EF"


class TestValidateKeyFormat:
    def test_valid(self) -> None:
        assert validate_key_format("CMDF-ABCD-EFGH-54EF") is True

    def test_wrong_prefix(self) -> None:
        assert validate_key_format("XXXX-ABCD-EFGH-54EF") is False

    def test_lowercase(self) -> None:
        assert validate_key_format("CMDF-abcd-efgh-54ef") is False

    def test_too_short(self) -> None:
        assert validate_key_format("CMDF-AB-CD") is False

    def test_empty(self) -> None:
        assert validate_key_format("") is False


class TestCheckSegment:
    def test_deterministic(self) -> None:
        s1 = _compute_check_segment("ABCD-EFGH")
        s2 = _compute_check_segment("ABCD-EFGH")
        assert s1 == s2

    def test_four_chars(self) -> None:
        seg = _compute_check_segment("ABCD-EFGH")
        assert len(seg) == 4

    def test_uppercase(self) -> None:
        seg = _compute_check_segment("ABCD-EFGH")
        assert seg == seg.upper()

    def test_different_bodies(self) -> None:
        s1 = _compute_check_segment("ABCD-EFGH")
        s2 = _compute_check_segment("WXYZ-QRST")
        assert s1 != s2

    def test_matches_cli_implementation(self) -> None:
        """Verify server key_gen matches CLI licensing.py."""
        from claudemd_forge.licensing import _compute_check_segment as cli_compute

        body = "ABCD-EFGH"
        assert _compute_check_segment(body) == cli_compute(body)

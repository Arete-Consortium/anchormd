"""License key generation and hashing utilities.

Duplicates the checksum algorithm from claudemd_forge.licensing intentionally —
the server is a separate deployable with no cross-package imports.
"""

from __future__ import annotations

import hashlib
import secrets

_KEY_SALT = "claudemd-forge-v1"


def _compute_check_segment(body: str) -> str:
    """Derive the check segment from the two middle key segments.

    Identical to the CLI-side implementation in licensing.py.
    """
    digest = hashlib.sha256(f"{_KEY_SALT}:{body}".encode()).hexdigest()
    return digest[:4].upper()


def generate_key() -> str:
    """Generate a valid CMDF-XXXX-XXXX-XXXX license key.

    Returns the full plaintext key (only exposed once at activation time).
    """
    seg1 = secrets.token_hex(2).upper()
    seg2 = secrets.token_hex(2).upper()
    body = f"{seg1}-{seg2}"
    check = _compute_check_segment(body)
    return f"CMDF-{seg1}-{seg2}-{check}"


def hash_key(key: str) -> str:
    """Return the SHA-256 hex digest of a plaintext license key.

    Used for database lookups — the plaintext key is never stored.
    """
    return hashlib.sha256(key.strip().encode()).hexdigest()


def mask_key(key: str) -> str:
    """Return a masked version of the key for display/storage.

    CMDF-ABCD-EFGH-54EF -> CMDF-****-****-54EF
    """
    parts = key.strip().split("-")
    if len(parts) != 4:
        return "CMDF-****-****-****"
    return f"CMDF-****-****-{parts[3]}"


def validate_key_format(key: str) -> bool:
    """Check if a key matches CMDF-XXXX-XXXX-XXXX format."""
    key = key.strip()
    if not key.startswith("CMDF-"):
        return False
    parts = key.split("-")
    if len(parts) != 4:
        return False
    for part in parts[1:]:
        if len(part) != 4 or not part.isalnum() or part != part.upper():
            return False
    return True


def validate_key_checksum(key: str) -> bool:
    """Verify the key's check segment matches its body."""
    parts = key.strip().split("-")
    if len(parts) != 4:
        return False
    body = f"{parts[1]}-{parts[2]}"
    expected = _compute_check_segment(body)
    return parts[3] == expected

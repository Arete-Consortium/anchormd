"""Strict-tier client-side seat management.

On first successful Strict validation, posts to /v1/seats/claim to register
this machine_id under the license. Skipped for free/pro users, gated by a
24-hour on-disk cache so we don't re-claim on every command invocation.

Failures are silent (network, server down, cache write) — never blocks the CLI.
A 409 from the server is logged at warning level: the user has more machines
than seats, but their CLI still works (server validation isn't seat-gated).
"""

from __future__ import annotations

import json
import logging
import os
import stat
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("~/.anchormd").expanduser()
_SEAT_CACHE_FILE = _CACHE_DIR / "seat_claim.json"
_CLAIM_CACHE_SECONDS = 86400  # 24 hours
_CLAIM_TIMEOUT_SECONDS = 2.0
_NO_AUDIT_ENV = "ANCHORMD_NO_AUDIT"  # also opts out of seat claims


def _claim_disabled() -> bool:
    """Same opt-out as the audit logger — paranoid environments stay quiet."""
    val = os.environ.get(_NO_AUDIT_ENV, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def _load_seat_cache(license_key: str, machine_id: str) -> bool:
    """Return True if we've successfully claimed within the TTL window."""
    try:
        if not _SEAT_CACHE_FILE.is_file():
            return False
        data = json.loads(_SEAT_CACHE_FILE.read_text())
        if data.get("license_key") != license_key:
            return False
        if data.get("machine_id") != machine_id:
            return False
        claimed_at = data.get("claimed_at", 0)
        return (time.time() - claimed_at) < _CLAIM_CACHE_SECONDS
    except Exception:
        return False


def _save_seat_cache(license_key: str, machine_id: str) -> None:
    """Persist a successful claim so we don't re-POST on every command."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "license_key": license_key,
            "machine_id": machine_id,
            "claimed_at": time.time(),
        }
        _SEAT_CACHE_FILE.write_text(json.dumps(payload))
        _SEAT_CACHE_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except Exception:
        logger.debug("Failed to save seat-claim cache", exc_info=True)


def claim_seat_on_startup(license_key: str) -> None:
    """Best-effort POST to /v1/seats/claim. Idempotent and rate-limited locally.

    Caller's responsibility to confirm tier=Strict before invoking. This module
    won't call get_license_info() itself — that would create a recursion through
    the lazy import in get_license_info → claim_seat_on_startup → get_license_info.
    """
    if _claim_disabled():
        return

    # Lazy imports keep cold-path overhead near zero on opt-out.
    from anchormd.licensing import _get_license_server_url

    server_url = _get_license_server_url()
    if not server_url:
        return

    try:
        from anchormd.machine_id import get_machine_id

        machine_id = get_machine_id()
    except Exception:
        return  # No machine_id, no seat claim possible.

    # Check cache first — avoids hitting the server on every CLI invocation.
    if _load_seat_cache(license_key, machine_id):
        return

    try:
        import httpx
    except ImportError:
        return

    try:
        resp = httpx.post(
            f"{server_url.rstrip('/')}/v1/seats/claim",
            json={"license_key": license_key, "machine_id": machine_id},
            timeout=_CLAIM_TIMEOUT_SECONDS,
        )
    except Exception:
        logger.debug("Seat claim POST failed (non-blocking)", exc_info=True)
        return

    if resp.status_code == 200:
        _save_seat_cache(license_key, machine_id)
        return

    if resp.status_code == 409:
        # Seat cap reached. Server validation is not seat-gated, so the CLI
        # keeps working — but the user should know their team has more
        # machines than seats.
        try:
            detail = resp.json().get("detail", "Seat cap reached")
        except Exception:
            detail = "Seat cap reached"
        logger.warning("anchormd Strict: %s", detail)
        return

    # Other status codes — log at debug, no user-visible noise.
    logger.debug("Seat claim returned %d", resp.status_code)

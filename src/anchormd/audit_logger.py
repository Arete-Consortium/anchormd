"""Strict-tier client-side audit logger.

Posts command events to the license server's /v1/audit/log endpoint.
Fire-and-forget: any failure is swallowed silently — the CLI never blocks
on audit posting.

Disabled when:
- ANCHORMD_NO_AUDIT is set (opt-out for paranoid environments)
- ANCHORMD_LICENSE_SERVER is unset (no server to post to)
- No license key is configured
- The current tier is not Strict (free + pro users skip audit)
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_NO_AUDIT_ENV = "ANCHORMD_NO_AUDIT"
_POST_TIMEOUT_SECONDS = 2.0


def _audit_disabled() -> bool:
    """Check whether the user has opted out via env var."""
    val = os.environ.get(_NO_AUDIT_ENV, "").strip().lower()
    return val in ("1", "true", "yes", "on")


def log_command(
    command: str,
    *,
    event_type: str = "scan",
    repo_fingerprint: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Post a command event to the audit log. Fire-and-forget.

    Returns immediately on any opt-out or failure condition. Network errors
    are logged at debug level only; they never propagate.
    """
    if _audit_disabled():
        return

    # Lazy imports to keep cold-path overhead near zero on opt-out.
    from anchormd.licensing import (
        Tier,
        _find_license_key,
        _get_license_server_url,
        get_license_info,
    )

    server_url = _get_license_server_url()
    if not server_url:
        return

    key = _find_license_key()
    if not key:
        return

    # Audit log is Strict-only — skip for free/pro users.
    if get_license_info().tier != Tier.STRICT:
        return

    try:
        import httpx
    except ImportError:
        return

    try:
        from anchormd.machine_id import get_machine_id

        machine_id = get_machine_id()
    except Exception:
        machine_id = None

    payload = {
        "license_key": key,
        "machine_id": machine_id,
        "event_type": event_type,
        "command": command,
        "repo_fingerprint": repo_fingerprint,
        "metadata": metadata or {},
    }

    try:
        httpx.post(
            f"{server_url.rstrip('/')}/v1/audit/log",
            json=payload,
            timeout=_POST_TIMEOUT_SECONDS,
        )
    except Exception:
        # Fire-and-forget — never block the CLI on audit posting.
        logger.debug("Audit log POST failed (non-blocking)", exc_info=True)

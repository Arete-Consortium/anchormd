"""POST /v1/audit/log, GET /v1/audit/export — Strict-tier audit trail.

Retention: prune_old_events() drops rows older than AUDIT_RETENTION_DAYS.
Called from main.py lifespan startup; no scheduled cron needed.
"""

from __future__ import annotations

import contextlib
import csv
import io
import json
import logging
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from license_server.config import get_admin_secret
from license_server.database import get_connection
from license_server.key_gen import hash_key, mask_key, validate_key_checksum, validate_key_format
from license_server.models import (
    AuditEvent,
    AuditExportResponse,
    AuditLogRequest,
    AuditLogResponse,
)
from license_server.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

_db_path_override = None

# 1 year — locked per spec §Locked decisions #3.
AUDIT_RETENTION_DAYS = 365


def _require_admin(authorization: str = Header(...)) -> str:
    """Verify Bearer token matches the admin secret."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[len("Bearer ") :]
    if token != get_admin_secret():
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return token


def prune_old_events(conn: sqlite3.Connection, retention_days: int = AUDIT_RETENTION_DAYS) -> int:
    """Delete audit events older than retention_days. Returns rows deleted.

    Called at server startup. Cheap — index on created_at handles the range scan.
    """
    cursor = conn.execute(
        "DELETE FROM audit_events WHERE created_at < datetime('now', ?)",
        (f"-{retention_days} days",),
    )
    conn.commit()
    deleted = cursor.rowcount
    if deleted > 0:
        logger.info("Pruned %d audit events older than %d days", deleted, retention_days)
    return deleted


def _resolve_license_id(conn: sqlite3.Connection, license_key: str, product: str):
    """Return (license_id, active) tuple or None."""
    product_aliases = [product]
    if product == "anchormd":
        product_aliases.append("claudemd-forge")
    elif product == "claudemd-forge":
        product_aliases.append("anchormd")

    if not any(validate_key_format(license_key, p) for p in product_aliases):
        return None
    if not any(validate_key_checksum(license_key, p) for p in product_aliases):
        return None

    key_h = hash_key(license_key)
    for product_name in product_aliases:
        row = conn.execute(
            "SELECT id, active FROM licenses WHERE key_hash = ? AND product = ?",
            (key_h, product_name),
        ).fetchone()
        if row is not None:
            return row
    return None


@router.post("/v1/audit/log", response_model=AuditLogResponse)
@limiter.limit("30/minute")
def log_event(req: AuditLogRequest, request: Request) -> AuditLogResponse:
    """Record a client command in the audit trail.

    Fire-and-forget from the client's perspective — a non-200 here never
    blocks the CLI. Unknown licenses get 404 so the client can stop retrying.
    """
    conn = get_connection(_db_path_override)
    row = _resolve_license_id(conn, req.license_key, req.product)
    if row is None or not row["active"]:
        raise HTTPException(status_code=404, detail="License not found or inactive")

    cursor = conn.execute(
        "INSERT INTO audit_events "
        "(license_id, machine_id, event_type, command, repo_fingerprint, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            row["id"],
            req.machine_id,
            req.event_type,
            req.command,
            req.repo_fingerprint,
            json.dumps(req.metadata or {}),
        ),
    )
    conn.commit()

    return AuditLogResponse(logged=True, event_id=cursor.lastrowid)


@router.get("/v1/audit/export")
@limiter.limit("30/minute")
def export_events(
    request: Request,
    license_key: str = Query(..., description="License key to export events for"),
    product: str = Query("anchormd"),
    output_format: str = Query("csv", alias="format", pattern="^(csv|json)$"),
    _token: str = Depends(_require_admin),
):
    """Admin-only: export audit events for a license. CSV or JSON."""
    conn = get_connection(_db_path_override)
    row = _resolve_license_id(conn, license_key, product)
    if row is None:
        raise HTTPException(status_code=404, detail="License not found")

    rows = conn.execute(
        "SELECT id, machine_id, event_type, command, repo_fingerprint, "
        "metadata, created_at FROM audit_events "
        "WHERE license_id = ? ORDER BY created_at ASC",
        (row["id"],),
    ).fetchall()

    masked = mask_key(license_key)

    if output_format == "json":
        events = []
        for r in rows:
            metadata = {}
            if r["metadata"]:
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    metadata = json.loads(r["metadata"])
            events.append(
                AuditEvent(
                    id=r["id"],
                    license_key_masked=masked,
                    machine_id=r["machine_id"],
                    event_type=r["event_type"],
                    command=r["command"],
                    repo_fingerprint=r["repo_fingerprint"],
                    created_at=r["created_at"],
                    metadata=metadata,
                )
            )
        return AuditExportResponse(total=len(events), events=events)

    # CSV (default).
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id",
            "license_key_masked",
            "machine_id",
            "event_type",
            "command",
            "repo_fingerprint",
            "created_at",
            "metadata",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                r["id"],
                masked,
                r["machine_id"] or "",
                r["event_type"],
                r["command"],
                r["repo_fingerprint"] or "",
                r["created_at"],
                r["metadata"] or "{}",
            ]
        )

    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit_{masked}.csv"',
        },
    )

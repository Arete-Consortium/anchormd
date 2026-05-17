"""POST /v1/seats/claim, /v1/seats/release, GET /v1/seats/list — Strict-tier seat management."""

from __future__ import annotations

import contextlib
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from license_server.config import get_admin_secret
from license_server.database import get_connection
from license_server.key_gen import hash_key, mask_key, validate_key_checksum, validate_key_format
from license_server.models import (
    SeatClaimRequest,
    SeatClaimResponse,
    SeatListResponse,
    SeatRecord,
    SeatReleaseRequest,
    SeatReleaseResponse,
)
from license_server.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

_db_path_override = None


def _require_admin(authorization: str = Header(...)) -> str:
    """Verify Bearer token matches the admin secret."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[len("Bearer ") :]
    if token != get_admin_secret():
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return token


def _resolve_license(conn, license_key: str, product: str):
    """Find an active license row by key. Returns sqlite3.Row or None.

    Tries the requested product and its legacy alias.
    """
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
            "SELECT id, tier, active, metadata FROM licenses WHERE key_hash = ? AND product = ?",
            (key_h, product_name),
        ).fetchone()
        if row is not None:
            return row
    return None


def _seats_total(metadata_json: str | None) -> int:
    """Extract seat cap from license metadata. Default = 1 (single-seat legacy)."""
    if not metadata_json:
        return 1
    with contextlib.suppress(json.JSONDecodeError, TypeError, ValueError):
        data = json.loads(metadata_json)
        raw = data.get("seats")
        if raw is None:
            return 1
        seats = int(raw)
        return max(1, seats)
    return 1


def _seats_used(conn, license_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM seats WHERE license_id = ?", (license_id,)
    ).fetchone()[0]


@router.post("/v1/seats/claim", response_model=SeatClaimResponse)
@limiter.limit("60/minute")
def claim_seat(req: SeatClaimRequest, request: Request) -> SeatClaimResponse:
    """Claim a seat for the given machine_id under the license.

    Idempotent: if the machine already holds a seat, refreshes last_seen_at
    and returns claimed=True without counting a new seat.
    Returns HTTP 409 when seats_total is already filled by other machines.
    """
    conn = get_connection(_db_path_override)
    row = _resolve_license(conn, req.license_key, req.product)
    if row is None or not row["active"]:
        raise HTTPException(status_code=404, detail="License not found or inactive")

    license_id = row["id"]
    seats_total = _seats_total(row["metadata"])

    existing = conn.execute(
        "SELECT id FROM seats WHERE license_id = ? AND machine_id = ?",
        (license_id, req.machine_id),
    ).fetchone()

    if existing:
        # Refresh last_seen_at — idempotent claim.
        conn.execute(
            "UPDATE seats SET last_seen_at = datetime('now') WHERE id = ?",
            (existing["id"],),
        )
        conn.commit()
        return SeatClaimResponse(
            claimed=True,
            seats_used=_seats_used(conn, license_id),
            seats_total=seats_total,
            machine_id=req.machine_id,
            license_key_masked=mask_key(req.license_key),
        )

    used = _seats_used(conn, license_id)
    if used >= seats_total:
        raise HTTPException(
            status_code=409,
            detail=f"Seat cap reached: {used}/{seats_total}. Release a seat or upgrade.",
        )

    conn.execute(
        "INSERT INTO seats (license_id, machine_id) VALUES (?, ?)",
        (license_id, req.machine_id),
    )
    conn.commit()

    return SeatClaimResponse(
        claimed=True,
        seats_used=_seats_used(conn, license_id),
        seats_total=seats_total,
        machine_id=req.machine_id,
        license_key_masked=mask_key(req.license_key),
    )


@router.post("/v1/seats/release", response_model=SeatReleaseResponse)
@limiter.limit("60/minute")
def release_seat(req: SeatReleaseRequest, request: Request) -> SeatReleaseResponse:
    """Release a seat. Idempotent — releasing an unclaimed seat returns released=False."""
    conn = get_connection(_db_path_override)
    row = _resolve_license(conn, req.license_key, req.product)
    if row is None:
        raise HTTPException(status_code=404, detail="License not found")

    license_id = row["id"]
    seats_total = _seats_total(row["metadata"])

    cursor = conn.execute(
        "DELETE FROM seats WHERE license_id = ? AND machine_id = ?",
        (license_id, req.machine_id),
    )
    conn.commit()
    released = cursor.rowcount > 0

    return SeatReleaseResponse(
        released=released,
        seats_used=_seats_used(conn, license_id),
        seats_total=seats_total,
    )


@router.get("/v1/seats/list", response_model=SeatListResponse)
@limiter.limit("60/minute")
def list_seats(
    request: Request,
    license_key: str = Query(..., description="License key to inspect"),
    product: str = Query("anchormd"),
    _token: str = Depends(_require_admin),
) -> SeatListResponse:
    """Admin-only: list all seats claimed under a license."""
    conn = get_connection(_db_path_override)
    row = _resolve_license(conn, license_key, product)
    if row is None:
        raise HTTPException(status_code=404, detail="License not found")

    license_id = row["id"]
    seats_total = _seats_total(row["metadata"])

    rows = conn.execute(
        "SELECT machine_id, claimed_at, last_seen_at FROM seats "
        "WHERE license_id = ? ORDER BY claimed_at ASC",
        (license_id,),
    ).fetchall()

    seats = [
        SeatRecord(
            machine_id=r["machine_id"],
            claimed_at=r["claimed_at"],
            last_seen_at=r["last_seen_at"],
        )
        for r in rows
    ]

    return SeatListResponse(
        license_key_masked=mask_key(license_key),
        seats_total=seats_total,
        seats=seats,
    )

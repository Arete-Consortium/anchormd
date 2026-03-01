"""POST /v1/activate — Create and activate a new license key."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from license_server.config import get_admin_secret
from license_server.database import get_connection
from license_server.key_gen import generate_key, hash_key, mask_key, validate_key_checksum
from license_server.models import ActivateRequest, ActivateResponse, ErrorResponse
from license_server.rate_limit import limiter

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


@router.post(
    "/v1/activate",
    response_model=ActivateResponse,
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
def activate(
    req: ActivateRequest,
    request: Request,
    _token: str = Depends(_require_admin),
) -> ActivateResponse:
    """Create a new license key and activate it."""
    conn = get_connection(_db_path_override)

    key = generate_key()

    if not validate_key_checksum(key):
        raise HTTPException(status_code=500, detail="Generated key failed validation")

    key_h = hash_key(key)

    # Prevent duplicate key hash (astronomically unlikely but safe).
    existing = conn.execute("SELECT id FROM licenses WHERE key_hash = ?", (key_h,)).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Key collision — please retry")

    license_id = str(uuid.uuid4())
    masked = mask_key(key)

    conn.execute(
        "INSERT INTO licenses (id, key_hash, license_key_masked, tier, email, active, metadata) "
        "VALUES (?, ?, ?, ?, ?, 1, ?)",
        (license_id, key_h, masked, req.tier, req.email, json.dumps(req.metadata)),
    )
    conn.commit()

    row = conn.execute(
        "SELECT created_at, expires_at FROM licenses WHERE id = ?", (license_id,)
    ).fetchone()

    return ActivateResponse(
        license_key=key,
        tier=req.tier,
        email=req.email,
        active=True,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
    )

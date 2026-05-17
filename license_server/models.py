"""Pydantic v2 request/response models for the license server."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

VALID_PRODUCTS = frozenset(
    {
        "anchormd",
        "agent-lint",
        "ai-spend",
        "promptctl",
        "context-hygiene",
        "auditchain",
    }
)

# --- Requests ---


class ActivateRequest(BaseModel):
    """Request body for POST /v1/activate."""

    email: str
    tier: str = "pro"
    product: str = "anchormd"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidateRequest(BaseModel):
    """Request body for POST /v1/validate."""

    license_key: str
    product: str = "anchormd"
    machine_id: str | None = None


# --- Responses ---


class HealthResponse(BaseModel):
    """Response for GET /v1/health."""

    status: str = "ok"
    version: str
    total_licenses: int = 0
    active_licenses: int = 0


class ActivateResponse(BaseModel):
    """Response for POST /v1/activate."""

    license_key: str
    tier: str
    product: str
    email: str
    active: bool = True
    created_at: str
    expires_at: str | None = None


class ValidateResponse(BaseModel):
    """Response for POST /v1/validate."""

    valid: bool
    tier: str
    product: str = "anchormd"
    active: bool = False
    email: str | None = None
    expires_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Seat info — populated for Strict licenses; None on legacy/Pro keys.
    seats_used: int | None = None
    seats_total: int | None = None


class RevokeRequest(BaseModel):
    """Request body for POST /v1/revoke."""

    license_key: str
    product: str = "anchormd"


class RevokeResponse(BaseModel):
    """Response for POST /v1/revoke."""

    revoked: bool
    license_key_masked: str
    product: str = "anchormd"
    email: str | None = None
    revoked_at: str


class UsageRecordRequest(BaseModel):
    """Request body for POST /v1/usage — record a scan."""

    license_key: str
    product: str = "anchormd"
    scan_type: str = "deep_scan"  # 'audit' or 'deep_scan'
    repo_fingerprint: str | None = None  # hash of repo URL/path


class UsageCheckRequest(BaseModel):
    """Request body for POST /v1/usage/check — check remaining quota."""

    license_key: str
    product: str = "anchormd"
    scan_type: str = "deep_scan"


class UsageResponse(BaseModel):
    """Response for usage endpoints."""

    scan_type: str
    used: int = 0
    limit: int = 0
    remaining: int = 0
    period: str = ""  # 'YYYY-MM'
    allowed: bool = True


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    detail: str | None = None


# --- Seats (Strict tier) ---


class SeatClaimRequest(BaseModel):
    """Request body for POST /v1/seats/claim."""

    license_key: str
    machine_id: str
    product: str = "anchormd"


class SeatClaimResponse(BaseModel):
    """Response for POST /v1/seats/claim."""

    claimed: bool
    seats_used: int
    seats_total: int
    machine_id: str
    license_key_masked: str | None = None


class SeatReleaseRequest(BaseModel):
    """Request body for POST /v1/seats/release."""

    license_key: str
    machine_id: str
    product: str = "anchormd"


class SeatReleaseResponse(BaseModel):
    """Response for POST /v1/seats/release."""

    released: bool
    seats_used: int
    seats_total: int


class SeatRecord(BaseModel):
    """A single seat row."""

    machine_id: str
    claimed_at: str
    last_seen_at: str


class SeatListResponse(BaseModel):
    """Response for GET /v1/seats/list — admin only."""

    license_key_masked: str
    seats_total: int
    seats: list[SeatRecord] = Field(default_factory=list)


# --- Audit log (Strict tier) ---


class AuditLogRequest(BaseModel):
    """Request body for POST /v1/audit/log — fire-and-forget client event."""

    license_key: str
    machine_id: str | None = None
    event_type: str = "scan"
    command: str
    repo_fingerprint: str | None = None
    product: str = "anchormd"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogResponse(BaseModel):
    """Response for POST /v1/audit/log."""

    logged: bool
    event_id: int | None = None


class AuditEvent(BaseModel):
    """A single audit log row."""

    id: int
    license_key_masked: str
    machine_id: str | None
    event_type: str
    command: str
    repo_fingerprint: str | None
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditExportResponse(BaseModel):
    """Response for GET /v1/audit/export when JSON requested."""

    total: int
    events: list[AuditEvent] = Field(default_factory=list)

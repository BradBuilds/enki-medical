"""
Admin endpoints: challenge issuance, device enrollment.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Literal

from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from storage.auth.config import CHALLENGE_TTL_SECONDS
from storage.auth.grant import issue_device_grant, DeviceTier, Algorithm
from storage.auth.challenge_store import InMemoryChallengeStore

from services.api.src.deps import (
    authenticate_request,
    get_challenge_store,
    get_grant_store,
    get_root_key,
    get_root_public_key_raw,
    raise_enki_error,
    sha256_hex,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/challenges/issue")
def issue_challenge(
    request: Request,
    device_id: str = Query(...),
):
    """Issue an authentication challenge for a device (public endpoint)."""
    challenge_store = request.app.state.challenge_store  # type: ignore[attr-defined]

    c = challenge_store.issue(device_id=device_id, ttl_seconds=CHALLENGE_TTL_SECONDS)
    return JSONResponse(
        {
            "challenge_id": c.challenge_id,
            "nonce": c.nonce,
            "issued_at": c.issued_at.isoformat(),
            "expires_at": c.expires_at.isoformat(),
        }
    )


class DeviceEnrollmentRequest(BaseModel):
    """
    EMULATED mode enrollment request.

    NOTE: explicit_tier is REQUIRED in EMULATED mode per governance corrections.
    PRODUCTION mode may add attestation inputs when VERIFY_ATTESTATION=True.
    """
    device_id: str
    public_key: str  # base64
    public_key_algorithm: Algorithm
    tenant_scopes: list[str]
    explicit_tier: DeviceTier = Field(..., description="Required in EMULATED mode")
    expires_days: int = Field(365, ge=1, le=3650)
    metadata: Optional[dict[str, Any]] = None


@router.post("/enroll_device")
async def enroll_device(
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-ID"),
    x_challenge_id: str = Header(..., alias="X-Challenge-ID"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_body_sha256: str = Header(..., alias="X-Body-SHA256"),
    x_signature: str = Header(..., alias="X-Signature"),
):
    """
    Enroll a device (Tier K required).

    Auth headers are validated against exact raw request bytes.
    """
    body = await request.body()

    # Strict: header hash must match raw bytes on wire
    computed = sha256_hex(body)
    if computed != x_body_sha256:
        raise_enki_error("INGEST.BODY_HASH_MISMATCH", "Body hash mismatch")

    grant_store = request.app.state.grant_store  # type: ignore[attr-defined]
    challenge_store = request.app.state.challenge_store  # type: ignore[attr-defined]
    root_public_key_raw = request.app.state.root_public_key_raw  # type: ignore[attr-defined]
    root_key = request.app.state.root_key  # type: ignore[attr-defined]

    auth = authenticate_request(
        request=request,
        body=body,
        x_device_id=x_device_id,
        x_challenge_id=x_challenge_id,
        x_tenant_id=x_tenant_id,
        x_body_sha256=x_body_sha256,
        x_signature=x_signature,
        grant_store=grant_store,
        challenge_store=challenge_store,
        root_public_key_raw=root_public_key_raw,
    )

    if not auth.success:
        raise_enki_error(auth.reason or "AUTH.VERIFICATION_ERROR", "Authentication failed")

    # Tier-K gate (policy at route level)
    if auth.device_tier != "K":
        raise_enki_error("AUTH.ADMIN_TIER_REQUIRED", "Admin enrollment requires Tier K")

    # Parse request body
    try:
        payload = DeviceEnrollmentRequest.model_validate_json(body)
    except Exception as e:
        raise_enki_error("API.BAD_REQUEST", f"Invalid enrollment payload: {e}")

    # Issue grant for new device
    try:
        public_key_bytes = base64.b64decode(payload.public_key)
    except Exception:
        raise_enki_error("API.BAD_REQUEST", "public_key must be valid base64")

    expires_at = (datetime.now(timezone.utc) + timedelta(days=payload.expires_days)).isoformat()

    grant = issue_device_grant(
        device_id=payload.device_id,
        public_key_bytes=public_key_bytes,
        public_key_algorithm=payload.public_key_algorithm,
        device_tier=payload.explicit_tier,
        tenant_scopes=payload.tenant_scopes,
        root_key=root_key,
        expires_at=expires_at,
    )

    grant_store.save(grant)

    return JSONResponse(grant.to_dict())

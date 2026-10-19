"""
Ingestion endpoint: POST /ingest/events with auth + tier enforcement.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from storage.ingest.ingestion import ingest_jsonl

from services.api.src.deps import (
    authenticate_request,
    raise_enki_error,
    sha256_hex,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


def _enforce_tier_w_connector_policy(*, device_id: str, events: list[dict[str, Any]]) -> None:
    """
    Tier W policy enforcement is route-level.

    This skeleton tries to use storage.connectors.registry.get_connector_config()
    if present. If your repo doesn't include that module yet, we fail loudly with
    an explicit error code rather than silently skipping enforcement.
    """
    try:
        from storage.connectors.registry import get_connector_config  # type: ignore
    except Exception:
        raise_enki_error(
            "CONNECTOR.MODULE_MISSING",
            "Tier W enforcement requires storage.connectors.registry.get_connector_config()",
        )

    connector = get_connector_config(device_id)

    # Connector must be in write-enabled state
    if getattr(connector, "state", None) not in ["VERIFIED_RAW", "ACTIVE_PROJECTION"]:
        raise_enki_error(
            "CONNECTOR.STATE_FORBIDS_WRITE",
            f"Connector state {getattr(connector, 'state', None)} does not allow writes",
        )

    allowed = set(getattr(connector, "allowed_event_types", []) or [])

    for ev in events:
        event_type = ev.get("event_type")
        if not event_type:
            continue

        # Tier W cannot submit assertions
        if event_type.startswith("assertion."):
            raise_enki_error(
                "CONNECTOR.EVENT_NOT_ALLOWED",
                "Tier W devices cannot submit assertions",
            )

        # Tier W must stay within allowlist
        if allowed and event_type not in allowed:
            raise_enki_error(
                "CONNECTOR.EVENT_NOT_ALLOWED",
                f"Event type {event_type} not in connector allowlist",
            )


@router.post("/events")
async def ingest_events(
    request: Request,
    x_device_id: str = Header(..., alias="X-Device-ID"),
    x_challenge_id: str = Header(..., alias="X-Challenge-ID"),
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    x_body_sha256: str = Header(..., alias="X-Body-SHA256"),
    x_signature: str = Header(..., alias="X-Signature"),
):
    body = await request.body()

    # Hash must match exact bytes on the wire
    computed = sha256_hex(body)
    if computed != x_body_sha256:
        raise_enki_error("INGEST.BODY_HASH_MISMATCH", "Body hash mismatch")

    grant_store = request.app.state.grant_store  # type: ignore[attr-defined]
    challenge_store = request.app.state.challenge_store  # type: ignore[attr-defined]
    root_public_key_raw = request.app.state.root_public_key_raw  # type: ignore[attr-defined]

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

    # Parse JSONL (Phase 3 expects list[str])
    jsonl_lines = body.decode("utf-8").splitlines()

    # Tier W enforcement (route-level policy)
    if auth.device_tier == "W":
        events = [json.loads(line) for line in jsonl_lines if line.strip()]
        _enforce_tier_w_connector_policy(device_id=x_device_id, events=events)

    # Phase 3 ingestion (LOCKED)
    receipt = ingest_jsonl(jsonl_lines, x_tenant_id)
    return JSONResponse(receipt)

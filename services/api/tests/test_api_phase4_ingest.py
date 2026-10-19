"""
Phase 4 Integration Tests: Event Ingestion

Tests POST /ingest/events with authentication and tier enforcement.
"""

import pytest
import json
import time
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
from services.api.tests.helpers import (
    create_test_client,
    authenticated_post,
    load_admin_device_key,
    issue_challenge,
    build_auth_headers,
    sha256_hex,
    generate_device_keypair,
    issue_signed_grant,
    save_grant,
    delete_grant,
)


@pytest.fixture
def client():
    return create_test_client()


@pytest.fixture
def admin_key():
    return load_admin_device_key()


@pytest.mark.db
def test_authenticated_ingestion_succeeds(client, admin_key):
    """Authenticated ingestion with valid grant should succeed."""
    # Create a minimal audit event
    events = [
        {
            "event_type": "test.integration",
            "event_time": "2026-01-06T12:00:00Z",
            "actor": "test_runner",
            "severity": "info",
        }
    ]
    
    jsonl = "\n".join(json.dumps(e) for e in events)
    
    response = authenticated_post(
        client,
        "/ingest/events",
        device_id="example-admin-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=jsonl.encode("utf-8"),
    )
    
    # TODO: Check exact success response format once Phase 3 integration is complete
    # For now, verify it's not an auth error
    assert response.status_code != 401
    assert response.status_code != 403


def test_invalid_signature_fails(client, admin_key):
    """Request with tampered signature should fail with AUTH.SIGNATURE_INVALID."""
    events = [{"event_type": "test.integration"}]
    jsonl = json.dumps(events[0])
    body_bytes = jsonl.encode("utf-8")
    
    # Issue challenge
    challenge = issue_challenge(client, "example-admin-device")
    
    # Build valid headers
    headers = build_auth_headers(
        device_id="example-admin-device",
        challenge_id=challenge["challenge_id"],
        tenant_id="practice-001",
        method="POST",
        path="/ingest/events",
        body=body_bytes,
        private_key=admin_key,
        nonce=challenge["nonce"],
        issued_at=challenge["issued_at"],
        expires_at=challenge["expires_at"],
    )
    
    # Tamper with signature
    headers["X-Signature"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
    
    response = client.post("/ingest/events", content=body_bytes, headers=headers)
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "AUTH.SIGNATURE_INVALID"


def test_body_hash_mismatch_fails(client, admin_key):
    """Request with wrong body hash should fail with INGEST.BODY_HASH_MISMATCH."""
    events = [{"event_type": "test.integration"}]
    jsonl = json.dumps(events[0])
    body_bytes = jsonl.encode("utf-8")
    
    # Issue challenge
    challenge = issue_challenge(client, "example-admin-device")
    
    # Build headers with WRONG body hash
    headers = build_auth_headers(
        device_id="example-admin-device",
        challenge_id=challenge["challenge_id"],
        tenant_id="practice-001",
        method="POST",
        path="/ingest/events",
        body=b"different body",  # Wrong body for hash computation
        private_key=admin_key,
        nonce=challenge["nonce"],
        issued_at=challenge["issued_at"],
        expires_at=challenge["expires_at"],
    )
    
    # Send actual body (mismatch)
    response = client.post("/ingest/events", content=body_bytes, headers=headers)
    
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["error_code"] == "INGEST.BODY_HASH_MISMATCH"


def test_expired_challenge_fails(client, admin_key):
    """Request with expired challenge should fail with AUTH.CHALLENGE_EXPIRED."""
    events = [{"event_type": "test.integration"}]
    jsonl = json.dumps(events[0])
    body_bytes = jsonl.encode("utf-8")
    
    # Issue challenge at current time
    initial_time = datetime.now(timezone.utc)
    with freeze_time(initial_time):
        challenge = issue_challenge(client, "example-admin-device")
    
    # Fast-forward 6 minutes (past the 5-minute CHALLENGE_TTL_SECONDS)
    expired_time = initial_time + timedelta(minutes=6)
    with freeze_time(expired_time):
        # Build auth headers manually using the expired challenge
        headers = build_auth_headers(
            device_id="example-admin-device",
            challenge_id=challenge["challenge_id"],
            tenant_id="practice-001",
            method="POST",
            path="/ingest/events",
            body=body_bytes,
            private_key=admin_key,
            nonce=challenge["nonce"],
            issued_at=challenge["issued_at"],
            expires_at=challenge["expires_at"],
        )
        headers["Content-Type"] = "application/json"
        
        # Try to use the expired challenge
        response = client.post("/ingest/events", content=body_bytes, headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert data["detail"]["error_code"] == "AUTH.CHALLENGE_EXPIRED"


def test_device_not_enrolled_fails(client, admin_key):
    """Request from non-enrolled device should fail with AUTH.DEVICE_NOT_ENROLLED."""
    events = [{"event_type": "test.integration"}]
    jsonl = json.dumps(events[0])
    
    # Use a device ID that doesn't have a grant
    response = authenticated_post(
        client,
        "/ingest/events",
        device_id="non-existent-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=jsonl.encode("utf-8"),
    )
    
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "AUTH.DEVICE_NOT_ENROLLED"


def test_tenant_scope_forbidden_fails(client, admin_key):
    """Request for tenant not in grant scopes should fail with TENANT.SCOPE_FORBIDDEN."""
    events = [{"event_type": "test.integration"}]
    jsonl = json.dumps(events[0])
    
    # Admin grant has scope "enki-test", request different tenant
    response = authenticated_post(
        client,
        "/ingest/events",
        device_id="example-admin-device",
        tenant_id="unauthorized-tenant",
        private_key=admin_key,
        body=jsonl.encode("utf-8"),
    )
    
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["error_code"] == "TENANT.SCOPE_FORBIDDEN"


def test_tier_w_cannot_submit_assertions(client, admin_key):
    """Tier W device should be blocked from submitting assertion events."""
    device_id = "tierw-device-001"
    priv = generate_device_keypair()

    # Issue and save a Tier W grant scoped to practice-001
    grant = issue_signed_grant(
        device_id=device_id,
        private_key=priv,
        device_tier="W",
        tenant_scopes=["practice-001"],
    )
    try:
        save_grant(grant)

        # Build a single assertion event (JSONL line)
        event = {"event_type": "assertion.instance.created", "actor": "tester"}
        body_bytes = json.dumps(event).encode("utf-8")

        # Issue challenge and build headers
        challenge = issue_challenge(client, device_id)
        headers = build_auth_headers(
            device_id=device_id,
            challenge_id=challenge["challenge_id"],
            tenant_id="practice-001",
            method="POST",
            path="/ingest/events",
            body=body_bytes,
            private_key=priv,
            nonce=challenge["nonce"],
            issued_at=challenge["issued_at"],
            expires_at=challenge["expires_at"],
        )
        headers["Content-Type"] = "application/json"

        resp = client.post("/ingest/events", content=body_bytes, headers=headers)
        assert resp.status_code == 403
        data = resp.json()
        assert data["detail"]["error_code"] == "CONNECTOR.EVENT_NOT_ALLOWED"
    finally:
        delete_grant(device_id)


@pytest.mark.db
def test_tier_w_respects_allowlist(client, admin_key):
    """Tier W device should only submit events in connector allowlist."""
    from pathlib import Path
    # Prepare device and grant
    device_id = "tierw-device-allowlist"
    priv = generate_device_keypair()
    grant = issue_signed_grant(
        device_id=device_id,
        private_key=priv,
        device_tier="W",
        tenant_scopes=["practice-001"],
    )

    # Update connectors config to allow only a specific event for this device
    cfg_path = Path("storage/connectors/config.json")
    cfg = {
        "connectors_enabled": True,
        "default_state": "ACTIVE_PROJECTION",
        "assertion_submission_allowed_for_tiers": ["K"],
        "global_allowed_event_types": [],
        "device_overrides": {
            device_id: {
                "state": "ACTIVE_PROJECTION",
                "allowed_event_types": ["audit.allowed"],
            }
        },
    }

    try:
        # Save grant and config
        save_grant(grant)
        cfg_path.write_text(json.dumps(cfg, separators=(",", ":")), encoding="utf-8")

        # First, try disallowed event -> should be blocked
        ev_disallowed = {"event_type": "audit.disallowed"}
        body_disallowed = json.dumps(ev_disallowed).encode("utf-8")
        challenge = issue_challenge(client, device_id)
        headers = build_auth_headers(
            device_id=device_id,
            challenge_id=challenge["challenge_id"],
            tenant_id="practice-001",
            method="POST",
            path="/ingest/events",
            body=body_disallowed,
            private_key=priv,
            nonce=challenge["nonce"],
            issued_at=challenge["issued_at"],
            expires_at=challenge["expires_at"],
        )
        headers["Content-Type"] = "application/json"
        r1 = client.post("/ingest/events", content=body_disallowed, headers=headers)
        assert r1.status_code == 403
        assert r1.json()["detail"]["error_code"] == "CONNECTOR.EVENT_NOT_ALLOWED"

        # Next, try allowed event -> should not be blocked by allowlist
        ev_allowed = {"event_type": "audit.allowed"}
        body_allowed = json.dumps(ev_allowed).encode("utf-8")
        challenge2 = issue_challenge(client, device_id)
        headers2 = build_auth_headers(
            device_id=device_id,
            challenge_id=challenge2["challenge_id"],
            tenant_id="practice-001",
            method="POST",
            path="/ingest/events",
            body=body_allowed,
            private_key=priv,
            nonce=challenge2["nonce"],
            issued_at=challenge2["issued_at"],
            expires_at=challenge2["expires_at"],
        )
        headers2["Content-Type"] = "application/json"
        r2 = client.post("/ingest/events", content=body_allowed, headers=headers2)
        # Success path may vary; ensure it's not our allowlist denial
        assert not (r2.status_code == 403 and r2.json()["detail"]["error_code"] == "CONNECTOR.EVENT_NOT_ALLOWED")
    finally:
        delete_grant(device_id)
        # best-effort cleanup of config change: restore minimal default
        cfg_path.write_text(
            json.dumps(
                {
                    "connectors_enabled": True,
                    "default_state": "ACTIVE_PROJECTION",
                    "assertion_submission_allowed_for_tiers": ["K"],
                    "global_allowed_event_types": [],
                    "device_overrides": {},
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )

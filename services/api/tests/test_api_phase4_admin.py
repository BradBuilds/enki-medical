"""
Phase 4 Integration Tests: Admin Enrollment

Tests POST /admin/enroll_device (Tier K required).
"""

import pytest
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from services.api.tests.helpers import (
    create_test_client,
    authenticated_post,
    load_admin_device_key,
    generate_device_keypair,
    issue_signed_grant,
    list_grant_files,
)


@pytest.fixture
def client():
    return create_test_client()


@pytest.fixture
def admin_key():
    return load_admin_device_key()


def test_tier_k_can_enroll_device(client, admin_key):
    """Tier K admin should be able to enroll a new device."""
    # Generate a new device key for enrollment
    new_device_key = Ed25519PrivateKey.generate()
    new_device_pubkey = new_device_key.public_key().public_bytes_raw()
    
    enrollment_request = {
        "device_id": "test-laptop-001",
        "public_key": base64.b64encode(new_device_pubkey).decode("ascii"),
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        "explicit_tier": "P",  # Laptop is Tier P
        "expires_days": 365,
    }
    
    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id="example-admin-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=enrollment_request,
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify grant structure
    assert data["device_id"] == "test-laptop-001"
    assert data["device_tier"] == "P"
    assert "grant_id" in data
    assert "enki_signature" in data
    assert "practice-001" in data["tenant_scopes"]


def test_tier_p_cannot_enroll_device(client, admin_key):
    """Tier P device should be rejected from enrolling (requires Tier K)."""
    # Create a Tier P device with a valid, unexpired grant
    tier_p_device_id = "test-tierp-001"
    tier_p_key = generate_device_keypair()
    tier_p_pub = tier_p_key.public_key().public_bytes_raw()
    future_expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    issue_signed_grant(
        device_id=tier_p_device_id,
        public_key_bytes=tier_p_pub,
        device_tier="P",
        tenant_scopes=["practice-001"],
        expires_at_iso=future_expiry,
    )

    before = list_grant_files()

    enrollment_request = {
        "device_id": "test-deny-target",
        "public_key": base64.b64encode(tier_p_pub).decode("ascii"),
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        "explicit_tier": "P",
        "expires_days": 365,
    }

    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id=tier_p_device_id,
        tenant_id="practice-001",
        private_key=tier_p_key,
        body=enrollment_request,
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "AUTH.ADMIN_TIER_REQUIRED"

    after = list_grant_files()
    assert after == before, "Grant set changed; Tier P should not enroll devices"


def test_enrolled_device_grant_persists(client, admin_key):
    """Enrolled device grant should persist to filesystem."""
    new_device_key = Ed25519PrivateKey.generate()
    new_device_pubkey = new_device_key.public_key().public_bytes_raw()
    
    device_id = "test-persistent-001"
    
    enrollment_request = {
        "device_id": device_id,
        "public_key": base64.b64encode(new_device_pubkey).decode("ascii"),
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        "explicit_tier": "P",
        "expires_days": 365,
    }
    
    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id="example-admin-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=enrollment_request,
    )
    
    assert response.status_code == 200
    
    # Verify grant file exists
    from storage.auth.config import GRANTS_DIR
    grant_path = Path(GRANTS_DIR) / f"{device_id}.json"
    assert grant_path.exists(), f"Grant file not found at {grant_path}"
    
    # Verify grant contents
    with open(grant_path) as f:
        stored_grant = json.load(f)
    
    assert stored_grant["device_id"] == device_id
    assert stored_grant["device_tier"] == "P"


def test_invalid_public_key_fails(client, admin_key):
    """Enrollment with invalid public key should fail with API.BAD_REQUEST."""
    enrollment_request = {
        "device_id": "test-invalid-key",
        "public_key": "NOT-VALID-BASE64!!!",
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        "explicit_tier": "P",
        "expires_days": 365,
    }
    
    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id="example-admin-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=enrollment_request,
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "API.BAD_REQUEST"


def test_missing_explicit_tier_fails(client, admin_key):
    """Enrollment without explicit_tier should fail in EMULATED mode."""
    new_device_key = Ed25519PrivateKey.generate()
    new_device_pubkey = new_device_key.public_key().public_bytes_raw()
    
    enrollment_request = {
        "device_id": "test-no-tier",
        "public_key": base64.b64encode(new_device_pubkey).decode("ascii"),
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        # explicit_tier omitted
        "expires_days": 365,
    }
    
    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id="example-admin-device",
        tenant_id="practice-001",
        private_key=admin_key,
        body=enrollment_request,
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == "API.BAD_REQUEST"
    assert "Invalid enrollment payload" in data["detail"]["detail"]


def test_expired_grant_cannot_enroll(client, admin_key):
    """Device with expired grant should fail enrollment."""
    expired_device_id = "test-expired-001"
    expired_key = generate_device_keypair()
    expired_pub = expired_key.public_key().public_bytes_raw()
    past_expiry = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    issue_signed_grant(
        device_id=expired_device_id,
        public_key_bytes=expired_pub,
        device_tier="P",
        tenant_scopes=["practice-001"],
        expires_at_iso=past_expiry,
    )

    before = list_grant_files()

    enrollment_request = {
        "device_id": "test-expired-target",
        "public_key": base64.b64encode(expired_pub).decode("ascii"),
        "public_key_algorithm": "Ed25519",
        "tenant_scopes": ["practice-001"],
        "explicit_tier": "P",
        "expires_days": 365,
    }

    response = authenticated_post(
        client,
        "/admin/enroll_device",
        device_id=expired_device_id,
        tenant_id="practice-001",
        private_key=expired_key,
        body=enrollment_request,
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["error_code"] == "AUTH.GRANT_EXPIRED"

    after = list_grant_files()
    assert after == before, "Grant set changed; expired device should not enroll"

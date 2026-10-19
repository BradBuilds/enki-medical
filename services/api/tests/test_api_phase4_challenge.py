"""
Phase 4 Integration Tests: Challenge Issuance

Tests GET /admin/challenges/issue (no authentication required).
"""

import pytest
from services.api.tests.helpers import create_test_client, issue_challenge


def test_challenge_issuance_succeeds():
    """Challenge issuance should succeed without authentication."""
    client = create_test_client()
    
    response = client.get("/admin/challenges/issue?device_id=test-device-001")
    
    assert response.status_code == 200
    data = response.json()
    
    # All required fields present
    assert "challenge_id" in data
    assert "nonce" in data
    assert "issued_at" in data
    assert "expires_at" in data


def test_challenge_fields_are_valid():
    """Challenge response should have valid field types."""
    client = create_test_client()
    
    challenge = issue_challenge(client, "test-device-002")
    
    # Nonce should be base64 (at least 16 bytes decoded)
    import base64
    nonce_bytes = base64.b64decode(challenge["nonce"])
    assert len(nonce_bytes) >= 16, "Nonce must be at least 16 bytes"
    
    # Timestamps should be ISO 8601
    from datetime import datetime
    issued_at = datetime.fromisoformat(challenge["issued_at"].replace("Z", "+00:00"))
    expires_at = datetime.fromisoformat(challenge["expires_at"].replace("Z", "+00:00"))
    
    # Expires after issued
    assert expires_at > issued_at, "Challenge must expire after issuance"

"""
Phase 4 Integration Tests: Query Endpoints

Tests GET /query/assertions (implemented, auth-wired).
"""

import pytest
from services.api.tests.helpers import (
    create_test_client,
    authenticated_get,
    load_admin_device_key,
)


@pytest.fixture
def client():
    return create_test_client()


@pytest.fixture
def admin_key():
    return load_admin_device_key()


@pytest.mark.db
@pytest.mark.db
def test_authenticated_query_returns_assertion_events(client, admin_key):
    """Query endpoint should return only assertion.* events."""
    # Ingest some events for practice-001
    from storage import ingest_jsonl
    import json
    tenant = "practice-001"
    lines = [
        json.dumps({"event_id": "q1", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {}}),
        json.dumps({"event_id": "q2", "event_type": "pack.loaded", "timestamp": "2026-01-07T10:00:01Z", "sequence": 2, "severity": "info", "scope": "local", "metadata": {}}),
    ]
    ingest_jsonl(lines, tenant)

    response = authenticated_get(
        client,
        "/query/assertions",
        device_id="example-admin-device",
        tenant_id=tenant,
        private_key=admin_key,
    )

    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert all(evt["event_type"].startswith("assertion.") for evt in data["events"]) 


def test_unauthenticated_query_fails(client):
    """Query without auth headers should fail with AUTH error."""
    response = client.get("/query/assertions")
    
    # Should fail auth before reaching business logic
    # Auth-gated endpoints return 401 for missing/invalid auth
    assert response.status_code == 401


def test_tenant_isolation_enforced(client, admin_key):
    """Query for unauthorized tenant should fail with TENANT.SCOPE_FORBIDDEN."""
    response = authenticated_get(
        client,
        "/query/assertions",
        device_id="example-admin-device",
        tenant_id="unauthorized-tenant",
        private_key=admin_key,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["error_code"] == "TENANT.SCOPE_FORBIDDEN"

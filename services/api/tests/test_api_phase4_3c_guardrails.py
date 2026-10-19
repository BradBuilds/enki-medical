import json
import os
import pytest

from services.api.tests.helpers import (
    create_test_client,
    authenticated_get,
    authenticated_post,
    generate_device_keypair,
    issue_signed_grant,
    save_grant,
)


def setup_device_for_tenant(tenant_id: str):
    private_key = generate_device_keypair()
    grant = issue_signed_grant(
        device_id=f"dev-{tenant_id}",
        device_tier="K",
        tenant_scopes=[tenant_id],
        private_key=private_key,
        expires_in_days=30,
    )
    save_grant(grant)
    return private_key, grant["device_id"]


@pytest.fixture(autouse=True)
def set_guardrail_env(monkeypatch):
    monkeypatch.setenv('ENKI_API_DEFAULT_LIMIT', '100')
    monkeypatch.setenv('ENKI_API_MAX_LIMIT', '200')  # use smaller max for testing
    monkeypatch.setenv('ENKI_API_MAX_ARTIFACT_BYTES', str(1024))  # 1KB limit for tests


def test_pagination_limit_too_large_returns_400():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    resp = authenticated_get(client, "/audit-events?limit=9999", device_id, tenant_id, private_key)
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error_code"] == "API.BAD_REQUEST"


def test_cursor_invalid_returns_400():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    resp = authenticated_get(client, "/audit-events?cursor=notanint", device_id, tenant_id, private_key)
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error_code"] == "API.BAD_REQUEST"


def test_artifact_upload_size_limit_enforced():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    just_under = b"a" * 1024
    just_over = b"b" * 1025

    # Under limit passes
    resp_ok = authenticated_post(client, "/artifacts", device_id, tenant_id, private_key, just_under)
    assert resp_ok.status_code == 200

    # Over limit fails with 413 (contract: API.PAYLOAD_TOO_LARGE)
    resp_bad = authenticated_post(client, "/artifacts", device_id, tenant_id, private_key, just_over)
    assert resp_bad.status_code == 413
    body = resp_bad.json()
    assert body["detail"]["error_code"] == "API.PAYLOAD_TOO_LARGE"

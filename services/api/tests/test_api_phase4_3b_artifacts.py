import os
import hashlib
import pytest

from services.api.tests.helpers import (
    create_test_client,
    authenticated_post,
    authenticated_get,
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


def test_artifact_upload_and_fetch_metadata():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    data = b"hello-artifact"
    expected_cid = hashlib.sha256(data).hexdigest()

    resp_upload = authenticated_post(client, "/artifacts", device_id, tenant_id, private_key, data)
    assert resp_upload.status_code == 200
    meta = resp_upload.json()
    assert meta["cid"] == expected_cid
    assert meta["byte_length"] == len(data)
    # Content-Type may be None or application/octet-stream depending on headers

    resp_meta = authenticated_get(client, f"/artifacts/{expected_cid}", device_id, tenant_id, private_key)
    assert resp_meta.status_code == 200
    meta2 = resp_meta.json()
    assert meta2["cid"] == expected_cid
    assert meta2["byte_length"] == len(data)


def test_artifact_content_roundtrip():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    data = b"bytes-roundtrip-12345"
    expected_cid = hashlib.sha256(data).hexdigest()

    resp_upload = authenticated_post(client, "/artifacts", device_id, tenant_id, private_key, data)
    assert resp_upload.status_code == 200

    resp_content = authenticated_get(client, f"/artifacts/{expected_cid}/content", device_id, tenant_id, private_key)
    assert resp_content.status_code == 200
    assert resp_content.content == data


def test_artifact_not_found():
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    missing_cid = "0" * 64

    resp_meta = authenticated_get(client, f"/artifacts/{missing_cid}", device_id, tenant_id, private_key)
    assert resp_meta.status_code == 404
    body = resp_meta.json()
    assert body["detail"]["error_code"] == "QUERY.ARTIFACT_NOT_FOUND"

    resp_content = authenticated_get(client, f"/artifacts/{missing_cid}/content", device_id, tenant_id, private_key)
    assert resp_content.status_code == 404
    body2 = resp_content.json()
    assert body2["detail"]["error_code"] == "QUERY.ARTIFACT_NOT_FOUND"


def test_tenant_isolation_artifacts():
    client = create_test_client()
    tenant_a = "practice-001"
    tenant_b = "practice-002"
    pk_a, dev_a = setup_device_for_tenant(tenant_a)
    pk_b, dev_b = setup_device_for_tenant(tenant_b)

    data = b"isolation-test"
    cid = hashlib.sha256(data).hexdigest()

    # Upload under tenant A
    resp_upload = authenticated_post(client, "/artifacts", dev_a, tenant_a, pk_a, data)
    assert resp_upload.status_code == 200

    # Try to fetch under tenant B → 404
    resp_meta_b = authenticated_get(client, f"/artifacts/{cid}", dev_b, tenant_b, pk_b)
    assert resp_meta_b.status_code == 404
    resp_content_b = authenticated_get(client, f"/artifacts/{cid}/content", dev_b, tenant_b, pk_b)
    assert resp_content_b.status_code == 404

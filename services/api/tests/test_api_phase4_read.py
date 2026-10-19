import json
import os
import pytest

from services.api.tests.helpers import (
    create_test_client,
    authenticated_get,
    generate_device_keypair,
    issue_signed_grant,
    save_grant,
)
from storage.postgres.db import get_connection
from storage.ids.rid import encode_rid
from storage import ingest_jsonl


@pytest.fixture
def test_dsn():
    dsn = os.getenv('ENKI_DB_DSN')
    if not dsn:
        pytest.skip("ENKI_DB_DSN not set")
    return dsn


@pytest.fixture
def clean_db(test_dsn):
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chain_state")
            cur.execute("DELETE FROM receipts")
            cur.execute("DELETE FROM audit_events")
        conn.commit()
    yield


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


def test_get_receipt_by_txid(test_dsn, clean_db):
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    # Ingest a couple of events to produce a receipt
    jsonl_lines = [
        json.dumps({"event_id": "evt1", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {}}),
        json.dumps({"event_id": "evt2", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:01:00Z", "sequence": 2, "severity": "info", "scope": "local", "metadata": {}}),
    ]
    receipt = ingest_jsonl(jsonl_lines, tenant_id)
    assert receipt['outcome'] == 'FULL_ACCEPT'

    # Query DB to get the receipt RID (txid := rid)
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT rid FROM receipts WHERE tenant_id = %s ORDER BY rid DESC LIMIT 1", (tenant_id,))
            rid_int = cur.fetchone()[0]
    txid = encode_rid(rid_int)

    resp = authenticated_get(client, f"/receipts/{txid}", device_id, tenant_id, private_key)
    assert resp.status_code == 200
    data = resp.json()
    assert data['rid'] == txid
    assert data['chain_hash'] == receipt['chain_hash']
    assert 'commit_time' in data


def test_list_audit_events_pagination(test_dsn, clean_db):
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    # Ingest 5 events
    jsonl_lines = []
    for i in range(5):
        jsonl_lines.append(json.dumps({
            "event_id": f"evt{i}",
            "event_type": "assertion.validated",
            "timestamp": f"2026-01-07T10:00:0{i}Z",
            "sequence": i + 1,
            "severity": "info",
            "scope": "local",
            "metadata": {"index": i}
        }))
    receipt = ingest_jsonl(jsonl_lines, tenant_id)
    assert receipt['outcome'] == 'FULL_ACCEPT'

    # Page 1
    resp1 = authenticated_get(client, "/audit-events?limit=2", device_id, tenant_id, private_key)
    assert resp1.status_code == 200
    page1 = resp1.json()
    assert len(page1['events']) == 2
    assert 'next_cursor' in page1

    # Page 2
    cursor = page1['next_cursor']
    resp2 = authenticated_get(client, f"/audit-events?limit=2&cursor={cursor}", device_id, tenant_id, private_key)
    page2 = resp2.json()
    assert len(page2['events']) == 2

    # Page 3
    cursor2 = page2['next_cursor']
    resp3 = authenticated_get(client, f"/audit-events?limit=2&cursor={cursor2}", device_id, tenant_id, private_key)
    page3 = resp3.json()
    assert len(page3['events']) == 1
    assert 'next_cursor' not in page3


def test_chain_verify_success_and_tamper(test_dsn, clean_db):
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    # Ingest batch 1
    jsonl1 = [json.dumps({"event_id": "a1", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {}})]
    ingest_jsonl(jsonl1, tenant_id)

    # Ingest batch 2
    jsonl2 = [json.dumps({"event_id": "a2", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:01:00Z", "sequence": 2, "severity": "info", "scope": "local", "metadata": {}})]
    ingest_jsonl(jsonl2, tenant_id)

    resp_verify = authenticated_get(client, "/chain/verify", device_id, tenant_id, private_key)
    assert resp_verify.status_code == 200
    verify = resp_verify.json()
    assert verify['valid'] is True
    assert verify['verified_count'] == 2

    # Tamper with chain_hash
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE receipts SET chain_hash = 'bad' WHERE tenant_id = %s", (tenant_id,))
        conn.commit()

    resp_verify2 = authenticated_get(client, "/chain/verify", device_id, tenant_id, private_key)
    assert resp_verify2.status_code == 200
    verify2 = resp_verify2.json()
    assert verify2['valid'] is False
    assert verify2['first_error'] is not None


def test_query_assertions_filters(test_dsn, clean_db):
    client = create_test_client()
    tenant_id = "practice-001"
    private_key, device_id = setup_device_for_tenant(tenant_id)

    # Ingest mixed events
    jsonl_lines = [
        json.dumps({"event_id": "q1", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"kind": "assertion"}}),
        json.dumps({"event_id": "q2", "event_type": "pack.loaded", "timestamp": "2026-01-07T10:00:01Z", "sequence": 2, "severity": "info", "scope": "local", "metadata": {"kind": "system"}}),
    ]
    ingest_jsonl(jsonl_lines, tenant_id)

    resp = authenticated_get(client, "/query/assertions", device_id, tenant_id, private_key)
    assert resp.status_code == 200
    data = resp.json()
    assert all(evt['event_type'].startswith('assertion.') for evt in data['events'])
    assert len(data['events']) == 1


def test_tenant_id_regex_validation(clean_db):
    client = create_test_client()
    tenant_id_invalid = "Practice_001"  # Uppercase + underscore should fail
    private_key, device_id = setup_device_for_tenant("practice-001")

    resp = authenticated_get(client, "/audit-events", device_id, tenant_id_invalid, private_key)
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error_code"] == "API.BAD_REQUEST"


def test_tenant_isolation_read_paths(test_dsn, clean_db):
    client = create_test_client()
    tenant_a = "practice-001"
    tenant_b = "practice-002"
    pk_a, dev_a = setup_device_for_tenant(tenant_a)
    pk_b, dev_b = setup_device_for_tenant(tenant_b)

    # Ingest one event for each tenant
    ingest_jsonl([json.dumps({"event_id": "ta", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"tenant": "a"}})], tenant_a)
    ingest_jsonl([json.dumps({"event_id": "tb", "event_type": "assertion.validated", "timestamp": "2026-01-07T10:00:00Z", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"tenant": "b"}})], tenant_b)

    resp_a = authenticated_get(client, "/audit-events", dev_a, tenant_a, pk_a)
    assert resp_a.status_code == 200
    events_a = resp_a.json()['events']
    assert len(events_a) == 1
    assert events_a[0]['metadata']['tenant'] == 'a'

    resp_b = authenticated_get(client, "/audit-events", dev_b, tenant_b, pk_b)
    events_b = resp_b.json()['events']
    assert len(events_b) == 1
    assert events_b[0]['metadata']['tenant'] == 'b'

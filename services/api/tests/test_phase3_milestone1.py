"""
Phase 3 Milestone 1 Tests: Read path and chain verification.

Tests the query functions added in Milestone 1:
- get_receipt() retrieval by RID
- list_audit_events() with integer cursor pagination
- verify_chain() with nullable previous_chain_hash handling
"""

import pytest
import json
import os
from storage import ingest_jsonl
from storage.postgres.queries import get_receipt, list_audit_events, verify_chain
from storage.postgres.db import get_connection
from storage.ids.rid import decode_rid, encode_rid


@pytest.fixture
def test_dsn():
    """Get PostgreSQL connection string from environment."""
    dsn = os.getenv('ENKI_DB_DSN')
    if not dsn:
        pytest.skip("ENKI_DB_DSN not set")
    return dsn


@pytest.fixture
def clean_db(test_dsn):
    """Clean database before each test."""
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chain_state")
            cur.execute("DELETE FROM receipts")
            cur.execute("DELETE FROM audit_events")
        conn.commit()
    yield


def test_receipt_roundtrip(test_dsn, clean_db):
    """
    Test 1: Ingest events, retrieve receipt by RID, verify all fields present.
    """
    tenant_id = "test-tenant-m1-roundtrip"
    
    # Ingest valid events (ingest_jsonl takes list of strings)
    jsonl_lines = [
        json.dumps({"event_id": "evt1", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:00:00.000000+00:00", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"key": "value"}}),
        json.dumps({"event_id": "evt2", "event_type": "assertion.validated", "timestamp": "2025-12-31T11:00:00.000000+00:00", "sequence": 2, "severity": "info", "scope": "local", "metadata": {"key": "value2"}})
    ]
    
    receipt = ingest_jsonl(jsonl_lines, tenant_id)
    
    assert receipt['outcome'] == 'FULL_ACCEPT'
    assert len(receipt['accepted_rids']) == 2
    
    # Get the receipt RID from database
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT rid FROM receipts WHERE tenant_id = %s", (tenant_id,))
            receipt_rid_int = cur.fetchone()[0]
    
    receipt_rid = encode_rid(receipt_rid_int)
    
    # Retrieve receipt
    retrieved = get_receipt(tenant_id, receipt_rid, test_dsn)
    
    assert retrieved is not None
    assert retrieved['rid'] == receipt_rid
    assert retrieved['chain_hash'] == receipt['chain_hash']
    assert retrieved['receipt_digest'] == receipt['receipt_digest']
    assert 'commit_time' in retrieved
    assert 'previous_chain_hash' in retrieved  # May be genesis or previous


def test_list_audit_events_pagination(test_dsn, clean_db):
    """
    Test 2: Ingest 5 events, list with limit=2, verify pagination with integer cursor.
    """
    tenant_id = "test-tenant-m1-pagination"
    
    # Ingest 5 events
    jsonl_lines = []
    for i in range(5):
        jsonl_lines.append(json.dumps({
            "event_id": f"evt{i}",
            "event_type": "assertion.validated",
            "timestamp": f"2025-12-31T10:00:0{i}.000000+00:00",
            "sequence": i + 1,
            "severity": "info",
            "scope": "local",
            "metadata": {"index": i}
        }))
    
    receipt = ingest_jsonl(jsonl_lines, tenant_id)
    
    assert receipt['outcome'] == 'FULL_ACCEPT'
    assert len(receipt['accepted_rids']) == 5
    
    # First page (limit=2)
    page1 = list_audit_events(tenant_id, test_dsn, limit=2)
    
    assert len(page1['events']) == 2
    assert 'next_cursor' in page1
    assert isinstance(page1['next_cursor'], int)  # Integer cursor
    
    # Second page (using cursor)
    page2 = list_audit_events(tenant_id, test_dsn, limit=2, cursor=page1['next_cursor'])
    
    assert len(page2['events']) == 2
    assert 'next_cursor' in page2
    
    # Third page (should have 1 event, no next cursor)
    page3 = list_audit_events(tenant_id, test_dsn, limit=2, cursor=page2['next_cursor'])
    
    assert len(page3['events']) == 1
    assert 'next_cursor' not in page3  # No more pages
    
    # Verify chronological order (RID increases)
    all_rids = [decode_rid(e['rid']) for e in page1['events'] + page2['events'] + page3['events']]
    assert all_rids == sorted(all_rids)


def test_verify_chain_success(test_dsn, clean_db):
    """
    Test 3: Ingest multiple receipts, verify chain integrity returns valid=True.
    """
    tenant_id = "test-tenant-m1-verify-success"
    
    # Ingest first batch
    jsonl1 = [json.dumps({"event_id": "batch1_evt1", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:00:00.000000+00:00", "sequence": 1, "severity": "info", "scope": "local", "metadata": {}})]
    receipt1 = ingest_jsonl(jsonl1, tenant_id)
    
    # Ingest second batch
    jsonl2 = [json.dumps({"event_id": "batch2_evt1", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:01:00.000000+00:00", "sequence": 2, "severity": "info", "scope": "local", "metadata": {}})]
    receipt2 = ingest_jsonl(jsonl2, tenant_id)
    
    # Verify chain
    result = verify_chain(tenant_id, test_dsn)
    
    assert result['valid'] is True
    assert result['verified_count'] == 2
    assert result['first_error'] is None


def test_verify_chain_detect_tamper(test_dsn, clean_db):
    """
    Test 4: Ingest events, manually corrupt chain_hash, verify detection.
    """
    tenant_id = "test-tenant-m1-tamper"
    
    # Ingest events
    jsonl = [json.dumps({"event_id": "tamper_evt", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:00:00.000000+00:00", "sequence": 1, "severity": "info", "scope": "local", "metadata": {}})]
    receipt = ingest_jsonl(jsonl, tenant_id)
    
    # Corrupt the chain_hash
    with get_connection(test_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE receipts 
                SET chain_hash = 'corrupted_hash_1234567890abcdef'
                WHERE tenant_id = %s
            """, (tenant_id,))
        conn.commit()
    
    # Verify should detect corruption
    result = verify_chain(tenant_id, test_dsn)
    
    assert result['valid'] is False
    assert result['verified_count'] == 0  # Fails on first receipt
    assert result['first_error'] is not None
    assert result['first_error']['actual'] == 'corrupted_hash_1234567890abcdef'


def test_tenant_isolation(test_dsn, clean_db):
    """
    Test 5: Ingest events for two tenants, verify queries respect isolation.
    """
    tenant_a = "test-tenant-m1-isolation-a"
    tenant_b = "test-tenant-m1-isolation-b"
    
    # Ingest for tenant A
    jsonl_a = [json.dumps({"event_id": "tenant_a_evt", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:00:00.000000+00:00", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"tenant": "a"}})]
    receipt_a = ingest_jsonl(jsonl_a, tenant_a)
    
    # Ingest for tenant B
    jsonl_b = [json.dumps({"event_id": "tenant_b_evt", "event_type": "assertion.validated", "timestamp": "2025-12-31T10:00:00.000000+00:00", "sequence": 1, "severity": "info", "scope": "local", "metadata": {"tenant": "b"}})]
    receipt_b = ingest_jsonl(jsonl_b, tenant_b)
    
    # List events for tenant A - should only see tenant A events
    events_a = list_audit_events(tenant_a, test_dsn)
    assert len(events_a['events']) == 1
    assert events_a['events'][0]['event_type'] == 'assertion.validated'
    assert events_a['events'][0]['metadata']['tenant'] == 'a'
    
    # List events for tenant B - should only see tenant B events
    events_b = list_audit_events(tenant_b, test_dsn)
    assert len(events_b['events']) == 1
    assert events_b['events'][0]['event_type'] == 'assertion.validated'
    assert events_b['events'][0]['metadata']['tenant'] == 'b'
    
    # Verify chains are independent
    verify_a = verify_chain(tenant_a, test_dsn)
    assert verify_a['valid'] is True
    assert verify_a['verified_count'] == 1
    
    verify_b = verify_chain(tenant_b, test_dsn)
    assert verify_b['valid'] is True
    assert verify_b['verified_count'] == 1

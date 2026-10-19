"""
Phase 3 Milestone 0 Tests - Vertical Slice

Tests the complete pipeline:
- ObservabilityEvent JSONL parsing
- Mapping to AuditEvent
- Validation
- Storage
- Receipt generation
- Chain hash computation
"""

import pytest
import json
import os

from storage import ingest_jsonl
from storage.postgres.db import initialize_schema, get_connection


@pytest.fixture(scope="module")
def setup_database():
    """
    Initialize test database once for all tests.
    
    Skips tests if ENKI_DB_DSN not set (allows CI/local flexibility).
    """
    if 'ENKI_DB_DSN' not in os.environ:
        pytest.skip("ENKI_DB_DSN not set - skipping Phase 3 tests")
    
    # Initialize schema (idempotent)
    initialize_schema()
    yield
    
    # Cleanup after tests
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE audit_events, receipts, chain_state CASCADE")
        conn.commit()


def test_full_accept_receipt(setup_database):
    """Test ingestion of all valid events → FULL_ACCEPT receipt"""
    jsonl = [
        json.dumps({
            "event_id": "event_1_123456789",
            "event_type": "assertion.validated",
            "timestamp": "2025-12-31T12:00:00.000000+00:00",
            "sequence": 1,
            "severity": "info",
            "scope": "local",
            "metadata": {"test": "data1"}
        }),
        json.dumps({
            "event_id": "event_2_123456790",
            "event_type": "assertion.validated",
            "timestamp": "2025-12-31T12:00:01.000000+00:00",
            "sequence": 2,
            "severity": "info",
            "scope": "local",
            "metadata": {"test": "data2"}
        })
    ]
    
    receipt = ingest_jsonl(jsonl, tenant_id="test_tenant_1")
    
    assert receipt['outcome'] == 'FULL_ACCEPT'
    assert receipt['accepted_count'] == 2
    assert receipt['rejected_count'] == 0
    assert 'chain_hash' in receipt
    assert 'receipt_digest' in receipt
    assert len(receipt['accepted_rids']) == 2
    assert len(receipt['accepted_cids']) == 2


def test_partial_accept_receipt(setup_database):
    """Test ingestion with validation failures → PARTIAL_ACCEPT"""
    jsonl = [
        json.dumps({
            "event_id": "event_3_123456791",
            "event_type": "assertion.validated",
            "timestamp": "2025-12-31T12:00:00.000000+00:00",
            "sequence": 3,
            "severity": "info",
            "scope": "local",
            "metadata": {}
        }),
        json.dumps({
            "event_id": "event_4_123456792",
            "event_type": None,  # Contract violation - null MUST field
            "timestamp": "2025-12-31T12:00:01.000000+00:00",
            "sequence": 4,
            "severity": "info",
            "scope": "local",
            "metadata": {}
        })
    ]
    
    receipt = ingest_jsonl(jsonl, tenant_id="test_tenant_2")
    
    assert receipt['outcome'] == 'PARTIAL_ACCEPT'
    assert receipt['accepted_count'] == 1
    assert receipt['rejected_count'] == 1
    assert len(receipt['rejected_items']) == 1
    # Rejection reason should be mapping_error (None not allowed) or validation_failed
    assert receipt['rejected_items'][0]['reason'] in ['mapping_error', 'validation_failed']


def test_chain_continuity(setup_database):
    """Test that chain hash links correctly across multiple ingestions"""
    # First ingestion
    jsonl1 = [json.dumps({
        "event_id": "event_5_123456793",
        "event_type": "pack.loaded",
        "timestamp": "2025-12-31T12:00:00.000000+00:00",
        "sequence": 5,
        "severity": "info",
        "scope": "local",
        "metadata": {}
    })]
    
    receipt1 = ingest_jsonl(jsonl1, tenant_id="chain_test")
    chain_hash_1 = receipt1['chain_hash']
    receipt_digest_1 = receipt1['receipt_digest']
    
    # Second ingestion
    jsonl2 = [json.dumps({
        "event_id": "event_6_123456794",
        "event_type": "pack.loaded",
        "timestamp": "2025-12-31T12:00:01.000000+00:00",
        "sequence": 6,
        "severity": "info",
        "scope": "local",
        "metadata": {}
    })]
    
    receipt2 = ingest_jsonl(jsonl2, tenant_id="chain_test")
    chain_hash_2 = receipt2['chain_hash']
    receipt_digest_2 = receipt2['receipt_digest']
    
    # Verify chain continuity
    assert chain_hash_1 != chain_hash_2
    
    # Chain hash 2 should be SHA256(chain_hash_1 || receipt2_digest)
    from storage.crypto.chain import compute_chain_hash
    expected_hash = compute_chain_hash(chain_hash_1, receipt_digest_2)
    assert chain_hash_2 == expected_hash, "Chain hash continuity broken"


def test_malformed_json(setup_database):
    """Test that malformed JSON is gracefully rejected without crashing"""
    jsonl = [
        '{"event_id": "event_7_123456795", "incomplete": ',  # Malformed JSON
        json.dumps({
            "event_id": "event_8_123456796",
            "event_type": "validation.completed",
            "timestamp": "2025-12-31T12:00:00.000000+00:00",
            "sequence": 8,
            "severity": "info",
            "scope": "local",
            "metadata": {}
        })
    ]
    
    # Should not crash
    receipt = ingest_jsonl(jsonl, tenant_id="test_tenant_3")
    
    assert receipt['outcome'] == 'PARTIAL_ACCEPT'
    assert receipt['accepted_count'] == 1
    assert receipt['rejected_count'] == 1
    assert receipt['rejected_items'][0]['reason'] == 'parse_error'


def test_contract_violation(setup_database):
    """Test that contract violations (null MUST fields) are rejected"""
    jsonl = [
        json.dumps({
            "event_id": None,  # Null MUST field - contract violation
            "event_type": "assertion.validated",
            "timestamp": "2025-12-31T12:00:00.000000+00:00",
            "sequence": 9,
            "severity": "info",
            "scope": "local",
            "metadata": {}
        })
    ]
    
    receipt = ingest_jsonl(jsonl, tenant_id="test_tenant_4")
    
    assert receipt['outcome'] == 'FULL_REJECT'
    assert receipt['accepted_count'] == 0
    assert receipt['rejected_count'] == 1
    # Should be caught during mapping (KeyError/TypeError) or validation
    assert receipt['rejected_items'][0]['reason'] in ['mapping_error', 'validation_failed']


def test_sequence_field_stored_in_metadata(setup_database):
    """Test that sequence field is stored in metadata._enki_observability_sequence"""
    jsonl = [json.dumps({
        "event_id": "event_10_123456797",
        "event_type": "assertion.validated",
        "timestamp": "2025-12-31T12:00:00.000000+00:00",
        "sequence": 42,  # Test specific sequence value
        "severity": "info",
        "scope": "local",
        "metadata": {"original": "data"}
    })]
    
    receipt = ingest_jsonl(jsonl, tenant_id="test_tenant_5")
    
    assert receipt['outcome'] == 'FULL_ACCEPT'
    assert receipt['accepted_count'] == 1
    
    # Verify sequence stored correctly by reading back from DB
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT payload_json 
                FROM audit_events 
                WHERE tenant_id = %s 
                AND event_type = 'assertion.validated'
                ORDER BY commit_time DESC 
                LIMIT 1
            """, ("test_tenant_5",))
            
            row = cur.fetchone()
            assert row is not None
            
            payload = row[0]  # JSONB column
            assert payload['metadata']['_enki_observability_sequence'] == 42
            assert payload['metadata']['original'] == 'data'

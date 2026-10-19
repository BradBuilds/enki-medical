"""
Tests for validation transcript determinism.

Verifies that transcript export produces identical output for identical inputs,
regardless of insertion order or timing.

Authority: GDU Technical Build Plan v2.4.0 §Phase 2.1
"""

import pytest
import json
import hashlib
from core.spine.validation_transcript import (
    ValidationTranscript,
    ValidationOutcome,
    TranscriptEntry
)


class TestTranscriptDeterminism:
    """Test transcript produces deterministic output."""
    
    def test_export_canonical_sorts_entries(self):
        """Entries are sorted deterministically by (pack_id, step_type, sequence)."""
        t1 = ValidationTranscript()
        
        # Record in random order
        t1.record_step("hash_verification", "zeta", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("namespace_check", "alpha", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("hash_verification", "alpha", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical = t1.export_canonical(include_timestamps=False)
        entry_keys = [(e["pack_id"], e["step_type"]) for e in canonical["entries"]]
        
        # Should be sorted by pack_id, then step_type
        assert entry_keys == [
            ("alpha", "hash_verification"),
            ("alpha", "namespace_check"),
            ("zeta", "hash_verification")
        ]
    
    def test_export_canonical_sorts_context_keys(self):
        """Context keys are sorted alphabetically."""
        t = ValidationTranscript()
        
        # Record with unsorted context
        t.record_step(
            "capability_check",
            "testpack",
            ValidationOutcome.FAIL,
            error_code="MISSING_CAP",
            context={
                "zebra": "last",
                "alpha": "first",
                "middle": "mid"
            },
            include_timestamp=False
        )
        
        canonical = t.export_canonical(include_timestamps=False)
        context_keys = list(canonical["entries"][0]["context"].keys())
        
        assert context_keys == ["alpha", "middle", "zebra"]
    
    def test_export_canonical_excludes_timestamps_by_default(self):
        """Timestamps excluded when include_timestamps=False."""
        t = ValidationTranscript()
        t.record_step("hash_check", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        canonical = t.export_canonical(include_timestamps=False)
        
        assert "timestamp" not in canonical["entries"][0]
    
    def test_export_canonical_includes_timestamps_when_requested(self):
        """Timestamps included when include_timestamps=True."""
        t = ValidationTranscript()
        t.record_step("hash_check", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        canonical = t.export_canonical(include_timestamps=True)
        
        assert "timestamp" in canonical["entries"][0]
        assert canonical["entries"][0]["timestamp"] is not None
    
    def test_same_operations_produce_identical_canonical_output(self):
        """Same validation steps produce byte-identical canonical JSON."""
        # Transcript 1
        t1 = ValidationTranscript()
        t1.record_step("hash_check", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("namespace_check", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("hash_check", "base60", ValidationOutcome.PASS, include_timestamp=False)
        
        # Transcript 2 (same steps, different execution)
        t2 = ValidationTranscript()
        t2.record_step("hash_check", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t2.record_step("namespace_check", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t2.record_step("hash_check", "base60", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical1 = t1.export_canonical(include_timestamps=False)
        canonical2 = t2.export_canonical(include_timestamps=False)
        
        # Should be identical
        assert canonical1 == canonical2
        
        # JSON serialization should also be identical
        json1 = json.dumps(canonical1, sort_keys=True)
        json2 = json.dumps(canonical2, sort_keys=True)
        assert json1 == json2
    
    def test_different_insertion_order_produces_same_canonical(self):
        """Different insertion order produces same canonical output."""
        # Transcript 1: alpha then beta
        t1 = ValidationTranscript()
        t1.record_step("hash_check", "alpha", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("hash_check", "beta", ValidationOutcome.PASS, include_timestamp=False)
        
        # Transcript 2: beta then alpha
        t2 = ValidationTranscript()
        t2.record_step("hash_check", "beta", ValidationOutcome.PASS, include_timestamp=False)
        t2.record_step("hash_check", "alpha", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical1 = t1.export_canonical(include_timestamps=False)
        canonical2 = t2.export_canonical(include_timestamps=False)
        
        # Entries should be sorted identically despite different insertion order
        assert canonical1["entries"][0]["pack_id"] == "alpha"
        assert canonical1["entries"][1]["pack_id"] == "beta"
        assert canonical2["entries"][0]["pack_id"] == "alpha"
        assert canonical2["entries"][1]["pack_id"] == "beta"


class TestCanonicalHashStability:
    """Test that canonical transcripts produce stable hashes."""
    
    def test_canonical_hash_is_deterministic(self):
        """Same transcript produces same hash via canonical export."""
        t1 = ValidationTranscript()
        t1.record_step("gate_a", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t1.record_step("gate_b", "identity", ValidationOutcome.PASS, include_timestamp=False)
        
        t2 = ValidationTranscript()
        t2.record_step("gate_a", "identity", ValidationOutcome.PASS, include_timestamp=False)
        t2.record_step("gate_b", "identity", ValidationOutcome.PASS, include_timestamp=False)
        
        # Export canonical and hash
        canonical1 = json.dumps(t1.export_canonical(include_timestamps=False), sort_keys=True)
        canonical2 = json.dumps(t2.export_canonical(include_timestamps=False), sort_keys=True)
        
        hash1 = hashlib.sha256(canonical1.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(canonical2.encode('utf-8')).hexdigest()
        
        assert hash1 == hash2
    
    def test_different_content_produces_different_hash(self):
        """Different validation results produce different hashes."""
        t1 = ValidationTranscript()
        t1.record_step("gate_a", "identity", ValidationOutcome.PASS, include_timestamp=False)
        
        t2 = ValidationTranscript()
        t2.record_step("gate_a", "identity", ValidationOutcome.FAIL, 
                      error_code="TEST_ERROR", include_timestamp=False)
        
        canonical1 = json.dumps(t1.export_canonical(include_timestamps=False), sort_keys=True)
        canonical2 = json.dumps(t2.export_canonical(include_timestamps=False), sort_keys=True)
        
        hash1 = hashlib.sha256(canonical1.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(canonical2.encode('utf-8')).hexdigest()
        
        assert hash1 != hash2
    
    def test_timestamps_do_not_affect_deterministic_hash(self):
        """When timestamps excluded, hash is deterministic across executions."""
        import time
        
        t1 = ValidationTranscript()
        t1.record_step("gate_a", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        time.sleep(0.01)  # Small delay to ensure different timestamp
        
        t2 = ValidationTranscript()
        t2.record_step("gate_a", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        # Timestamps are different
        assert t1.entries[0].timestamp != t2.entries[0].timestamp
        
        # But canonical hashes (without timestamps) are identical
        canonical1 = json.dumps(t1.export_canonical(include_timestamps=False), sort_keys=True)
        canonical2 = json.dumps(t2.export_canonical(include_timestamps=False), sort_keys=True)
        
        hash1 = hashlib.sha256(canonical1.encode('utf-8')).hexdigest()
        hash2 = hashlib.sha256(canonical2.encode('utf-8')).hexdigest()
        
        assert hash1 == hash2


class TestCanonicalFieldOrdering:
    """Test canonical export maintains consistent field ordering."""
    
    def test_entry_fields_have_consistent_order(self):
        """Entry fields appear in consistent order."""
        t = ValidationTranscript()
        t.record_step(
            "test_step",
            "testpack",
            ValidationOutcome.FAIL,
            error_code="TEST_ERROR",
            context={"key": "value"},
            include_timestamp=False
        )
        
        canonical = t.export_canonical(include_timestamps=False)
        entry = canonical["entries"][0]
        
        # Check field order (pack_id first, then step_type, outcome, sequence, error_code, context)
        keys = list(entry.keys())
        assert keys[0] == "pack_id"
        assert keys[1] == "step_type"
        assert keys[2] == "outcome"
        assert keys[3] == "sequence_number"
        assert keys[4] == "error_code"
        assert keys[5] == "context"
    
    def test_root_fields_have_consistent_order(self):
        """Root fields appear in consistent order."""
        t = ValidationTranscript()
        t.record_step("test", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical = t.export_canonical(include_timestamps=False)
        
        keys = list(canonical.keys())
        assert keys == ["version", "entries", "entry_count"]


class TestEdgeCases:
    """Test edge cases for canonical export."""
    
    def test_empty_transcript_canonical(self):
        """Empty transcript exports correctly."""
        t = ValidationTranscript()
        canonical = t.export_canonical(include_timestamps=False)
        
        assert canonical["version"] == "1.0.0"
        assert canonical["entries"] == []
        assert canonical["entry_count"] == 0
    
    def test_entry_without_error_code(self):
        """Passing entries without error_code export correctly."""
        t = ValidationTranscript()
        t.record_step("test", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical = t.export_canonical(include_timestamps=False)
        entry = canonical["entries"][0]
        
        # error_code should not be present for PASS
        assert "error_code" not in entry
    
    def test_entry_without_context(self):
        """Entries without context export correctly."""
        t = ValidationTranscript()
        t.record_step("test", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        canonical = t.export_canonical(include_timestamps=False)
        entry = canonical["entries"][0]
        
        # context should not be present if empty
        assert "context" not in entry
    
    def test_complex_context_sorting(self):
        """Complex nested context is sorted correctly."""
        t = ValidationTranscript()
        t.record_step(
            "test",
            "pack1",
            ValidationOutcome.FAIL,
            error_code="ERROR",
            context={
                "z_last": "value1",
                "a_first": "value2",
                "m_middle": {
                    "nested_z": "nested1",
                    "nested_a": "nested2"
                }
            },
            include_timestamp=False
        )
        
        canonical = t.export_canonical(include_timestamps=False)
        context = canonical["entries"][0]["context"]
        
        # Top-level keys sorted
        keys = list(context.keys())
        assert keys == ["a_first", "m_middle", "z_last"]
        
        # Note: nested dicts are sorted at top level only
        # (deeper sorting would require recursive implementation)

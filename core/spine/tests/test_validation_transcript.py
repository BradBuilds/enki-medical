"""
ENKI Spine S1.4 — Validation Transcript Tests

Tests for deterministic validation recording and transcript hashing.
Per SPINE-EXECUTION-PLAN S1.4 (10 minimum test cases)
"""

import pytest
import json
import tempfile
from pathlib import Path
from core.spine.validation_transcript import (
    ValidationTranscript,
    TranscriptEntry,
    ValidationOutcome,
    create_transcript_from_validation
)


class TestEmptyTranscript:
    """Test empty transcript handling."""
    
    def test_empty_transcript(self):
        """Test case 1: Empty transcript → empty array, hash computed correctly."""
        transcript = ValidationTranscript()
        
        assert transcript.is_empty()
        assert len(transcript.entries) == 0
        
        # Should be able to compute hash of empty transcript
        hash_result = transcript.compute_hash()
        assert hash_result.startswith("sha256:")
        assert len(hash_result) == len("sha256:") + 64


class TestSingleStep:
    """Test single validation step recording."""
    
    def test_single_step_recorded(self):
        """Test case 2: Single validation step recorded."""
        transcript = ValidationTranscript()
        
        entry = transcript.record_step(
            step_type="capability_validation",
            pack_id="test_pack",
            outcome=ValidationOutcome.PASS
        )
        
        assert len(transcript.entries) == 1
        assert entry.step_type == "capability_validation"
        assert entry.pack_id == "test_pack"
        assert entry.outcome == "pass"
        assert entry.sequence_number == 1
        assert entry.error_code is None


class TestMultipleSteps:
    """Test multiple validation steps in order."""
    
    def test_multiple_steps_in_order(self):
        """Test case 3: Multiple steps recorded in execution order."""
        transcript = ValidationTranscript()
        
        transcript.record_step("namespace_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("capability_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("hash_verification", "pack1", ValidationOutcome.PASS)
        
        assert len(transcript.entries) == 3
        
        # Check sequence numbers increment
        assert transcript.entries[0].sequence_number == 1
        assert transcript.entries[1].sequence_number == 2
        assert transcript.entries[2].sequence_number == 3
        
        # Check execution order preserved
        assert transcript.entries[0].step_type == "namespace_validation"
        assert transcript.entries[1].step_type == "capability_validation"
        assert transcript.entries[2].step_type == "hash_verification"


class TestOutcomes:
    """Test different validation outcomes."""
    
    def test_pass_outcome_recorded(self):
        """Test case 4: Pass outcome recorded (no error_code)."""
        transcript = ValidationTranscript()
        
        entry = transcript.record_step(
            "namespace_validation",
            "pack1",
            ValidationOutcome.PASS
        )
        
        assert entry.outcome == "pass"
        assert entry.error_code is None
    
    def test_fail_outcome_recorded(self):
        """Test case 5: Fail outcome recorded (with error_code)."""
        transcript = ValidationTranscript()
        
        entry = transcript.record_step(
            "namespace_validation",
            "pack1",
            ValidationOutcome.FAIL,
            error_code="NAMESPACE_COLLISION",
            context={"namespace": "audit"}
        )
        
        assert entry.outcome == "fail"
        assert entry.error_code == "NAMESPACE_COLLISION"
        assert entry.context["namespace"] == "audit"


class TestDeterministicHashing:
    """Test deterministic transcript hashing."""
    
    def test_deterministic_hash(self):
        """Test case 6: Same validation run → same transcript hash."""
        transcript1 = ValidationTranscript()
        transcript1.record_step("test_step", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        transcript1.record_step("test_step", "pack2", ValidationOutcome.PASS, include_timestamp=False)
        
        transcript2 = ValidationTranscript()
        transcript2.record_step("test_step", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        transcript2.record_step("test_step", "pack2", ValidationOutcome.PASS, include_timestamp=False)
        
        hash1 = transcript1.compute_hash(include_timestamps=False)
        hash2 = transcript2.compute_hash(include_timestamps=False)
        
        assert hash1 == hash2, "Same steps should produce same hash"
    
    def test_same_input_same_hash(self):
        """Test case 7: Load same packs twice → identical transcript hash."""
        # Simulate loading same packs twice
        def create_test_transcript():
            t = ValidationTranscript()
            t.record_step("namespace_validation", "pack1", ValidationOutcome.PASS, include_timestamp=False)
            t.record_step("capability_validation", "pack1", ValidationOutcome.PASS, include_timestamp=False)
            return t
        
        transcript1 = create_test_transcript()
        transcript2 = create_test_transcript()
        
        hash1 = transcript1.compute_hash(include_timestamps=False)
        hash2 = transcript2.compute_hash(include_timestamps=False)
        
        assert hash1 == hash2
    
    def test_different_input_different_hash(self):
        """Test case 8: Load different packs → different transcript hash."""
        transcript1 = ValidationTranscript()
        transcript1.record_step("test_step", "pack1", ValidationOutcome.PASS, include_timestamp=False)
        
        transcript2 = ValidationTranscript()
        transcript2.record_step("test_step", "pack2", ValidationOutcome.PASS, include_timestamp=False)
        
        hash1 = transcript1.compute_hash(include_timestamps=False)
        hash2 = transcript2.compute_hash(include_timestamps=False)
        
        assert hash1 != hash2, "Different packs should produce different hashes"


class TestTranscriptExport:
    """Test transcript JSON export/import."""
    
    def test_export_to_json(self, tmp_path):
        """Test case 9: Export transcript → valid JSON, passes schema."""
        transcript = ValidationTranscript()
        transcript.record_step("namespace_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("capability_validation", "pack1", ValidationOutcome.FAIL, error_code="MISSING_CAPABILITY")
        
        output_file = tmp_path / "transcript.json"
        transcript.export_to_file(str(output_file))
        
        assert output_file.exists()
        
        # Verify it's valid JSON
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert data["version"] == "1.0.0"
        assert data["entry_count"] == 2
        assert len(data["entries"]) == 2
        assert data["entries"][0]["step_type"] == "namespace_validation"
        assert data["entries"][1]["outcome"] == "fail"
    
    def test_import_from_json(self, tmp_path):
        """Test: Load transcript from JSON → identical structure."""
        # Create and export transcript
        transcript1 = ValidationTranscript()
        transcript1.record_step("test_step", "pack1", ValidationOutcome.PASS)
        transcript1.record_step("test_step", "pack2", ValidationOutcome.FAIL, error_code="TEST_ERROR")
        
        output_file = tmp_path / "transcript.json"
        transcript1.export_to_file(str(output_file))
        
        # Load transcript
        transcript2 = ValidationTranscript.load_from_file(str(output_file))
        
        assert len(transcript2.entries) == 2
        assert transcript2.entries[0].step_type == "test_step"
        assert transcript2.entries[0].pack_id == "pack1"
        assert transcript2.entries[1].error_code == "TEST_ERROR"


class TestAllStepTypes:
    """Test all validation step types represented."""
    
    def test_all_step_types_represented(self):
        """Test case 10: Full validation → transcript includes capability, namespace, hash steps."""
        transcript = ValidationTranscript()
        
        # Namespace validation
        transcript.record_step("namespace_validation", "pack1", ValidationOutcome.PASS)
        
        # Capability validation
        transcript.record_step("capability_validation", "pack1", ValidationOutcome.PASS)
        
        # Hash verification
        transcript.record_step("hash_verification", "pack1", ValidationOutcome.PASS)
        
        # Check all step types present
        step_types = {entry.step_type for entry in transcript.entries}
        assert "namespace_validation" in step_types
        assert "capability_validation" in step_types
        assert "hash_verification" in step_types


class TestTranscriptQueries:
    """Test transcript query methods."""
    
    def test_get_failures(self):
        """Test: Query failed steps."""
        transcript = ValidationTranscript()
        transcript.record_step("step1", "pack1", ValidationOutcome.PASS)
        transcript.record_step("step2", "pack2", ValidationOutcome.FAIL, error_code="ERROR1")
        transcript.record_step("step3", "pack3", ValidationOutcome.FAIL, error_code="ERROR2")
        
        failures = transcript.get_failures()
        assert len(failures) == 2
        assert failures[0].error_code == "ERROR1"
        assert failures[1].error_code == "ERROR2"
    
    def test_get_passes(self):
        """Test: Query passed steps."""
        transcript = ValidationTranscript()
        transcript.record_step("step1", "pack1", ValidationOutcome.PASS)
        transcript.record_step("step2", "pack2", ValidationOutcome.FAIL, error_code="ERROR1")
        transcript.record_step("step3", "pack3", ValidationOutcome.PASS)
        
        passes = transcript.get_passes()
        assert len(passes) == 2
        assert passes[0].pack_id == "pack1"
        assert passes[1].pack_id == "pack3"
    
    def test_has_failures(self):
        """Test: Check if transcript contains failures."""
        transcript1 = ValidationTranscript()
        transcript1.record_step("step1", "pack1", ValidationOutcome.PASS)
        assert not transcript1.has_failures()
        
        transcript2 = ValidationTranscript()
        transcript2.record_step("step1", "pack1", ValidationOutcome.FAIL, error_code="ERROR")
        assert transcript2.has_failures()
    
    def test_get_steps_by_type(self):
        """Test: Query steps by type."""
        transcript = ValidationTranscript()
        transcript.record_step("namespace_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("capability_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("namespace_validation", "pack2", ValidationOutcome.PASS)
        
        namespace_steps = transcript.get_steps_by_type("namespace_validation")
        assert len(namespace_steps) == 2
        
        capability_steps = transcript.get_steps_by_type("capability_validation")
        assert len(capability_steps) == 1
    
    def test_get_steps_for_pack(self):
        """Test: Query steps for specific pack."""
        transcript = ValidationTranscript()
        transcript.record_step("namespace_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("capability_validation", "pack1", ValidationOutcome.PASS)
        transcript.record_step("namespace_validation", "pack2", ValidationOutcome.PASS)
        
        pack1_steps = transcript.get_steps_for_pack("pack1")
        assert len(pack1_steps) == 2
        
        pack2_steps = transcript.get_steps_for_pack("pack2")
        assert len(pack2_steps) == 1


class TestTimestampHandling:
    """Test timestamp inclusion/exclusion in hashing."""
    
    def test_timestamps_excluded_from_hash(self):
        """Test: Timestamps don't affect hash (determinism)."""
        transcript1 = ValidationTranscript()
        transcript1.record_step("test_step", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        # Wait a tiny bit to ensure different timestamp
        import time
        time.sleep(0.01)
        
        transcript2 = ValidationTranscript()
        transcript2.record_step("test_step", "pack1", ValidationOutcome.PASS, include_timestamp=True)
        
        # Different timestamps
        assert transcript1.entries[0].timestamp != transcript2.entries[0].timestamp
        
        # But same hash (timestamps excluded)
        hash1 = transcript1.compute_hash(include_timestamps=False)
        hash2 = transcript2.compute_hash(include_timestamps=False)
        
        assert hash1 == hash2, "Timestamps should not affect hash"


class TestTranscriptCreationHelper:
    """Test helper function for creating transcripts from validation results."""
    
    def test_create_from_validation_results(self):
        """Test: Create transcript from validation errors."""
        # Mock error objects
        from dataclasses import dataclass
        
        @dataclass
        class MockError:
            code: str
            context: dict
        
        namespace_errors = [
            MockError("NAMESPACE_COLLISION", {"pack_id": "pack1", "namespace": "audit"})
        ]
        capability_errors = []
        hash_errors = []
        packs = ["pack1", "pack2"]
        
        transcript = create_transcript_from_validation(
            namespace_errors, capability_errors, hash_errors, packs
        )
        
        assert len(transcript.entries) > 0
        
        # Should have entries for both packs
        pack1_steps = transcript.get_steps_for_pack("pack1")
        pack2_steps = transcript.get_steps_for_pack("pack2")
        
        assert len(pack1_steps) > 0
        assert len(pack2_steps) > 0
        
        # Pack1 should have a failure
        pack1_failures = [e for e in pack1_steps if e.outcome == "fail"]
        assert len(pack1_failures) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

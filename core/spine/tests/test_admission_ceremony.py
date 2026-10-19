"""
End-to-End Admission Ceremony Determinism Test

Tests that the admission ceremony produces deterministic artifacts:
- Same transcript hash across multiple runs
- Same activation record structure
- No machine-specific paths or randomness

This is NOT an S1 test - it tests the ceremony orchestration script.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.governance.run_admission_ceremony import run_ceremony
from core.spine.validation_transcript import ValidationTranscript


class TestAdmissionCeremonyDeterminism:
    """Test admission ceremony determinism guarantees."""
    
    def test_ceremony_produces_identical_transcript_hash(self):
        """
        Critical test: Running ceremony twice with same inputs must produce
        identical transcript hash (excluding timestamps, which are not in hash).
        """
        # Setup: Create temp directories for two ceremony runs
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            
            output_dir1 = Path(tmpdir1)
            output_dir2 = Path(tmpdir2)
            
            active_set_path = project_root / "active_set_v1.json"
            operator = "test_operator"
            
            # Run ceremony twice
            result1 = run_ceremony(active_set_path, output_dir1, operator)
            result2 = run_ceremony(active_set_path, output_dir2, operator)
            
            # Assert: Transcript hashes are identical
            assert result1["success"], "First ceremony failed"
            assert result2["success"], "Second ceremony failed"
            assert result1["transcript_hash"] == result2["transcript_hash"], \
                f"Transcript hashes differ: {result1['transcript_hash']} vs {result2['transcript_hash']}"
            
            print(f"✅ Determinism verified: {result1['transcript_hash']}")
    
    def test_ceremony_produces_valid_artifacts(self):
        """Test that ceremony produces valid transcript and activation artifacts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            active_set_path = project_root / "active_set_v1.json"
            operator = "test_operator"
            
            # Run ceremony
            result = run_ceremony(active_set_path, output_dir, operator)
            
            assert result["success"], "Ceremony failed"
            
            # Assert: Transcript file exists and is valid JSON
            transcript_path = output_dir / "validation_transcript.json"
            assert transcript_path.exists(), "Transcript file not created"
            
            with open(transcript_path, 'r') as f:
                transcript_data = json.load(f)
            
            assert "entries" in transcript_data, "Transcript missing entries"
            assert len(transcript_data["entries"]) > 0, "Transcript has no entries"
            
            # Assert: Activation record exists and is valid JSON
            activation_path = output_dir / "activation_record.json"
            assert activation_path.exists(), "Activation record not created"
            
            with open(activation_path, 'r') as f:
                activation_data = json.load(f)
            
            # Activation record is wrapped in a container
            assert "activation" in activation_data or "activation_id" in activation_data, \
                "Activation record missing required fields"
            
            # Handle both flat and nested formats
            if "activation" in activation_data:
                activation = activation_data["activation"]
            else:
                activation = activation_data
            
            assert "activation_id" in activation
            assert "transcript_hash" in activation
            assert "activated_by" in activation
            assert "activated_at" in activation
            assert "active_set_version" in activation
            
            # Assert: Activation record references the correct transcript hash
            assert activation["transcript_hash"] == result["transcript_hash"], \
                "Activation record references wrong transcript hash"
            
            print(f"✅ Artifacts valid: transcript + activation record")
    
    def test_ceremony_validates_all_three_packs(self):
        """Test that ceremony validates all three Phase 0 trilogy packs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            active_set_path = project_root / "active_set_v1.json"
            operator = "test_operator"
            
            # Run ceremony
            result = run_ceremony(active_set_path, output_dir, operator)
            
            assert result["success"], "Ceremony failed"
            assert result["pack_count"] == 3, f"Expected 3 packs, got {result['pack_count']}"
            
            # Load transcript and verify all three packs were validated
            transcript_path = output_dir / "validation_transcript.json"
            with open(transcript_path, 'r') as f:
                transcript_data = json.load(f)
            
            pack_ids_seen = set()
            for entry in transcript_data["entries"]:
                if entry["pack_id"] != "_system":
                    pack_ids_seen.add(entry["pack_id"])
            
            expected_packs = {"identity", "assertionvocab", "auditvocab"}
            assert pack_ids_seen == expected_packs, \
                f"Expected packs {expected_packs}, got {pack_ids_seen}"
            
            print(f"✅ All three packs validated: {pack_ids_seen}")
    
    def test_transcript_entries_are_deterministically_ordered(self):
        """
        Test that transcript entries have consistent sequence_number ordering
        across multiple runs (excluding timestamps).
        """
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            
            output_dir1 = Path(tmpdir1)
            output_dir2 = Path(tmpdir2)
            
            active_set_path = project_root / "active_set_v1.json"
            operator = "test_operator"
            
            # Run ceremony twice
            result1 = run_ceremony(active_set_path, output_dir1, operator)
            result2 = run_ceremony(active_set_path, output_dir2, operator)
            
            # Load both transcripts
            transcript_path1 = output_dir1 / "validation_transcript.json"
            transcript_path2 = output_dir2 / "validation_transcript.json"
            
            with open(transcript_path1, 'r') as f:
                transcript1 = json.load(f)
            with open(transcript_path2, 'r') as f:
                transcript2 = json.load(f)
            
            # Assert: Same number of entries
            assert len(transcript1["entries"]) == len(transcript2["entries"]), \
                "Transcripts have different entry counts"
            
            # Assert: Entries have same sequence (excluding timestamps)
            for e1, e2 in zip(transcript1["entries"], transcript2["entries"]):
                assert e1["sequence_number"] == e2["sequence_number"]
                assert e1["step_type"] == e2["step_type"]
                assert e1["outcome"] == e2["outcome"]
                assert e1["pack_id"] == e2["pack_id"]
                # error_code is optional (only present if outcome="fail")
                assert e1.get("error_code") == e2.get("error_code")
                # Note: timestamps will differ, context may have file paths
            
            print(f"✅ Transcript ordering is deterministic: {len(transcript1['entries'])} entries")
    
    def test_ceremony_v2_with_base60_deterministic(self):
        """Test ceremony v2 (4 packs: trilogy + base60) produces identical transcript hash."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            active_set_path = project_root / "active_set_v2.json"
            output_dir1 = tmpdir / "run1"
            output_dir2 = tmpdir / "run2"
            operator = "Test Operator"
            
            # Run ceremony twice with same inputs
            result1 = run_ceremony(active_set_path, output_dir1, operator)
            result2 = run_ceremony(active_set_path, output_dir2, operator)
            
            # Assert: Transcript hashes are identical
            assert result1["transcript_hash"] == result2["transcript_hash"], \
                f"Transcript hashes differ: {result1['transcript_hash']} != {result2['transcript_hash']}"
            
            # Assert: Expected hash (golden constant for v2.1.0 with 5 packs including language)
            expected_hash = "sha256:d178213048e99f4d2d70a317c6e1eb5503a6eec544f459839a57d3c4e70356e0"
            assert result1["transcript_hash"] == expected_hash, \
                f"Transcript hash mismatch: got {result1['transcript_hash']}, expected {expected_hash}"
            
            # Assert: All 5 packs validated (identity, assertionvocab, auditvocab, base60, language)
            assert result1["pack_count"] == 5
            assert result2["pack_count"] == 5
            
            print(f"✅ Ceremony v2.1.0 (5 packs) deterministic: {result1['transcript_hash']}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])

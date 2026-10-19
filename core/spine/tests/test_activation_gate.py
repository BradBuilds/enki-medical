"""
ENKI Spine S1.5 — Activation Gate Tests

Tests for explicit activation requirement enforcement.
Per SPINE-EXECUTION-PLAN S1.5 (10 minimum test cases)
"""

import pytest
import json
from pathlib import Path
from core.spine.activation_gate import (
    ActivationRecord,
    create_activation_record,
    verify_activation,
    save_activation_record,
    load_activation_record,
    find_latest_activation,
    require_activation,
    ActivationRequiredError,
    ActivationTranscriptMismatchError
)


class TestActivationRecordCreation:
    """Test activation record creation."""
    
    def test_create_activation_record(self):
        """Test case 1: Activation record creation → valid structure, passes schema."""
        record = create_activation_record(
            active_set_version="1.0.0",
            transcript_hash="sha256:abc123def456" + "0" * 50,
            activated_by="developer"
        )
        
        assert record.active_set_version == "1.0.0"
        assert record.transcript_hash.startswith("sha256:")
        assert record.activated_by == "developer"
        assert record.activation_id is not None
        assert record.activated_at is not None
        
        # Verify UUID format
        import uuid
        uuid.UUID(record.activation_id)  # Should not raise


class TestActivationImmutability:
    """Test activation record immutability."""
    
    def test_activation_immutability(self):
        """Test case 2: Activation record immutability (frozen dataclass)."""
        record = create_activation_record("1.0.0", "sha256:" + "a" * 64, "developer")
        
        # Attempt to modify should raise error
        with pytest.raises(Exception):  # FrozenInstanceError
            record.transcript_hash = "sha256:" + "b" * 64


class TestActivationRequired:
    """Test activation requirement enforcement."""
    
    def test_no_activation_halts(self, tmp_path):
        """Test case 3: No activation → HALT ACTIVATION_REQUIRED."""
        # Empty directory (no activations)
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        with pytest.raises(ActivationRequiredError) as exc_info:
            require_activation(
                active_set_version="1.0.0",
                transcript_hash="sha256:" + "a" * 64,
                activation_directory=str(activation_dir)
            )
        
        assert exc_info.value.active_set_version == "1.0.0"
        assert "1.0.0" in str(exc_info.value)
    
    def test_activation_present_proceeds(self, tmp_path):
        """Test case 4: Activation present → proceed (load succeeds)."""
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        transcript_hash = "sha256:" + "a" * 64
        
        # Create and save activation
        record = create_activation_record("1.0.0", transcript_hash, "developer")
        save_activation_record(record, str(activation_dir / "activation_1.json"))
        
        # Require activation should succeed
        loaded_activation = require_activation(
            active_set_version="1.0.0",
            transcript_hash=transcript_hash,
            activation_directory=str(activation_dir)
        )
        
        assert loaded_activation.activation_id == record.activation_id


class TestTranscriptHashVerification:
    """Test transcript hash verification."""
    
    def test_transcript_hash_mismatch_halts(self, tmp_path):
        """Test case 5: Transcript hash mismatch → HALT ACTIVATION_TRANSCRIPT_MISMATCH."""
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        declared_hash = "sha256:" + "a" * 64
        computed_hash = "sha256:" + "b" * 64
        
        # Create activation with declared hash
        record = create_activation_record("1.0.0", declared_hash, "developer")
        save_activation_record(record, str(activation_dir / "activation_1.json"))
        
        # Require activation with different computed hash
        with pytest.raises(ActivationTranscriptMismatchError) as exc_info:
            require_activation(
                active_set_version="1.0.0",
                transcript_hash=computed_hash,  # Different!
                activation_directory=str(activation_dir)
            )
        
        assert exc_info.value.declared_hash == declared_hash
        assert exc_info.value.computed_hash == computed_hash
    
    def test_transcript_hash_match_proceeds(self, tmp_path):
        """Test case 6: Transcript hash match → proceed (verification passes)."""
        transcript_hash = "sha256:" + "a" * 64
        
        record = create_activation_record("1.0.0", transcript_hash, "developer")
        
        # Verify should pass
        assert verify_activation(record, transcript_hash) is True


class TestMultipleActivations:
    """Test multiple activations (append-only)."""
    
    def test_multiple_activations_append_only(self, tmp_path):
        """Test case 7: Multiple activations → both exist, latest used."""
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        transcript_hash = "sha256:" + "a" * 64
        
        # Create first activation
        import time
        record1 = create_activation_record("1.0.0", transcript_hash, "developer1")
        save_activation_record(record1, str(activation_dir / "activation_1.json"))
        
        # Wait a tiny bit to ensure different timestamp
        time.sleep(0.01)
        
        # Create second activation
        record2 = create_activation_record("1.0.0", transcript_hash, "developer2")
        save_activation_record(record2, str(activation_dir / "activation_2.json"))
        
        # Both files should exist
        assert (activation_dir / "activation_1.json").exists()
        assert (activation_dir / "activation_2.json").exists()
        
        # Latest should be used
        latest = find_latest_activation(str(activation_dir), "1.0.0")
        assert latest.activation_id == record2.activation_id


class TestActivationSerialization:
    """Test activation record serialization."""
    
    def test_save_and_load_activation(self, tmp_path):
        """Test case 8: Save activation → reload → identical structure."""
        record = create_activation_record(
            "1.0.0",
            "sha256:" + "a" * 64,
            "developer"
        )
        
        output_file = tmp_path / "activation.json"
        save_activation_record(record, str(output_file))
        
        # Verify file exists and is valid JSON
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert data["version"] == "1.0.0"
        assert "activation" in data
        assert data["activation"]["activation_id"] == record.activation_id
        
        # Load back
        loaded = load_activation_record(str(output_file))
        
        assert loaded.activation_id == record.activation_id
        assert loaded.active_set_version == record.active_set_version
        assert loaded.transcript_hash == record.transcript_hash
        assert loaded.activated_by == record.activated_by


class TestSchemaValidation:
    """Test activation record schema validation."""
    
    def test_invalid_activation_schema_rejection(self, tmp_path):
        """Test case 9: Invalid activation record → schema rejection."""
        output_file = tmp_path / "invalid.json"
        
        # Write invalid structure (missing required field)
        invalid_data = {
            "version": "1.0.0",
            "activation": {
                "activation_id": "test-id",
                # Missing transcript_hash and other required fields!
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(invalid_data, f)
        
        # Loading should fail
        with pytest.raises(KeyError):  # Missing required field
            load_activation_record(str(output_file))


class TestActivationWithoutHardware:
    """Test activation without hardware (developer mode)."""
    
    def test_activation_without_hardware(self):
        """Test case 10: Activation with activated_by='developer' → succeeds (no hardware required)."""
        # This is the S1.5 scope: declarative only, no hardware yet
        record = create_activation_record(
            "1.0.0",
            "sha256:" + "a" * 64,
            activated_by="developer"  # No hardware attestation
        )
        
        assert record.activated_by == "developer"
        assert record.activation_id is not None
        
        # Should be valid activation
        transcript_hash = "sha256:" + "a" * 64
        assert verify_activation(record, transcript_hash) is True


class TestActivationFindLatest:
    """Test finding latest activation."""
    
    def test_find_latest_by_version(self, tmp_path):
        """Test: Find latest activation for specific active set version."""
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        # Create activations for different versions
        import time
        
        record_v1 = create_activation_record("1.0.0", "sha256:" + "a" * 64, "dev1")
        save_activation_record(record_v1, str(activation_dir / "activation_v1_1.json"))
        
        time.sleep(0.01)
        
        record_v2 = create_activation_record("2.0.0", "sha256:" + "b" * 64, "dev2")
        save_activation_record(record_v2, str(activation_dir / "activation_v2_1.json"))
        
        time.sleep(0.01)
        
        record_v1_2 = create_activation_record("1.0.0", "sha256:" + "c" * 64, "dev3")
        save_activation_record(record_v1_2, str(activation_dir / "activation_v1_2.json"))
        
        # Find latest for v1.0.0 (should be record_v1_2)
        latest_v1 = find_latest_activation(str(activation_dir), "1.0.0")
        assert latest_v1 is not None, "Should find activation for v1.0.0"
        assert latest_v1.activation_id == record_v1_2.activation_id
        
        # Find latest for v2.0.0 (should be record_v2)
        latest_v2 = find_latest_activation(str(activation_dir), "2.0.0")
        assert latest_v2 is not None, "Should find activation for v2.0.0"
        assert latest_v2.activation_id == record_v2.activation_id
    
    def test_find_no_activation(self, tmp_path):
        """Test: Find activation when none exists → returns None."""
        activation_dir = tmp_path / "activations"
        activation_dir.mkdir()
        
        result = find_latest_activation(str(activation_dir), "1.0.0")
        assert result is None


class TestActivationContext:
    """Test activation in different contexts."""
    
    def test_to_dict_from_dict_roundtrip(self):
        """Test: to_dict() and from_dict() roundtrip."""
        record = create_activation_record(
            "1.0.0",
            "sha256:" + "a" * 64,
            "developer"
        )
        
        # Convert to dict
        data = record.to_dict()
        
        # Verify dict structure
        assert "activation_id" in data
        assert "active_set_version" in data
        assert "transcript_hash" in data
        assert "activated_at" in data
        assert "activated_by" in data
        
        # Convert back
        loaded = ActivationRecord.from_dict(data)
        
        assert loaded.activation_id == record.activation_id
        assert loaded.active_set_version == record.active_set_version
        assert loaded.transcript_hash == record.transcript_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

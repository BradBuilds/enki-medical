"""
Tests for Active Set Strict Mode

Authority: GDU Technical Build Plan v2.4.0 §1.1 Active Set Loader (Strict Mode)
"""

import json
import pytest
import tempfile
from pathlib import Path
from core.spine.active_set import (
    ActiveSet,
    PackDeclaration,
    load_active_set_strict,
    verify_pack_allowed
)


@pytest.fixture
def valid_active_set_data():
    """Valid active set with all required fields."""
    return {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "identity",
                "version": "0.2.0",
                "content_hash": "sha256:b023e0406af4daf434fd97b4eae72436a29b422d0ea4d12b3d4509ea19dbb78a"
            },
            {
                "pack_id": "language",
                "version": "0.1.0",
                "content_hash": "sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
            }
        ]
    }


@pytest.fixture
def active_set_missing_hash():
    """Active set with missing content_hash (invalid for strict mode)."""
    return {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "identity",
                "version": "0.2.0"
                # Missing content_hash
            }
        ]
    }


@pytest.fixture
def active_set_invalid_hash_format():
    """Active set with invalid hash format."""
    return {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "identity",
                "version": "0.2.0",
                "content_hash": "md5:abc123"  # Wrong algorithm
            }
        ]
    }


@pytest.fixture
def active_set_invalid_version():
    """Active set with invalid semver."""
    return {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "identity",
                "version": "0.2",  # Missing patch
                "content_hash": "sha256:b023e0406af4daf434fd97b4eae72436a29b422d0ea4d12b3d4509ea19dbb78a"
            }
        ]
    }


@pytest.fixture
def active_set_unsorted():
    """Active set with unsorted packs (should be normalized)."""
    return {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "language",
                "version": "0.1.0",
                "content_hash": "sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
            },
            {
                "pack_id": "identity",
                "version": "0.2.0",
                "content_hash": "sha256:b023e0406af4daf434fd97b4eae72436a29b422d0ea4d12b3d4509ea19dbb78a"
            }
        ]
    }


class TestLoadActiveSetStrict:
    """Test strict active set loading."""
    
    def test_load_valid_active_set(self, valid_active_set_data, tmp_path):
        """Load valid active set with all required fields."""
        # Write test file
        test_file = tmp_path / "active_set_test.json"
        with open(test_file, 'w') as f:
            json.dump(valid_active_set_data, f)
        
        # Load strict
        active_set = load_active_set_strict(test_file)
        
        # Verify loaded correctly
        assert active_set.version == "1.0.0"
        assert len(active_set.packs) == 2
        
        # Verify all packs have content_hash
        for pack in active_set.packs:
            assert pack.content_hash is not None
            assert pack.content_hash.startswith("sha256:")
    
    def test_reject_missing_content_hash(self, active_set_missing_hash, tmp_path):
        """Strict mode rejects active set without content_hash."""
        test_file = tmp_path / "active_set_no_hash.json"
        with open(test_file, 'w') as f:
            json.dump(active_set_missing_hash, f)
        
        with pytest.raises(ValueError, match="missing required content_hash"):
            load_active_set_strict(test_file)
    
    def test_reject_invalid_hash_format(self, active_set_invalid_hash_format, tmp_path):
        """Strict mode rejects invalid hash format."""
        test_file = tmp_path / "active_set_bad_hash.json"
        with open(test_file, 'w') as f:
            json.dump(active_set_invalid_hash_format, f)
        
        # Schema validation catches this before our additional checks
        with pytest.raises(Exception, match="does not match"):  # jsonschema.ValidationError
            load_active_set_strict(test_file)
    
    def test_reject_invalid_version(self, active_set_invalid_version, tmp_path):
        """Strict mode rejects invalid semver."""
        test_file = tmp_path / "active_set_bad_version.json"
        with open(test_file, 'w') as f:
            json.dump(active_set_invalid_version, f)
        
        # Schema validation catches this before our semver parsing
        with pytest.raises(Exception, match="does not match"):  # jsonschema.ValidationError
            load_active_set_strict(test_file)
    
    def test_normalize_pack_ordering(self, active_set_unsorted, tmp_path):
        """Strict loader normalizes pack ordering (NOT an error)."""
        test_file = tmp_path / "active_set_unsorted.json"
        with open(test_file, 'w') as f:
            json.dump(active_set_unsorted, f)
        
        # Load strict
        active_set = load_active_set_strict(test_file)
        
        # Verify packs are sorted by pack_id
        pack_ids = [p.pack_id for p in active_set.packs]
        assert pack_ids == sorted(pack_ids)
        assert pack_ids == ["identity", "language"]


class TestVerifyPackAllowed:
    """Test pack verification against active set."""
    
    def test_accept_valid_pack(self, valid_active_set_data):
        """Accept pack that matches active set exactly."""
        active_set = ActiveSet.from_dict(valid_active_set_data)
        
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="language",
            version="0.1.0",
            actual_hash="sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
        )
        
        assert ok is True
        assert error_code is None
        assert context["verified"] is True
    
    def test_reject_unknown_pack(self, valid_active_set_data):
        """Reject pack not in active set."""
        active_set = ActiveSet.from_dict(valid_active_set_data)
        
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="unknown_pack",
            version="1.0.0",
            actual_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000"
        )
        
        assert ok is False
        assert error_code == "PACK_NOT_IN_ACTIVE_SET"
        assert context["pack_id"] == "unknown_pack"
    
    def test_reject_version_mismatch(self, valid_active_set_data):
        """Reject pack with wrong version."""
        active_set = ActiveSet.from_dict(valid_active_set_data)
        
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="language",
            version="0.2.0",  # Wrong version
            actual_hash="sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
        )
        
        assert ok is False
        assert error_code == "PACK_VERSION_MISMATCH"
        assert context["declared_version"] == "0.1.0"
        assert context["actual_version"] == "0.2.0"
    
    def test_reject_hash_mismatch(self, valid_active_set_data):
        """Reject pack with wrong content hash."""
        active_set = ActiveSet.from_dict(valid_active_set_data)
        
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="language",
            version="0.1.0",
            actual_hash="sha256:0000000000000000000000000000000000000000000000000000000000000000"
        )
        
        assert ok is False
        assert error_code == "PACK_HASH_MISMATCH"
        assert "declared_hash" in context
        assert "actual_hash" in context


class TestErrorCodeAuthority:
    """Test that error codes match locked specification."""
    
    def test_error_code_names_locked(self, valid_active_set_data):
        """Verify error code names match GDU Technical Build Plan v2.4.0."""
        active_set = ActiveSet.from_dict(valid_active_set_data)
        
        # Test each locked error code
        _, code, _ = verify_pack_allowed(
            active_set, "unknown", "1.0.0", "sha256:0" * 64
        )
        assert code == "PACK_NOT_IN_ACTIVE_SET"  # LOCKED
        
        _, code, _ = verify_pack_allowed(
            active_set, "language", "9.9.9", "sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
        )
        assert code == "PACK_VERSION_MISMATCH"  # LOCKED
        
        _, code, _ = verify_pack_allowed(
            active_set, "language", "0.1.0", "sha256:0" * 64
        )
        assert code == "PACK_HASH_MISMATCH"  # LOCKED


class TestStrictModeIntegration:
    """Integration tests for strict mode behavior."""
    
    def test_strict_mode_end_to_end(self, valid_active_set_data, tmp_path):
        """Test complete strict mode flow: load + verify."""
        # Write test file
        test_file = tmp_path / "active_set_integration.json"
        with open(test_file, 'w') as f:
            json.dump(valid_active_set_data, f)
        
        # Load strict
        active_set = load_active_set_strict(test_file)
        
        # Verify pack (success case)
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="language",
            version="0.1.0",
            actual_hash="sha256:f7786484ce7da1e1bc4ae8d2f5fde757d18ecf7ca6a7ae531dad3030b9d6278d"
        )
        
        assert ok is True
        assert error_code is None
        
        # Verify pack (failure case)
        ok, error_code, context = verify_pack_allowed(
            active_set,
            pack_id="language",
            version="0.1.0",
            actual_hash="sha256:wrong_hash_12345678901234567890123456789012345678901234567890123456"
        )
        
        assert ok is False
        assert error_code == "PACK_HASH_MISMATCH"

"""
Tests for PackLoader Strict Mode Active Set Enforcement

Authority: GDU Technical Build Plan v2.4.0 §1.2 Pack Loader Integration
"""

import json
import pytest
import tempfile
from pathlib import Path
from core.packs.loader import PackLoader
from core.packs import errors
from core.spine.active_set import ActiveSet


@pytest.fixture
def valid_pack_structure(tmp_path):
    """Create a valid pack structure for testing."""
    pack_dir = tmp_path / "test_pack"
    pack_dir.mkdir()
    
    # Create pack.json
    pack_json = {
        "pack_id": "testpack",
        "version": "1.0.0",
        "name": "Test Pack",
        "description": "A test pack",
        "definitions": [
            {"id": "testpack.def1", "path": "definitions/def1.json"}
        ]
    }
    with open(pack_dir / "pack.json", 'w') as f:
        json.dump(pack_json, f)
    
    # Create definition
    (pack_dir / "definitions").mkdir()
    def_json = {
        "id": "testpack.def1",
        "type": "system",  # Valid type per schema: system, rules, glyphs, digits, custom
        "version": "1.0.0",
        "description": "Test definition",
        "content": {"value": "test"}
    }
    with open(pack_dir / "definitions" / "def1.json", 'w') as f:
        json.dump(def_json, f)
    
    return pack_dir


@pytest.fixture
def active_set_with_pack(tmp_path):
    """Create an active set that includes testpack."""
    # Note: This uses a placeholder hash - tests will need actual hash
    active_set_data = {
        "version": "1.0.0",
        "packs": [
            {
                "pack_id": "testpack",
                "version": "1.0.0",
                "content_hash": "sha256:placeholder_will_be_replaced_in_test"
            }
        ]
    }
    
    active_set_file = tmp_path / "active_set.json"
    with open(active_set_file, 'w') as f:
        json.dump(active_set_data, f)
    
    return active_set_file


class TestStrictModeRequirements:
    """Test strict mode requires active set."""
    
    def test_strict_mode_requires_active_set(self, valid_pack_structure):
        """Strict mode MUST fail if no active set provided."""
        loader = PackLoader(strict=True)  # No active_set
        
        result = loader.load_pack(valid_pack_structure)
        
        assert not result.ok
        assert len(result.errors) == 1
        assert result.errors[0].code == errors.STRICT_MODE_REQUIRES_ACTIVE_SET
        assert result.canonical is False
    
    def test_non_strict_mode_allows_no_active_set(self, valid_pack_structure):
        """Non-strict mode can load without active set (inspection mode)."""
        loader = PackLoader(strict=False)  # No active_set
        
        result = loader.load_pack(valid_pack_structure)
        
        # Should load successfully but marked non-canonical
        assert result.ok
        assert result.canonical is False
        assert result.verification.get("strict_active_set") is False


class TestStrictModeActiveSetEnforcement:
    """Test strict mode enforces active set membership."""
    
    def test_strict_rejects_pack_not_in_active_set(self, valid_pack_structure, tmp_path):
        """Strict loader rejects pack not in active set."""
        # Create active set WITHOUT testpack
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "other_pack",
                    "version": "1.0.0",
                    "content_hash": "sha256:" + "0" * 64
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        loader = PackLoader(active_set=active_set, strict=True)
        result = loader.load_pack(valid_pack_structure)
        
        assert not result.ok
        assert len(result.errors) == 1
        assert result.errors[0].code == errors.PACK_NOT_IN_ACTIVE_SET
        assert result.canonical is False


class TestStrictModeVersionVerification:
    """Test strict mode verifies version matches."""
    
    def test_strict_rejects_version_mismatch(self, valid_pack_structure, tmp_path):
        """Strict loader rejects pack with wrong version."""
        from core.spine.content_hash import compute_pack_hash
        
        # Compute actual hash
        actual_hash = compute_pack_hash(str(valid_pack_structure))
        
        # Create active set with WRONG version
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "2.0.0",  # Wrong version!
                    "content_hash": actual_hash
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        loader = PackLoader(active_set=active_set, strict=True)
        result = loader.load_pack(valid_pack_structure)
        
        assert not result.ok
        assert len(result.errors) == 1
        assert result.errors[0].code == errors.PACK_VERSION_MISMATCH
        assert result.errors[0].context["declared_version"] == "2.0.0"
        assert result.errors[0].context["actual_version"] == "1.0.0"
        assert result.canonical is False


class TestStrictModeHashVerification:
    """Test strict mode verifies content hash matches."""
    
    def test_strict_rejects_hash_mismatch(self, valid_pack_structure, tmp_path):
        """Strict loader rejects pack with wrong hash."""
        # Create active set with WRONG hash
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "1.0.0",
                    "content_hash": "sha256:" + "0" * 64  # Wrong hash!
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        loader = PackLoader(active_set=active_set, strict=True)
        result = loader.load_pack(valid_pack_structure)
        
        assert not result.ok
        assert len(result.errors) == 1
        assert result.errors[0].code == errors.PACK_HASH_MISMATCH
        assert "declared_hash" in result.errors[0].context
        assert "actual_hash" in result.errors[0].context
        assert result.canonical is False


class TestStrictModeSuccess:
    """Test strict mode succeeds with valid pack."""
    
    def test_strict_accepts_valid_pack(self, valid_pack_structure, tmp_path):
        """Strict loader accepts pack with correct hash, version, and membership."""
        from core.spine.content_hash import compute_pack_hash
        
        # Compute actual hash
        actual_hash = compute_pack_hash(str(valid_pack_structure))
        
        # Create active set with CORRECT values
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "1.0.0",
                    "content_hash": actual_hash
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        loader = PackLoader(active_set=active_set, strict=True)
        result = loader.load_pack(valid_pack_structure)
        
        # Should succeed
        assert result.ok
        assert len(result.errors) == 0
        
        # MUST be marked canonical
        assert result.canonical is True
        
        # Verification tracking
        assert result.verification["strict_active_set"] is True
        assert result.verification["hash_verified"] is True
        assert result.verification["version_verified"] is True


class TestNonStrictModeBehavior:
    """Test non-strict mode behavior (inspection only)."""
    
    def test_non_strict_with_active_set_loads_but_non_canonical(self, valid_pack_structure, tmp_path):
        """Non-strict mode with active set loads pack but marks non-canonical."""
        from core.spine.content_hash import compute_pack_hash
        
        actual_hash = compute_pack_hash(str(valid_pack_structure))
        
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "1.0.0",
                    "content_hash": actual_hash
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        loader = PackLoader(active_set=active_set, strict=False)
        result = loader.load_pack(valid_pack_structure)
        
        # Loads successfully
        assert result.ok
        
        # But NOT canonical (no hash verification in non-strict)
        assert result.canonical is False
        assert result.verification.get("strict_active_set") is False
    
    def test_non_strict_without_active_set_marks_inspection_mode(self, valid_pack_structure):
        """Non-strict mode without active set is pure inspection mode."""
        loader = PackLoader(strict=False)  # No active_set
        result = loader.load_pack(valid_pack_structure)
        
        assert result.ok
        assert result.canonical is False
        assert result.verification.get("strict_active_set") is False


class TestCanonicalFlagAuthority:
    """Test that canonical flag is ONLY set by strict mode."""
    
    def test_only_strict_mode_sets_canonical_true(self, valid_pack_structure, tmp_path):
        """ONLY strict mode with successful verification can set canonical=True."""
        from core.spine.content_hash import compute_pack_hash
        
        actual_hash = compute_pack_hash(str(valid_pack_structure))
        
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "1.0.0",
                    "content_hash": actual_hash
                }
            ]
        }
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        # Test 1: Strict mode with success → canonical=True
        strict_loader = PackLoader(active_set=active_set, strict=True)
        strict_result = strict_loader.load_pack(valid_pack_structure)
        assert strict_result.canonical is True
        
        # Test 2: Non-strict mode → canonical=False (even with active set)
        non_strict_loader = PackLoader(active_set=active_set, strict=False)
        non_strict_result = non_strict_loader.load_pack(valid_pack_structure)
        assert non_strict_result.canonical is False
        
        # Test 3: No active set → canonical=False
        no_active_loader = PackLoader(strict=False)
        no_active_result = no_active_loader.load_pack(valid_pack_structure)
        assert no_active_result.canonical is False


class TestErrorCodeLocking:
    """Test that error codes match locked specification."""
    
    def test_error_codes_match_plan(self, valid_pack_structure, tmp_path):
        """Verify error codes match GDU Technical Build Plan v2.4.0."""
        from core.spine.content_hash import compute_pack_hash
        
        actual_hash = compute_pack_hash(str(valid_pack_structure))
        
        # Test STRICT_MODE_REQUIRES_ACTIVE_SET
        loader1 = PackLoader(strict=True)
        result1 = loader1.load_pack(valid_pack_structure)
        assert result1.errors[0].code == "STRICT_MODE_REQUIRES_ACTIVE_SET"
        
        # Test PACK_NOT_IN_ACTIVE_SET
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "other_pack",
                    "version": "1.0.0",
                    "content_hash": "sha256:" + "0" * 64
                }
            ]
        }
        active_set_file = tmp_path / "active_set_no_pack.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        loader2 = PackLoader(active_set=active_set, strict=True)
        result2 = loader2.load_pack(valid_pack_structure)
        assert result2.errors[0].code == "PACK_NOT_IN_ACTIVE_SET"
        
        # Test PACK_VERSION_MISMATCH
        active_set_data["packs"] = [
            {
                "pack_id": "testpack",
                "version": "2.0.0",
                "content_hash": actual_hash
            }
        ]
        active_set_file2 = tmp_path / "active_set_wrong_ver.json"
        with open(active_set_file2, 'w') as f:
            json.dump(active_set_data, f)
        active_set2 = load_active_set_strict(active_set_file2)
        loader3 = PackLoader(active_set=active_set2, strict=True)
        result3 = loader3.load_pack(valid_pack_structure)
        assert result3.errors[0].code == "PACK_VERSION_MISMATCH"
        
        # Test PACK_HASH_MISMATCH
        active_set_data["packs"] = [
            {
                "pack_id": "testpack",
                "version": "1.0.0",
                "content_hash": "sha256:" + "0" * 64
            }
        ]
        active_set_file3 = tmp_path / "active_set_wrong_hash.json"
        with open(active_set_file3, 'w') as f:
            json.dump(active_set_data, f)
        active_set3 = load_active_set_strict(active_set_file3)
        loader4 = PackLoader(active_set=active_set3, strict=True)
        result4 = loader4.load_pack(valid_pack_structure)
        assert result4.errors[0].code == "PACK_HASH_MISMATCH"

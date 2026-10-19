"""
GDU Context Tests

Verifies GDUContext enforces canonical pack loading and prevents bypasses.

Authority: GDU Technical Build Plan v2.4.0 §Phase 3.1
"""

import pytest
import json
import tempfile
from pathlib import Path

from core.gdu.runtime import (
    GDUContext,
    GDULoadResult,
    load_active_gdu,
    set_global_gdu_context,
    get_global_gdu_context,
)
from core.spine.active_set import ActiveSet, PackDeclaration
from core.spine.content_hash import compute_pack_hash


@pytest.fixture
def valid_pack_structure(tmp_path):
    """Create valid test pack."""
    pack_dir = tmp_path / "testpack"
    pack_dir.mkdir()
    
    # Create pack.json
    pack_json = {
        "pack_id": "testpack",
        "version": "1.0.0",
        "name": "Test Pack",
        "description": "Test pack for GDU testing",
        "definitions": []
    }
    with open(pack_dir / "pack.json", 'w') as f:
        json.dump(pack_json, f)
    
    # Create definitions directory with valid definition
    definitions_dir = pack_dir / "definitions"
    definitions_dir.mkdir()
    
    def_json = {
        "id": "testpack.def1",
        "type": "system",
        "version": "1.0.0",
        "description": "Test definition",
        "content": {"value": "test"}
    }
    with open(definitions_dir / "def1.json", 'w') as f:
        json.dump(def_json, f)
    
    # Add definition to pack.json (prevents PACK_EMPTY error)
    pack_json["definitions"] = [{"id": "testpack.def1", "path": "definitions/def1.json"}]
    with open(pack_dir / "pack.json", 'w') as f:
        json.dump(pack_json, f)
    
    return pack_dir


@pytest.fixture
def active_set_with_pack(valid_pack_structure, tmp_path):
    """Create active set with correct hash for test pack."""
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
    return load_active_set_strict(active_set_file)


class TestGDUContextInitialization:
    """Test GDUContext initialization."""
    
    def test_gdu_context_requires_active_set(self):
        """GDUContext requires valid ActiveSet."""
        with pytest.raises(TypeError):
            GDUContext(None)
        
        with pytest.raises(TypeError):
            GDUContext("not_an_active_set")
    
    def test_gdu_context_accepts_active_set(self, active_set_with_pack):
        """GDUContext accepts valid ActiveSet."""
        ctx = GDUContext(active_set_with_pack)
        assert ctx.active_set == active_set_with_pack


class TestGDUContextPackLoading:
    """Test GDUContext pack loading."""
    
    def test_gdu_context_loads_valid_pack_as_canonical(self, valid_pack_structure, active_set_with_pack):
        """GDUContext loads valid pack with canonical=True."""
        ctx = GDUContext(active_set_with_pack)
        result = ctx.load_pack("testpack", valid_pack_structure)
        
        assert result.ok
        assert result.canonical is True  # CRITICAL: Must be canonical in GDU context
        assert result.pack_id == "testpack"
    
    def test_gdu_context_rejects_pack_not_in_active_set(self, valid_pack_structure, tmp_path):
        """GDUContext rejects pack not in active set."""
        # Create empty active set
        active_set_data = {
            "version": "1.0.0",
            "packs": []  # testpack NOT included
        }
        
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        ctx = GDUContext(active_set)
        result = ctx.load_pack("testpack", valid_pack_structure)
        
        assert not result.ok
        assert "PACK_NOT_IN_ACTIVE_SET" in str(result.errors)
    
    def test_gdu_context_verifies_hash(self, valid_pack_structure, tmp_path):
        """GDUContext verifies pack hash."""
        # Create active set with WRONG hash
        wrong_hash = "sha256:0000000000000000000000000000000000000000000000000000000000000000"
        
        active_set_data = {
            "version": "1.0.0",
            "packs": [
                {
                    "pack_id": "testpack",
                    "version": "1.0.0",
                    "content_hash": wrong_hash
                }
            ]
        }
        
        active_set_file = tmp_path / "active_set.json"
        with open(active_set_file, 'w') as f:
            json.dump(active_set_data, f)
        
        from core.spine.active_set import load_active_set_strict
        active_set = load_active_set_strict(active_set_file)
        
        ctx = GDUContext(active_set)
        result = ctx.load_pack("testpack", valid_pack_structure)
        
        assert not result.ok
        assert "PACK_HASH_MISMATCH" in str(result.errors)
    
    def test_gdu_context_stores_loaded_packs(self, valid_pack_structure, active_set_with_pack):
        """GDUContext caches loaded packs."""
        ctx = GDUContext(active_set_with_pack)
        
        result1 = ctx.load_pack("testpack", valid_pack_structure)
        assert result1.ok
        
        # Get from cache
        cached = ctx.get_loaded_pack("testpack")
        assert cached is not None
        assert cached == result1


class TestGDUContextLoadAll:
    """Test GDUContext load_all_active_packs."""
    
    def test_load_all_active_packs_success(self, valid_pack_structure, active_set_with_pack):
        """load_all_active_packs succeeds with valid packs."""
        ctx = GDUContext(active_set_with_pack)
        
        pack_paths = {"testpack": valid_pack_structure}
        result = ctx.load_all_active_packs(pack_paths)
        
        assert result.success is True
        assert "testpack" in result.packs
        assert result.packs["testpack"].ok
        assert result.packs["testpack"].canonical is True
        assert result.all_canonical() is True
    
    def test_load_all_active_packs_missing_pack(self, active_set_with_pack, tmp_path):
        """load_all_active_packs fails with missing pack."""
        ctx = GDUContext(active_set_with_pack)
        
        # Don't provide testpack in pack_paths
        result = ctx.load_all_active_packs({})
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_load_all_returns_gdu_load_result(self, valid_pack_structure, active_set_with_pack):
        """load_all_active_packs returns GDULoadResult."""
        ctx = GDUContext(active_set_with_pack)
        
        pack_paths = {"testpack": valid_pack_structure}
        result = ctx.load_all_active_packs(pack_paths)
        
        assert isinstance(result, GDULoadResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'packs')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'all_canonical')


class TestGlobalGDUContext:
    """Test module-level GDU context functions."""
    
    def test_set_global_context(self, active_set_with_pack):
        """Can set global GDU context."""
        ctx = GDUContext(active_set_with_pack)
        set_global_gdu_context(ctx)
        
        retrieved = get_global_gdu_context()
        assert retrieved is ctx
    
    def test_load_active_gdu_requires_global_context(self, valid_pack_structure):
        """load_active_gdu fails without global context."""
        # Clear global context
        set_global_gdu_context(None)
        
        with pytest.raises(RuntimeError, match="No global GDU context"):
            load_active_gdu("testpack", valid_pack_structure)
    
    def test_load_active_gdu_with_global_context(self, valid_pack_structure, active_set_with_pack):
        """load_active_gdu works with global context."""
        ctx = GDUContext(active_set_with_pack)
        set_global_gdu_context(ctx)
        
        result = load_active_gdu("testpack", valid_pack_structure)
        
        assert result.ok
        assert result.canonical is True
    
    def test_load_active_gdu_guaranteed_canonical(self, valid_pack_structure, active_set_with_pack):
        """load_active_gdu guarantees canonical flag."""
        ctx = GDUContext(active_set_with_pack)
        set_global_gdu_context(ctx)
        
        result = load_active_gdu("testpack", valid_pack_structure)
        
        # CRITICAL: load_active_gdu ALWAYS returns canonical=True on success
        if result.ok:
            assert result.canonical is True


class TestGDUCriticalInvariants:
    """Test critical GDU invariants."""
    
    def test_cannot_bypass_with_non_canonical_pack(self, valid_pack_structure, active_set_with_pack):
        """Cannot load non-canonical pack through GDU."""
        ctx = GDUContext(active_set_with_pack)
        
        # Load through GDU (strict mode)
        result = ctx.load_pack("testpack", valid_pack_structure)
        
        # If it loaded, it MUST be canonical
        if result.ok:
            assert result.canonical is True, (
                "CRITICAL: Pack loaded through GDUContext but canonical=False. "
                "This violates GDU invariant."
            )
    
    def test_gdu_context_enforces_strict_mode(self, valid_pack_structure, active_set_with_pack):
        """GDUContext always uses strict mode internally."""
        ctx = GDUContext(active_set_with_pack)
        
        # GDU context should have created a strict loader
        assert ctx._loader.strict is True
    
    def test_verify_all_canonical_checks_all_packs(self, valid_pack_structure, active_set_with_pack):
        """verify_all_canonical checks all loaded packs."""
        ctx = GDUContext(active_set_with_pack)
        
        # Load pack
        ctx.load_pack("testpack", valid_pack_structure)
        
        # All should be canonical
        assert ctx.verify_all_canonical() is True


class TestGDUEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_get_loaded_pack_not_found(self, active_set_with_pack):
        """get_loaded_pack returns None for non-loaded pack."""
        ctx = GDUContext(active_set_with_pack)
        
        result = ctx.get_loaded_pack("nonexistent")
        assert result is None
    
    def test_get_all_loaded_packs_returns_copy(self, valid_pack_structure, active_set_with_pack):
        """get_all_loaded_packs returns new dict (not reference)."""
        ctx = GDUContext(active_set_with_pack)
        ctx.load_pack("testpack", valid_pack_structure)
        
        packs1 = ctx.get_all_loaded_packs()
        packs2 = ctx.get_all_loaded_packs()
        
        # Should be equal but not same object
        assert packs1 == packs2
        assert packs1 is not packs2
    
    def test_multiple_gdu_contexts_independent(self, valid_pack_structure, active_set_with_pack):
        """Multiple GDUContext instances are independent."""
        ctx1 = GDUContext(active_set_with_pack)
        ctx2 = GDUContext(active_set_with_pack)
        
        ctx1.load_pack("testpack", valid_pack_structure)
        
        # ctx2 should not have the pack
        assert ctx1.get_loaded_pack("testpack") is not None
        assert ctx2.get_loaded_pack("testpack") is None

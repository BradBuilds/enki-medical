"""
ENKI Spine S1.0 - Spine-Only Boot Mode Test

Critical Test: Proves the spine can reject data it's never seen before.

This test validates:
1. System boots with zero domain packs
2. Active set enforcement prevents unauthorized pack loading
3. System produces stable proof output (even if trivial)
4. "Fail-closed" behavior is enforced

Success Criteria:
- Empty active set loads successfully
- Pack loader rejects all domain packs not in active set
- No silent failures or fallbacks
- Deterministic behavior across runs
"""

import pytest
from pathlib import Path
from core.spine.active_set import ActiveSet
from core.packs.loader import PackLoader
from core.packs import errors


class TestSpineOnlyBootMode:
    """
    Spine-Only Boot Mode Test Suite
    
    Validates that ENKI's spine can function with ZERO domain packs.
    """
    
    def test_empty_active_set_loads(self):
        """Empty active set creates successfully (spine-only mode)."""
        active_set = ActiveSet.empty()
        
        assert active_set.is_spine_only()
        assert len(active_set.packs) == 0
        assert active_set.version == "0.1.0"
    
    def test_loader_with_empty_active_set_rejects_all_packs(self):
        """Pack loader with empty active set rejects ALL domain packs."""
        active_set = ActiveSet.empty()
        loader = PackLoader(active_set=active_set)
        
        # Try to load base60 pack (should be rejected)
        base60_path = Path("libraries/base60")
        if base60_path.exists():
            result = loader.load_pack(base60_path)
            
            assert not result.ok
            assert result.has_errors()
            assert any(
                err.code == errors.PACK_NOT_IN_ACTIVE_SET 
                for err in result.errors
            )
    
    def test_loader_with_empty_active_set_rejects_identity_pack(self):
        """Pack loader with empty active set rejects identity pack."""
        active_set = ActiveSet.empty()
        loader = PackLoader(active_set=active_set)
        
        # Try to load identity pack (should be rejected)
        identity_path = Path("libraries/identity")
        if identity_path.exists():
            result = loader.load_pack(identity_path)
            
            assert not result.ok
            assert result.has_errors()
            assert any(
                err.code == errors.PACK_NOT_IN_ACTIVE_SET 
                for err in result.errors
            )
    
    def test_loader_without_active_set_allows_packs(self):
        """Pack loader WITHOUT active set allows packs (backward compatibility)."""
        loader = PackLoader()  # No active set
        
        # Try to load base60 pack (should succeed if pack is valid)
        base60_path = Path("libraries/base60")
        if base60_path.exists():
            result = loader.load_pack(base60_path)
            
            # Should succeed (no active set enforcement)
            # NOTE: May have other errors if pack is invalid, but NOT PACK_NOT_IN_ACTIVE_SET
            if result.has_errors():
                assert not any(
                    err.code == errors.PACK_NOT_IN_ACTIVE_SET 
                    for err in result.errors
                ), "Should not have active set rejection without active set"
    
    def test_loader_with_allowed_pack_succeeds(self):
        """Pack loader with pack in active set allows that pack."""
        from core.spine.active_set import PackDeclaration
        
        active_set = ActiveSet(
            version="1.0.0",
            packs=[PackDeclaration("base60", "0.1.0")]
        )
        loader = PackLoader(active_set=active_set)
        
        # Try to load base60 pack (should be allowed)
        base60_path = Path("libraries/base60")
        if base60_path.exists():
            result = loader.load_pack(base60_path)
            
            # Should not have active set rejection
            assert not any(
                err.code == errors.PACK_NOT_IN_ACTIVE_SET 
                for err in result.errors
            )
    
    def test_spine_only_rejection_is_deterministic(self):
        """Spine-only rejection is deterministic across multiple attempts."""
        active_set = ActiveSet.empty()
        loader = PackLoader(active_set=active_set)
        
        base60_path = Path("libraries/base60")
        if not base60_path.exists():
            pytest.skip("base60 pack not found")
        
        # Load twice, should get identical results
        result1 = loader.load_pack(base60_path)
        result2 = loader.load_pack(base60_path)
        
        assert result1.ok == result2.ok
        assert len(result1.errors) == len(result2.errors)
        assert result1.errors[0].code == result2.errors[0].code
    
    def test_spine_only_error_message_clarity(self):
        """Spine-only rejection provides clear error message."""
        active_set = ActiveSet.empty()
        loader = PackLoader(active_set=active_set)
        
        base60_path = Path("libraries/base60")
        if not base60_path.exists():
            pytest.skip("base60 pack not found")
        
        result = loader.load_pack(base60_path)
        
        assert not result.ok
        error = result.errors[0]
        assert error.code == errors.PACK_NOT_IN_ACTIVE_SET
        assert "spine" in error.message.lower() or "active set" in error.message.lower()
        assert error.context is not None
        assert "active_set_mode" in error.context
        assert error.context["active_set_mode"] == "spine-only"


class TestSpineProofOutput:
    """
    Test that spine produces stable proof output.
    
    Even in spine-only mode with no domain data, the system should
    produce consistent, verifiable output.
    """
    
    def test_empty_active_set_serialization_stable(self):
        """Empty active set serializes consistently."""
        active_set1 = ActiveSet.empty()
        active_set2 = ActiveSet.empty()
        
        dict1 = active_set1.to_dict()
        dict2 = active_set2.to_dict()
        
        assert dict1 == dict2
    
    def test_rejection_result_structure_stable(self):
        """Pack rejection result has stable structure."""
        active_set = ActiveSet.empty()
        loader = PackLoader(active_set=active_set)
        
        base60_path = Path("libraries/base60")
        if not base60_path.exists():
            pytest.skip("base60 pack not found")
        
        result = loader.load_pack(base60_path)
        
        # Verify stable structure
        assert hasattr(result, 'ok')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'pack_id')
        assert not result.ok
        assert len(result.errors) > 0


class TestFailClosedBehavior:
    """
    Test that spine enforces fail-closed behavior.
    
    If something is not explicitly allowed, it is rejected.
    No silent fallbacks, no "best effort" modes.
    """
    
    def test_unknown_pack_explicitly_rejected(self):
        """Unknown pack is explicitly rejected, not silently ignored."""
        active_set = ActiveSet(
            version="1.0.0",
            packs=[]  # Empty, but explicitly created
        )
        loader = PackLoader(active_set=active_set)
        
        # Try to load any pack
        base60_path = Path("libraries/base60")
        if not base60_path.exists():
            pytest.skip("base60 pack not found")
        
        result = loader.load_pack(base60_path)
        
        # Must explicitly reject, not silently skip
        assert not result.ok
        assert len(result.errors) > 0
        assert result.errors[0].code == errors.PACK_NOT_IN_ACTIVE_SET
    
    def test_no_silent_fallback_to_permissive_mode(self):
        """Empty active set does not silently become permissive."""
        active_set = ActiveSet.empty()
        
        # Verify it stays in spine-only mode
        assert active_set.is_spine_only()
        assert not active_set.is_pack_allowed("base60")
        assert not active_set.is_pack_allowed("identity")
        assert not active_set.is_pack_allowed("any_pack")
    
    def test_partial_allowlist_rejects_others(self):
        """Active set with one pack rejects all others."""
        from core.spine.active_set import PackDeclaration
        
        active_set = ActiveSet(
            version="1.0.0",
            packs=[PackDeclaration("base60", "0.1.0")]
        )
        
        assert active_set.is_pack_allowed("base60")
        assert not active_set.is_pack_allowed("identity")
        assert not active_set.is_pack_allowed("unknown")


# ============================================================
# CRITICAL SUCCESS METRIC
# ============================================================

def test_spine_can_reject_data_never_seen():
    """
    CRITICAL TEST: Spine can reject data it has never seen before.
    
    This is the fundamental proof that the spine is abstract and
    does not depend on domain data to function.
    
    If this test passes, we have proven:
    1. Spine has explicit allow-list enforcement
    2. Spine rejects by default (fail-closed)
    3. Spine operates without domain knowledge
    """
    # Create empty active set (no domain packs)
    active_set = ActiveSet.empty()
    assert active_set.is_spine_only()
    
    # Create loader with active set enforcement
    loader = PackLoader(active_set=active_set)
    
    # Try to load ANY pack (simulating never-seen domain data)
    test_packs = ["libraries/base60", "libraries/identity", "libraries/assertion_vocab"]
    
    rejections = []
    for pack_path_str in test_packs:
        pack_path = Path(pack_path_str)
        if pack_path.exists():
            result = loader.load_pack(pack_path)
            
            # Pack MUST be rejected
            assert not result.ok, f"Pack {pack_path_str} should be rejected in spine-only mode"
            assert result.has_errors()
            
            # Rejection MUST be due to active set enforcement
            has_active_set_error = any(
                err.code == errors.PACK_NOT_IN_ACTIVE_SET 
                for err in result.errors
            )
            assert has_active_set_error, f"Pack {pack_path_str} must be rejected by active set"
            
            rejections.append(pack_path_str)
    
    # We must have successfully rejected at least one pack
    assert len(rejections) > 0, "No packs found to test rejection"
    
    print(f"\n✅ SPINE PROOF: Successfully rejected {len(rejections)} domain packs without domain knowledge")
    print(f"   Rejected packs: {rejections}")

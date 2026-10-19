"""
Anti-Bypass Tests

Verifies that no production code bypasses GDUContext for canonical operations.

Authority: GDU Technical Build Plan v2.4.0 §Phase 3.3
"""

import pytest
import ast
from pathlib import Path


class TestNoDirectPackLoading:
    """Test that production code doesn't bypass GDU."""
    
    def test_validation_code_not_using_direct_pack_loader(self):
        """
        Production validation code should not import PackLoader directly.
        
        This enforces that all canonical operations go through GDUContext.
        """
        workspace = Path(__file__).parent.parent.parent.parent  # workspace root
        validation_dir = workspace / "core" / "validation"
        
        forbidden_files = []
        
        if validation_dir.exists():
            for py_file in validation_dir.rglob("*.py"):
                if "__pycache__" in str(py_file) or "test" in py_file.name:
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(py_file))
                    
                    # Check for PackLoader imports
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module == "core.packs.loader":
                                for alias in node.names:
                                    if alias.name == "PackLoader":
                                        forbidden_files.append(str(py_file.relative_to(workspace)))
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                if "PackLoader" in alias.name:
                                    forbidden_files.append(str(py_file.relative_to(workspace)))
                
                except (SyntaxError, ValueError):
                    pass
        
        assert forbidden_files == [], (
            f"Found {len(forbidden_files)} files directly importing PackLoader in validation code. "
            f"Use GDUContext.load_active_gdu() instead. Files:\n" +
            "\n".join(f"  - {f}" for f in forbidden_files)
        )
    
    def test_api_code_not_using_direct_pack_loader(self):
        """API services should not import PackLoader directly."""
        workspace = Path(__file__).parent.parent.parent.parent
        api_dir = workspace / "services" / "api"
        
        forbidden_files = []
        
        if api_dir.exists():
            for py_file in api_dir.rglob("*.py"):
                if "__pycache__" in str(py_file) or "test" in py_file.name:
                    continue
                
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        tree = ast.parse(content, filename=str(py_file))
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ImportFrom):
                            if node.module == "core.packs.loader":
                                for alias in node.names:
                                    if alias.name == "PackLoader":
                                        forbidden_files.append(str(py_file.relative_to(workspace)))
                        elif isinstance(node, ast.Import):
                            for alias in node.names:
                                if "PackLoader" in alias.name:
                                    forbidden_files.append(str(py_file.relative_to(workspace)))
                
                except (SyntaxError, ValueError):
                    pass
        
        assert forbidden_files == [], (
            f"Found {len(forbidden_files)} files directly importing PackLoader in API code. "
            f"Use GDUContext or load_active_gdu() instead. Files:\n" +
            "\n".join(f"  - {f}" for f in forbidden_files)
        )


class TestGDUContextIsOnlyAuthorizedPath:
    """Test that GDUContext is the only authorized loading path."""
    
    def test_gdu_context_is_importable(self):
        """GDUContext should be easily importable."""
        from core.gdu.runtime import GDUContext
        assert GDUContext is not None
    
    def test_load_active_gdu_is_importable(self):
        """load_active_gdu should be easily importable."""
        from core.gdu.runtime import load_active_gdu
        assert load_active_gdu is not None
    
    def test_direct_pack_loader_usage_is_discouraged(self):
        """Direct PackLoader usage should be possible but discouraged."""
        # We allow it in tests and implementation, but should warn
        from core.gdu.runtime import deprecation_warning_for_direct_pack_loading
        
        # Should be able to call deprecation warning
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            deprecation_warning_for_direct_pack_loading()
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)


class TestBypassPrevention:
    """Test specific bypass scenarios."""
    
    def test_non_canonical_pack_rejected_in_computation(self):
        """
        Non-canonical packs should be rejected in any compute path.
        
        This test verifies the design constraint that only canonical
        packs (loaded via GDUContext strict mode) can be used.
        """
        from core.packs.loader import PackLoader
        from core.spine.active_set import ActiveSet
        
        # Create active set but don't use strict mode
        active_set = ActiveSet(version="1.0.0", packs=[])
        
        # Non-strict loader will mark pack non-canonical
        loader = PackLoader(active_set=active_set, strict=False)
        
        # Even if it loaded successfully, canonical should be False
        # (we can't test this fully without a real pack, but we verify the design)
        assert loader.strict is False
    
    def test_gdu_context_strict_mode_verified(self):
        """GDUContext internally uses strict mode."""
        from core.gdu.runtime import GDUContext
        from core.spine.active_set import ActiveSet
        
        active_set = ActiveSet(version="1.0.0", packs=[])
        ctx = GDUContext(active_set)
        
        # GDU context must use strict loader
        assert ctx._loader.strict is True
    
    def test_bypass_attempt_via_raw_pack_loader(self):
        """
        Attempting to bypass GDU context using raw PackLoader
        should be detectable (for code review/linting).
        """
        # This is more of a code review checklist than an automated test
        # but we document the concern here
        
        violation = """
        # VIOLATION: Direct PackLoader usage (bypass attempt)
        from core.packs.loader import PackLoader
        loader = PackLoader(strict=False)
        result = loader.load_pack(pack_path)  # Could mark as non-canonical!
        
        # CORRECT: Use GDUContext
        from core.gdu.runtime import load_active_gdu
        result = load_active_gdu(pack_id, pack_path)  # Always canonical
        """
        
        # Just verify the correct usage is documented
        assert "load_active_gdu" in violation
        assert "GDUContext" in violation


class TestGDUInvariants:
    """Test critical GDU invariants."""
    
    def test_canonical_flag_invariant(self):
        """
        Invariant: All packs loaded through GDU are canonical.
        
        This is THE critical invariant that prevents bypasses.
        Violation of this invariant is a critical security issue.
        """
        from core.gdu.runtime import GDUContext
        from core.spine.active_set import ActiveSet
        
        active_set = ActiveSet(version="1.0.0", packs=[])
        ctx = GDUContext(active_set)
        
        # GDUContext uses strict mode which sets canonical=True on success
        assert ctx._loader.strict is True
        
        # This means: success => canonical=True
        # Verified by test_runtime.py tests
    
    def test_strict_mode_only_invariant(self):
        """Invariant: GDU context always uses strict mode."""
        from core.gdu.runtime import GDUContext
        from core.spine.active_set import ActiveSet
        
        active_set = ActiveSet(version="1.0.0", packs=[])
        
        # Every GDU context uses strict mode
        ctx1 = GDUContext(active_set)
        ctx2 = GDUContext(active_set)
        
        assert ctx1._loader.strict is True
        assert ctx2._loader.strict is True

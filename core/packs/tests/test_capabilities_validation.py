"""
ENKI Spine S1.1 — Capability Validation Tests

Tests for capability declaration validation:
- Shape validation (lists, dicts, required fields)
- Regex pattern enforcement
- Duplicate detection
- Deterministic error ordering
"""

import pytest
from core.packs.types import PackManifest
from core.packs.capabilities import validate_capabilities
from core.packs import errors


def test_empty_capabilities_valid():
    """Empty capability arrays should pass validation."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[],
        capabilities_required=[]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 0


def test_valid_capability_declarations():
    """Well-formed capability declarations should pass."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "numeric.base60", "version": "1.0.0"}
        ],
        capabilities_required=[
            {"capability": "core.validation", "version": "2.1.3"}
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 0


def test_invalid_capability_name_pattern():
    """Capability names must match lowercase dot-path pattern."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "Numeric.Base60", "version": "1.0.0"},  # Uppercase
            {"capability": "valid.name", "version": "1.0.0"},
            {"capability": "invalid-name", "version": "1.0.0"},  # Hyphen
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 2  # Two invalid patterns
    assert all(err.code == errors.INVALID_CAPABILITY_DECLARATION for err in result)


def test_invalid_version_pattern():
    """Versions must match semver pattern."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0"},  # Missing patch
            {"capability": "test.cap2", "version": "v1.0.0"},  # Prefix
            {"capability": "test.cap3", "version": "1.0.0"},  # Valid
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 2
    assert all(err.code == errors.INVALID_CAPABILITY_DECLARATION for err in result)


def test_missing_required_fields():
    """Missing 'capability' or 'version' fields should error."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap"},  # Missing version
            {"version": "1.0.0"},  # Missing capability
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 2
    assert all(err.code == errors.INVALID_CAPABILITY_DECLARATION for err in result)


def test_duplicate_capability_in_same_pack():
    """Duplicate (capability, version) tuples within same pack should error."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"},
            {"capability": "test.cap", "version": "1.0.0"},  # Duplicate
            {"capability": "test.cap", "version": "2.0.0"},  # Different version, OK
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 1
    assert result[0].code == errors.DUPLICATE_CAPABILITY_DECLARATION
    assert result[0].context["capability"] == "test.cap"
    assert result[0].context["version"] == "1.0.0"


def test_validation_error_deterministic_ordering():
    """Validation errors must be sorted deterministically."""
    # Create multiple manifests with various errors
    manifest_a = PackManifest(
        pack_id="a.pack",
        version="1.0.0",
        name="Pack A",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "Invalid", "version": "1.0.0"},  # Invalid at index 0
        ]
    )
    
    manifest_b = PackManifest(
        pack_id="b.pack",
        version="1.0.0",
        name="Pack B",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "invalid"},  # Invalid at index 0
        ]
    )
    
    manifest_c = PackManifest(
        pack_id="a.pack2",
        version="1.0.0",
        name="Pack A2",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"version": "1.0.0"},  # Missing capability at index 0
        ]
    )
    
    # Run validation multiple times with different manifest orders
    result1 = validate_capabilities([manifest_a, manifest_b, manifest_c])
    result2 = validate_capabilities([manifest_c, manifest_a, manifest_b])
    result3 = validate_capabilities([manifest_b, manifest_c, manifest_a])
    
    # Extract error signatures (code + pack_id + field)
    def error_sig(err):
        return (err.code, err.context.get("pack_id"), err.context.get("field"))
    
    sigs1 = [error_sig(e) for e in result1]
    sigs2 = [error_sig(e) for e in result2]
    sigs3 = [error_sig(e) for e in result3]
    
    # All orderings should produce identical sequences
    assert sigs1 == sigs2 == sigs3


def test_validation_accumulates_all_errors():
    """Validation should collect ALL errors, not halt on first."""
    manifests = [
        PackManifest(
            pack_id=f"pack{i}",
            version="1.0.0",
            name=f"Pack {i}",
            description="Test",
            definitions=[],
            capabilities_provided=[
                {"capability": "Invalid", "version": "1.0.0"}  # Invalid pattern
            ]
        )
        for i in range(5)
    ]
    
    result = validate_capabilities(manifests)
    assert len(result) == 5  # Should have 5 errors, one from each pack


def test_field_ordering_in_validation_errors():
    """Errors should sort by field: capabilities_provided before capabilities_required."""
    manifest = PackManifest(
        pack_id="test.pack",
        version="1.0.0",
        name="Test Pack",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "BAD", "version": "1.0.0"}  # Invalid
        ],
        capabilities_required=[
            {"capability": "ALSO.BAD", "version": "1.0.0"}  # Invalid
        ]
    )
    
    result = validate_capabilities([manifest])
    assert len(result) == 2
    # capabilities_provided error should come first
    assert result[0].context["field"] == "capabilities_provided"
    assert result[1].context["field"] == "capabilities_required"


def test_validation_sort_key_exact_order():
    """Validation errors must sort by exact locked key: (pack_id, field, index/capability)."""
    # Create manifests with both INVALID and DUPLICATE errors
    manifest_a = PackManifest(
        pack_id="a.pack",
        version="1.0.0",
        name="Pack A",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "INVALID", "version": "1.0.0"},  # INVALID at index 0
            {"capability": "valid.cap", "version": "1.0.0"},
            {"capability": "valid.cap", "version": "1.0.0"},  # DUPLICATE
        ],
        capabilities_required=[
            {"version": "1.0.0"}  # INVALID (missing capability) at index 0
        ]
    )
    
    manifest_b = PackManifest(
        pack_id="b.pack",
        version="1.0.0",
        name="Pack B",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"},
            {"capability": "test.cap", "version": "1.0.0"},  # DUPLICATE
        ]
    )
    
    # Run with different orderings
    result1 = validate_capabilities([manifest_a, manifest_b])
    result2 = validate_capabilities([manifest_b, manifest_a])
    
    # Both should produce identical error signatures in identical order
    def error_sig(err):
        return (
            err.code,
            err.context.get("pack_id"),
            err.context.get("field"),
            err.context.get("index", -1),
            err.context.get("capability", ""),
            err.context.get("version", "")
        )
    
    sigs1 = [error_sig(e) for e in result1]
    sigs2 = [error_sig(e) for e in result2]
    
    # Must be identical
    assert sigs1 == sigs2
    
    # Verify ordering follows locked spec: pack_id → field → index (INVALID before DUPLICATE)
    # Expected order:
    # 1. a.pack, capabilities_provided, index 0 (INVALID)
    # 2. a.pack, capabilities_provided, duplicate (valid.cap, 1.0.0)
    # 3. a.pack, capabilities_required, index 0 (INVALID)
    # 4. b.pack, capabilities_provided, duplicate (test.cap, 1.0.0)
    
    assert result1[0].context["pack_id"] == "a.pack"
    assert result1[0].context["field"] == "capabilities_provided"
    assert result1[0].context["index"] == 0
    assert result1[0].code == errors.INVALID_CAPABILITY_DECLARATION
    
    assert result1[1].context["pack_id"] == "a.pack"
    assert result1[1].context["field"] == "capabilities_provided"
    assert result1[1].code == errors.DUPLICATE_CAPABILITY_DECLARATION
    assert result1[1].context["capability"] == "valid.cap"
    
    assert result1[2].context["pack_id"] == "a.pack"
    assert result1[2].context["field"] == "capabilities_required"
    assert result1[2].context["index"] == 0
    
    assert result1[3].context["pack_id"] == "b.pack"
    assert result1[3].code == errors.DUPLICATE_CAPABILITY_DECLARATION


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

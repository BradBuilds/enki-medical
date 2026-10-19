"""
ENKI Spine S1.1 — Capability Resolution Tests

Tests for capability requirement resolution:
- Missing capability detection
- Ambiguous capability detection
- Version mismatch detection
- Happy path resolution
- Deterministic behavior
"""

import pytest
from core.packs.types import PackManifest
from core.packs.capabilities import resolve_capabilities
from core.packs import errors


def test_no_requirements_no_errors():
    """Packs with no requirements should resolve successfully."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[]  # No requirements
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 0


def test_successful_resolution():
    """Valid requirement with exactly one provider should resolve."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "numeric.base60", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "numeric.base60", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 0  # No errors


def test_missing_capability():
    """Required capability with no provider should error."""
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "missing.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([consumer])
    assert len(result) == 1
    assert result[0].code == errors.MISSING_CAPABILITY
    assert result[0].context["consumer_pack_id"] == "consumer.pack"
    assert result[0].context["capability"] == "missing.cap"
    assert result[0].context["version"] == "1.0.0"


def test_ambiguous_capability():
    """Multiple providers for same (capability, version) should error."""
    provider1 = PackManifest(
        pack_id="provider.a",
        version="1.0.0",
        name="Provider A",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    provider2 = PackManifest(
        pack_id="provider.b",
        version="1.0.0",
        name="Provider B",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider1, provider2, consumer])
    assert len(result) == 1
    assert result[0].code == errors.AMBIGUOUS_CAPABILITY
    assert result[0].context["consumer_pack_id"] == "consumer.pack"
    assert result[0].context["capability"] == "test.cap"
    assert result[0].context["providers"] == ["provider.a", "provider.b"]


def test_version_mismatch():
    """Capability exists but with wrong version should error."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"},
            {"capability": "test.cap", "version": "2.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.5.0"}  # No provider for this version
        ]
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 1
    assert result[0].code == errors.CAPABILITY_VERSION_MISMATCH
    assert result[0].context["consumer_pack_id"] == "consumer.pack"
    assert result[0].context["capability"] == "test.cap"
    assert result[0].context["required_version"] == "1.5.0"
    
    # Check available versions
    available = result[0].context["available_versions"]
    assert len(available) == 2
    assert {"pack_id": "provider.pack", "version": "1.0.0"} in available
    assert {"pack_id": "provider.pack", "version": "2.0.0"} in available


def test_version_matching_is_exact():
    """Version matching must be exact string equality, not semver compatible."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.0.1"}  # Different patch
        ]
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 1
    assert result[0].code == errors.CAPABILITY_VERSION_MISMATCH


def test_multiple_consumers_same_requirement():
    """Multiple consumers requiring same capability should resolve if single provider."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "shared.cap", "version": "1.0.0"}
        ]
    )
    
    consumer1 = PackManifest(
        pack_id="consumer.a",
        version="1.0.0",
        name="Consumer A",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "shared.cap", "version": "1.0.0"}
        ]
    )
    
    consumer2 = PackManifest(
        pack_id="consumer.b",
        version="1.0.0",
        name="Consumer B",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "shared.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider, consumer1, consumer2])
    assert len(result) == 0  # Should resolve successfully


def test_resolution_determinism():
    """Resolution errors should be deterministic regardless of manifest order."""
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "2.0.0"}
        ]
    )
    
    consumer1 = PackManifest(
        pack_id="consumer.a",
        version="1.0.0",
        name="Consumer A",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer2 = PackManifest(
        pack_id="consumer.b",
        version="1.0.0",
        name="Consumer B",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "missing.cap", "version": "1.0.0"}
        ]
    )
    
    # Try different orderings
    result1 = resolve_capabilities([provider, consumer1, consumer2])
    result2 = resolve_capabilities([consumer2, provider, consumer1])
    result3 = resolve_capabilities([consumer1, consumer2, provider])
    
    # All should have same number of errors
    assert len(result1) == len(result2) == len(result3) == 2
    
    # Extract error signatures
    def error_sig(err):
        return (err.code, err.context.get("consumer_pack_id"), err.context.get("capability"))
    
    sigs1 = sorted([error_sig(e) for e in result1])
    sigs2 = sorted([error_sig(e) for e in result2])
    sigs3 = sorted([error_sig(e) for e in result3])
    
    assert sigs1 == sigs2 == sigs3


def test_available_versions_sorted():
    """Available versions in VERSION_MISMATCH error must be sorted."""
    provider1 = PackManifest(
        pack_id="z.provider",
        version="1.0.0",
        name="Provider Z",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "2.0.0"}
        ]
    )
    
    provider2 = PackManifest(
        pack_id="a.provider",
        version="1.0.0",
        name="Provider A",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "3.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider1, provider2, consumer])
    assert len(result) == 1
    
    available = result[0].context["available_versions"]
    # Should be sorted by (pack_id, version)
    assert available[0]["pack_id"] == "a.provider"
    assert available[1]["pack_id"] == "z.provider"


def test_missing_capability_context_exact_keys():
    """MISSING_CAPABILITY error context must have exact keys (no higher-precedence fields)."""
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "missing.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([consumer])
    assert len(result) == 1
    assert result[0].code == errors.MISSING_CAPABILITY
    
    # Assert EXACT keys - no definition_id or other higher-precedence fields
    context_keys = set(result[0].context.keys())
    expected_keys = {"consumer_pack_id", "capability", "version"}
    assert context_keys == expected_keys, f"Context keys mismatch. Expected {expected_keys}, got {context_keys}"


def test_ambiguous_capability_context_exact_keys():
    """AMBIGUOUS_CAPABILITY error context must have exact keys."""
    provider1 = PackManifest(
        pack_id="provider.a",
        version="1.0.0",
        name="Provider A",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    provider2 = PackManifest(
        pack_id="provider.b",
        version="1.0.0",
        name="Provider B",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider1, provider2, consumer])
    assert len(result) == 1
    assert result[0].code == errors.AMBIGUOUS_CAPABILITY
    
    # Assert EXACT keys
    context_keys = set(result[0].context.keys())
    expected_keys = {"consumer_pack_id", "capability", "version", "providers"}
    assert context_keys == expected_keys, f"Context keys mismatch. Expected {expected_keys}, got {context_keys}"
    
    # Verify providers is sorted list
    assert result[0].context["providers"] == ["provider.a", "provider.b"]


def test_version_mismatch_context_exact_keys():
    """VERSION_MISMATCH error context must have exact keys with sorted available_versions."""
    provider = PackManifest(
        pack_id="z.provider",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "2.0.0"},
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.5.0"}
        ]
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 1
    assert result[0].code == errors.CAPABILITY_VERSION_MISMATCH
    
    # Assert EXACT keys
    context_keys = set(result[0].context.keys())
    expected_keys = {"consumer_pack_id", "capability", "required_version", "available_versions"}
    assert context_keys == expected_keys, f"Context keys mismatch. Expected {expected_keys}, got {context_keys}"
    
    # Verify available_versions is sorted by (pack_id, version)
    available = result[0].context["available_versions"]
    assert len(available) == 2
    assert available[0] == {"pack_id": "z.provider", "version": "1.0.0"}
    assert available[1] == {"pack_id": "z.provider", "version": "2.0.0"}


def test_version_mismatch_requires_capability_exists():
    """VERSION_MISMATCH must only trigger when capability exists with different versions."""
    # Provider offers different capability
    provider = PackManifest(
        pack_id="provider.pack",
        version="1.0.0",
        name="Provider",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "other.cap", "version": "1.0.0"}
        ]
    )
    
    consumer = PackManifest(
        pack_id="consumer.pack",
        version="1.0.0",
        name="Consumer",
        description="Test",
        definitions=[],
        capabilities_required=[
            {"capability": "test.cap", "version": "1.0.0"}
        ]
    )
    
    result = resolve_capabilities([provider, consumer])
    assert len(result) == 1
    # Should be MISSING, not VERSION_MISMATCH
    assert result[0].code == errors.MISSING_CAPABILITY
    
    # Now test with same capability but different version
    provider2 = PackManifest(
        pack_id="provider2.pack",
        version="1.0.0",
        name="Provider 2",
        description="Test",
        definitions=[],
        capabilities_provided=[
            {"capability": "test.cap", "version": "2.0.0"}
        ]
    )
    
    result2 = resolve_capabilities([provider2, consumer])
    assert len(result2) == 1
    # Should be VERSION_MISMATCH, not MISSING
    assert result2[0].code == errors.CAPABILITY_VERSION_MISMATCH


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

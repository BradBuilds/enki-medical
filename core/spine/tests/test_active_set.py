"""
ENKI Spine S1.0 - Active Set Tests

Tests for the active definition set module.
"""

import json
import pytest
from pathlib import Path
from core.spine.active_set import (
    ActiveSet,
    PackDeclaration,
    validate_active_set,
    load_active_set
)


def test_empty_active_set_creation():
    """Empty active set creates spine-only mode."""
    active_set = ActiveSet.empty()
    
    assert active_set.version == "0.1.0"
    assert len(active_set.packs) == 0
    assert active_set.is_spine_only()
    assert not active_set.is_pack_allowed("base60")
    assert not active_set.is_pack_allowed("identity")


def test_active_set_with_packs():
    """Active set with packs allows those packs."""
    active_set = ActiveSet(
        version="1.0.0",
        packs=[
            PackDeclaration("base60", "1.0.0"),
            PackDeclaration("identity", "1.0.0")
        ]
    )
    
    assert not active_set.is_spine_only()
    assert active_set.is_pack_allowed("base60")
    assert active_set.is_pack_allowed("identity")
    assert not active_set.is_pack_allowed("unknown_pack")


def test_pack_with_content_hash():
    """Pack declaration can include content hash."""
    pack_decl = PackDeclaration(
        "base60",
        "1.0.0",
        "sha256:abc123def456"
    )
    
    assert pack_decl.pack_id == "base60"
    assert pack_decl.version == "1.0.0"
    assert pack_decl.content_hash == "sha256:abc123def456"


def test_active_set_to_dict():
    """Active set serializes to dictionary correctly."""
    active_set = ActiveSet(
        version="1.0.0",
        packs=[
            PackDeclaration("base60", "1.0.0", "sha256:abc123")
        ],
        metadata={"author": "ENKI"}
    )
    
    data = active_set.to_dict()
    
    assert data["version"] == "1.0.0"
    assert len(data["packs"]) == 1
    assert data["packs"][0]["pack_id"] == "base60"
    assert data["packs"][0]["version"] == "1.0.0"
    assert data["packs"][0]["content_hash"] == "sha256:abc123"
    assert data["metadata"]["author"] == "ENKI"


def test_active_set_from_dict():
    """Active set deserializes from dictionary correctly."""
    data = {
        "version": "1.0.0",
        "packs": [
            {"pack_id": "base60", "version": "1.0.0"}
        ]
    }
    
    active_set = ActiveSet.from_dict(data)
    
    assert active_set.version == "1.0.0"
    assert len(active_set.packs) == 1
    assert active_set.packs[0].pack_id == "base60"
    assert active_set.packs[0].version == "1.0.0"


def test_active_set_file_roundtrip(tmp_path):
    """Active set can be saved and loaded from file."""
    file_path = tmp_path / "active_set.json"
    
    original = ActiveSet(
        version="1.0.0",
        packs=[PackDeclaration("base60", "1.0.0")]
    )
    
    original.to_file(file_path)
    loaded = ActiveSet.from_file(file_path)
    
    assert loaded.version == original.version
    assert len(loaded.packs) == len(original.packs)
    assert loaded.packs[0].pack_id == original.packs[0].pack_id


def test_validate_active_set_valid(tmp_path):
    """Valid active set passes schema validation."""
    data = {
        "version": "1.0.0",
        "packs": []
    }
    
    # Should not raise
    validate_active_set(data)


def test_validate_active_set_invalid_missing_version():
    """Active set without version fails validation."""
    data = {
        "packs": []
    }
    
    with pytest.raises(Exception):  # jsonschema.ValidationError
        validate_active_set(data)


def test_validate_active_set_invalid_version_format():
    """Active set with invalid version format fails validation."""
    data = {
        "version": "invalid",
        "packs": []
    }
    
    with pytest.raises(Exception):  # jsonschema.ValidationError
        validate_active_set(data)


def test_get_pack_declaration():
    """Can retrieve declaration for specific pack."""
    active_set = ActiveSet(
        version="1.0.0",
        packs=[
            PackDeclaration("base60", "1.0.0"),
            PackDeclaration("identity", "1.0.0")
        ]
    )
    
    base60_decl = active_set.get_pack_declaration("base60")
    assert base60_decl is not None
    assert base60_decl.pack_id == "base60"
    assert base60_decl.version == "1.0.0"
    
    unknown_decl = active_set.get_pack_declaration("unknown")
    assert unknown_decl is None


def test_deterministic_serialization():
    """Active set serialization is deterministic (sorted keys)."""
    active_set = ActiveSet(
        version="1.0.0",
        packs=[
            PackDeclaration("zebra", "1.0.0"),
            PackDeclaration("alpha", "1.0.0")
        ],
        metadata={"z_field": "last", "a_field": "first"}
    )
    
    # Serialize twice
    import json
    json1 = json.dumps(active_set.to_dict(), sort_keys=True)
    json2 = json.dumps(active_set.to_dict(), sort_keys=True)
    
    # Should be identical
    assert json1 == json2

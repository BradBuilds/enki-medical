"""
ENKI Definition Pack Loader - Test Suite

Tests proving correctness of the pack loader:
- Base-60 pack loads successfully
- Duplicate definition_id fails
- Duplicate name fails (if applicable)
- Invalid schema fails
- Indexes are correctly populated
- Deterministic ordering
"""

import json
import pytest
from pathlib import Path
from core.packs import load_pack, PackLoader
from core.packs import errors as error_codes


# Test fixtures
TEST_DATA_DIR = Path(__file__).parent / "test_data"


class TestBase60Loading:
    """Tests for loading the real Base-60 pack."""

    def test_base60_loads_successfully(self):
        """Base-60 pack should load without errors."""
        # Assumes running from project root
        result = load_pack("libraries/base60")
        
        assert result.ok, f"Base-60 pack failed to load: {result.errors}"
        assert result.pack_id == "base60"
        # Version per pack.json canonical source of truth
        assert result.version["version"] == "0.2.0"
        assert result.definition_count() == 4
        assert len(result.errors) == 0

    def test_base60_has_correct_definitions(self):
        """Base-60 should have system, rules, glyphs, digits."""
        result = load_pack("libraries/base60")
        
        assert result.ok
        
        # Check all expected IDs are present
        expected_ids = {
            "base60.system",
            "base60.rules",
            "base60.glyphs",
            "base60.digits"
        }
        actual_ids = set(result.index.by_id.keys())
        assert actual_ids == expected_ids

    def test_base60_index_by_type(self):
        """Base-60 definitions should be indexed by type."""
        result = load_pack("libraries/base60")
        
        assert result.ok
        assert "system" in result.index.by_type
        assert "rules" in result.index.by_type
        assert "glyphs" in result.index.by_type
        assert "digits" in result.index.by_type
        
        # Each type should have one definition
        assert len(result.index.by_type["system"]) == 1
        assert len(result.index.by_type["rules"]) == 1
        assert len(result.index.by_type["glyphs"]) == 1
        assert len(result.index.by_type["digits"]) == 1

    def test_base60_definitions_have_content(self):
        """All Base-60 definitions should have valid content."""
        result = load_pack("libraries/base60")
        
        assert result.ok
        
        for definition in result.definitions:
            assert definition.id
            assert definition.type
            assert definition.version
            assert definition.content
            assert isinstance(definition.content, dict)
            assert len(definition.content) > 0

    def test_base60_system_definition_content(self):
        """Base-60 system definition should have expected properties."""
        result = load_pack("libraries/base60")
        
        assert result.ok
        
        system_def = result.index.by_id["base60.system"]
        assert system_def.content["base"] == 60
        assert system_def.content["name"] == "Sexagesimal"


class TestPackValidation:
    """Tests for pack validation logic."""

    def test_nonexistent_path_fails(self):
        """Loading a nonexistent path should fail."""
        result = load_pack("libraries/does_not_exist")
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.PACK_PATH_NOT_FOUND for e in result.errors)

    def test_missing_manifest_fails(self, tmp_path):
        """Pack without pack.json should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.PACK_MANIFEST_MISSING for e in result.errors)

    def test_invalid_json_manifest_fails(self, tmp_path):
        """Pack with invalid JSON manifest should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        
        manifest_path = pack_dir / "pack.json"
        manifest_path.write_text("{invalid json", encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.PACK_MANIFEST_INVALID_JSON for e in result.errors)

    def test_empty_pack_fails(self, tmp_path):
        """Pack with no definitions should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        
        manifest = {
            "pack_id": "empty",
            "version": "0.1.0",
            "name": "Empty Pack",
            "description": "A pack with no definitions",
            "definitions": []
        }
        
        manifest_path = pack_dir / "pack.json"
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.PACK_EMPTY for e in result.errors)


class TestDuplicateDetection:
    """Tests for duplicate definition detection."""

    def test_duplicate_id_fails(self, tmp_path):
        """Pack with duplicate definition IDs should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        # Create manifest with duplicate ID
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.def1", "path": "definitions/def1.json", "type": "custom"},
                {"id": "test.def1", "path": "definitions/def2.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        # Create two definitions with same ID
        def1 = {
            "id": "test.def1",
            "type": "custom",
            "version": "0.1.0",
            "description": "First definition",
            "content": {"value": 1}
        }
        
        def2 = {
            "id": "test.def1",
            "type": "custom",
            "version": "0.1.0",
            "description": "Second definition",
            "content": {"value": 2}
        }
        
        (defs_dir / "def1.json").write_text(json.dumps(def1), encoding='utf-8')
        (defs_dir / "def2.json").write_text(json.dumps(def2), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.DUPLICATE_DEFINITION_ID for e in result.errors)


class TestSchemaValidation:
    """Tests for JSON schema validation."""

    def test_missing_required_field_fails(self, tmp_path):
        """Definition missing required field should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.def1", "path": "definitions/def1.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        # Missing "content" field (required)
        def1 = {
            "id": "test.def1",
            "type": "custom",
            "version": "0.1.0"
        }
        
        (defs_dir / "def1.json").write_text(json.dumps(def1), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.DEFINITION_SCHEMA_INVALID for e in result.errors)

    def test_invalid_id_format_fails(self, tmp_path):
        """Definition with invalid ID format should fail."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "INVALID ID!", "path": "definitions/def1.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        # ID with invalid characters
        def1 = {
            "id": "INVALID ID!",
            "type": "custom",
            "version": "0.1.0",
            "content": {}
        }
        
        (defs_dir / "def1.json").write_text(json.dumps(def1), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.has_errors()
        assert any(e.code == error_codes.DEFINITION_SCHEMA_INVALID for e in result.errors)


class TestIndexing:
    """Tests for definition indexing."""

    def test_index_by_id(self, tmp_path):
        """Definitions should be indexed by ID."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.alpha", "path": "definitions/alpha.json", "type": "custom"},
                {"id": "test.beta", "path": "definitions/beta.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        alpha = {
            "id": "test.alpha",
            "type": "custom",
            "version": "0.1.0",
            "content": {"value": "a"}
        }
        
        beta = {
            "id": "test.beta",
            "type": "custom",
            "version": "0.1.0",
            "content": {"value": "b"}
        }
        
        (defs_dir / "alpha.json").write_text(json.dumps(alpha), encoding='utf-8')
        (defs_dir / "beta.json").write_text(json.dumps(beta), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert result.ok
        assert "test.alpha" in result.index.by_id
        assert "test.beta" in result.index.by_id
        assert result.index.by_id["test.alpha"].content["value"] == "a"
        assert result.index.by_id["test.beta"].content["value"] == "b"

    def test_index_by_type(self, tmp_path):
        """Definitions should be indexed by type."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.sys1", "path": "definitions/sys1.json", "type": "system"},
                {"id": "test.sys2", "path": "definitions/sys2.json", "type": "system"},
                {"id": "test.rule1", "path": "definitions/rule1.json", "type": "rules"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        for def_id, def_type in [("test.sys1", "system"), ("test.sys2", "system"), ("test.rule1", "rules")]:
            def_data = {
                "id": def_id,
                "type": def_type,
                "version": "0.1.0",
                "content": {}
            }
            (defs_dir / f"{def_id.split('.')[1]}.json").write_text(json.dumps(def_data), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert result.ok
        assert "system" in result.index.by_type
        assert "rules" in result.index.by_type
        assert len(result.index.by_type["system"]) == 2
        assert len(result.index.by_type["rules"]) == 1


class TestDeterministicBehavior:
    """Tests for deterministic ordering."""

    def test_definitions_sorted_by_id(self, tmp_path):
        """Definitions should be sorted by ID regardless of load order."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        # Intentionally unordered in manifest
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.zulu", "path": "definitions/zulu.json", "type": "custom"},
                {"id": "test.alpha", "path": "definitions/alpha.json", "type": "custom"},
                {"id": "test.mike", "path": "definitions/mike.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        for def_id in ["test.zulu", "test.alpha", "test.mike"]:
            def_data = {
                "id": def_id,
                "type": "custom",
                "version": "0.1.0",
                "content": {}
            }
            filename = def_id.split('.')[1]
            (defs_dir / f"{filename}.json").write_text(json.dumps(def_data), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        assert result.ok
        
        # Definitions should be sorted alphabetically by ID
        ids = [d.id for d in result.definitions]
        assert ids == ["test.alpha", "test.mike", "test.zulu"]


class TestWarnings:
    """Tests for non-fatal warnings."""

    def test_missing_description_warning(self, tmp_path):
        """Definition without description should generate warning."""
        pack_dir = tmp_path / "test_pack"
        pack_dir.mkdir()
        defs_dir = pack_dir / "definitions"
        defs_dir.mkdir()
        
        manifest = {
            "pack_id": "test",
            "version": "0.1.0",
            "name": "Test Pack",
            "description": "Test",
            "definitions": [
                {"id": "test.def1", "path": "definitions/def1.json", "type": "custom"}
            ]
        }
        
        (pack_dir / "pack.json").write_text(json.dumps(manifest), encoding='utf-8')
        
        # No description field
        def1 = {
            "id": "test.def1",
            "type": "custom",
            "version": "0.1.0",
            "content": {}
        }
        
        (defs_dir / "def1.json").write_text(json.dumps(def1), encoding='utf-8')
        
        result = load_pack(str(pack_dir))
        
        # Should load successfully but with warning
        assert result.ok
        assert result.has_warnings()
        assert any(w.code == error_codes.MISSING_DESCRIPTION for w in result.warnings)


class TestPackLoadResult:
    """Tests for PackLoadResult data structure."""

    def test_result_has_correct_metadata(self):
        """PackLoadResult should contain pack metadata."""
        result = load_pack("libraries/base60")
        
        assert result.pack_id == "base60"
        assert "version" in result.version
        assert "name" in result.version
        # Version per pack.json canonical source of truth
        assert result.version["version"] == "0.2.0"
        assert result.version["name"] == "ENKI Base-60 Core"

    def test_failed_result_has_empty_index(self, tmp_path):
        """Failed load should have empty index."""
        pack_dir = tmp_path / "bad_pack"
        pack_dir.mkdir()
        
        result = load_pack(str(pack_dir))
        
        assert not result.ok
        assert result.index.is_empty()
        assert len(result.index.by_id) == 0
        assert len(result.index.by_type) == 0

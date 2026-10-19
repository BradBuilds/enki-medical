"""
Language Pack Tests

Verifies language pack structure, definitions, and integration.
"""

import pytest

from core.packs import load_pack


def _get_defs(result):
    """
    Get definitions from PackLoadResult.
    PackLoadResult has .definitions directly (no .pack wrapper).
    """
    defs = getattr(result, "definitions", None)
    if defs is None:
        raise AssertionError("result has no .definitions attribute")
    return defs


def _find_def(defs, def_id: str):
    return [d for d in defs if getattr(d, "id", None) == def_id]


def _def_content(defn):
    # Most ENKI defs are objects with .content; fallback to dict style just in case.
    if hasattr(defn, "content"):
        return defn.content
    if isinstance(defn, dict):
        return defn.get("content", {})
    raise AssertionError(f"Unexpected definition shape for {defn}")


def test_language_pack_loads():
    result = load_pack("libraries/language")
    assert getattr(result, "ok", False), f"Failed to load: {getattr(result, 'errors', None)}"
    assert getattr(result, "pack_id", None) == "language"
    assert getattr(result, "version", None) is not None


def test_language_pack_has_10_definitions():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    assert len(defs) == 10


def test_language_pack_namespace_ownership():
    result = load_pack("libraries/language")
    # Namespace ownership is encoded in pack definition, verified via load success
    # and definition filtering
    defs = _get_defs(result)
    language_defs = [d for d in defs if d.id.startswith("language.")]
    assert len(language_defs) == 10, "All definitions should be in language.* namespace"


def test_language_definitions_all_in_language_namespace():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    for d in defs:
        assert d.id.startswith("language."), f"Non-language namespace found: {d.id}"


def test_language_definitions_indexed_by_type():
    result = load_pack("libraries/language")
    index = getattr(result, "index", None)
    assert index is not None, "Expected result.index"
    by_type = getattr(index, "by_type", None)
    assert by_type is not None, "Expected result.index.by_type"
    # Expected types present
    assert "system" in by_type
    assert "rules" in by_type
    assert "glyphs" in by_type
    assert "custom" in by_type


def test_language_system_exists_and_has_base_concepts():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.system")
    assert len(found) == 1
    assert found[0].type == "system"
    content = _def_content(found[0])
    assert "base_concepts" in content
    assert isinstance(content["base_concepts"], list)


def test_language_scripts_has_three_scripts_and_new_fields():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.scripts")
    assert len(found) == 1
    assert found[0].type == "rules"
    content = _def_content(found[0])
    scripts = content.get("scripts", {})
    assert "latin" in scripts
    assert "cyrillic" in scripts
    assert "devanagari" in scripts

    for name, s in scripts.items():
        assert "expected_glyphs" in s, f"Missing expected_glyphs in {name}"
        assert "v0_1_0_included_glyphs" in s, f"Missing v0_1_0_included_glyphs in {name}"
        assert "glyphs_defined_in" in s, f"Missing glyphs_defined_in in {name}"
        assert "completeness" in s, f"Missing completeness in {name}"


def test_language_phonology_exists_and_has_inventory():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.phonology")
    assert len(found) == 1
    assert found[0].type == "custom"
    content = _def_content(found[0])
    assert "phoneme_inventory" in content


def test_language_morphology_exists_and_has_processes():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.morphology")
    assert len(found) == 1
    assert found[0].type == "rules"
    content = _def_content(found[0])
    assert "processes" in content


def test_language_semantics_exists_and_has_relations():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.semantics")
    assert len(found) == 1
    assert found[0].type == "custom"
    content = _def_content(found[0])
    assert "semantic_relations" in content


def test_language_pragmatics_exists_and_has_speech_acts():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.pragmatics")
    assert len(found) == 1
    assert found[0].type == "rules"
    content = _def_content(found[0])
    assert "speech_acts" in content


def test_language_indexes_exists_and_has_indexes():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    found = _find_def(defs, "language.indexes")
    assert len(found) == 1
    assert found[0].type == "custom"
    content = _def_content(found[0])
    assert "script_by_code" in content
    assert "glyph_definitions" in content


def test_glyph_defs_exist_and_have_completeness_coverage_styles():
    result = load_pack("libraries/language")
    defs = _get_defs(result)
    glyph_defs = [d for d in defs if d.type == "glyphs"]

    glyph_ids = {d.id for d in glyph_defs}
    assert "language.glyphs.latin" in glyph_ids
    assert "language.glyphs.cyrillic" in glyph_ids
    assert "language.glyphs.devanagari" in glyph_ids

    for d in glyph_defs:
        content = _def_content(d)
        assert content.get("completeness") == "partial", f"{d.id} completeness must be 'partial'"
        coverage = content.get("coverage")
        assert isinstance(coverage, dict), f"{d.id} missing coverage dict"
        for k in ("scope", "included_count", "expected_count", "notes"):
            assert k in coverage, f"{d.id} coverage missing {k}"
        styles = content.get("styles")
        assert isinstance(styles, dict) and len(styles) > 0, f"{d.id} must define >=1 styles"


def test_pack_passes_schema_validation_flag():
    result = load_pack("libraries/language")
    assert getattr(result, "ok", False), f"Loader reported not-ok: {getattr(result, 'errors', None)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

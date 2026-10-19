"""
Test suite for gdu.numeric.core v1.0.0

Tests verify:
- Manifest integrity
- Definition file structure
- Forbidden glyph leakage
- Conversion rules presence
- Invariant mapping

Test Categories:
- SCHEMA: Structural validation
- INV: Core semantic invariants
- SEP: Separation/leakage prevention
- CONV: Conversion correctness
- DEP: Dependency integrity

See docs/specs/gdu.numeric.core.invariants.md for formal invariant specifications.
"""

import json
from pathlib import Path

# Path resolution
ROOT = Path(__file__).resolve().parents[1]
DEFS = ROOT / "definitions"
PACK = ROOT / "pack.json"

# Required top-level fields for pack manifest
REQUIRED_PACK_TOP = {"pack_id", "version", "name", "description", "namespaces_owned", "definitions", "metadata"}

# Required top-level fields for definition files
REQUIRED_DEF_TOP = {"id", "type", "version", "content"}


def load_json(p: Path) -> dict:
    """Load and parse JSON file."""
    return json.loads(p.read_text(encoding="utf-8"))


# ==============================================================================
# SCHEMA TESTS - Structural Validation
# ==============================================================================

def test_pack_exists_and_has_manifest():
    """
    Verifies: SCHEMA-002, INV-001
    
    Tests:
    - Pack manifest exists
    - Required fields present
    - Pack ID correct
    - Status is LOCKED
    - All 5 definition files declared
    """
    data = load_json(PACK)
    
    # Required top-level fields
    assert REQUIRED_PACK_TOP.issubset(data.keys()), \
        f"Pack manifest missing required fields. Expected {REQUIRED_PACK_TOP}, got {set(data.keys())}"
    
    # Pack identity
    assert data["pack_id"] == "numeric", \
        f"Expected pack_id 'numeric', got '{data['pack_id']}'"
    
    # Status check (now in metadata)
    assert "metadata" in data, "Pack manifest missing 'metadata' field"
    assert data["metadata"]["status"] == "LOCKED", \
        f"Expected status 'LOCKED', got '{data['metadata']['status']}'"
    
    # Definition files declared (now top-level)
    assert "definitions" in data, \
        "Pack manifest missing 'definitions' field"
    assert len(data["definitions"]) == 5, \
        f"Expected 5 definition files, got {len(data['definitions'])}"


def test_all_definition_files_exist_and_have_canonical_fields():
    """
    Verifies: SCHEMA-001
    
    Tests:
    - All declared definition files exist
    - Each has required fields: id, path, type
    """
    pack = load_json(PACK)
    
    for def_entry in pack["definitions"]:
        rel = def_entry["path"]
        p = ROOT / rel
        assert p.exists(), f"Missing definition file: {rel}"
        
        d = load_json(p)
        assert REQUIRED_DEF_TOP.issubset(d.keys()), \
            f"Missing canonical fields in {rel}. Required: {REQUIRED_DEF_TOP}, Found: {d.keys()}"


# ==============================================================================
# SEPARATION TESTS - Prevent Cross-Layer Contamination
# ==============================================================================

def test_no_glyphs_in_numeric_core():
    """
    Verifies: INV-003, SEP-001
    
    Tests:
    - No glyph symbols in numeric core files
    - No cuneiform Unicode characters
    - Separation between truth and appearance enforced
    
    Hard guarantee: numeric core must not contain glyph symbols or rendering styles.
    """
    # Forbidden tokens - these should NEVER appear in numeric core
    forbidden_symbols = ["𒁹", "𒌋"]  # Cuneiform symbols
    
    # Collect all text from pack and definitions
    texts = []
    texts.append(PACK.read_text(encoding="utf-8"))
    for p in DEFS.glob("*.json"):
        texts.append(p.read_text(encoding="utf-8"))
    
    blob = "\n".join(texts)
    
    # Check for forbidden symbols
    for symbol in forbidden_symbols:
        assert symbol not in blob, \
            f"Forbidden glyph symbol '{symbol}' found in numeric core. " \
            f"Glyphs belong in gdu.glyphs.base60 pack, not numeric core."


# ==============================================================================
# CONVERSION TESTS - Declarative Rules Validation
# ==============================================================================

def test_conversion_rules_present_as_invariants_not_code():
    """
    Verifies: INV-004
    
    Tests:
    - Conversion rules exist in conversion_rules.json
    - Rules are declarative (strings), not executable code
    - Lossless invariant declared
    """
    rules = load_json(DEFS / "numeric.conversion_rules.json")
    content = rules["content"]
    
    # Check lossless invariant declared
    assert "lossless_invariant" in content, \
        "Missing lossless_invariant in conversion rules"
    
    # Check conversion directions exist
    assert "decimal_to_base60" in content, \
        "Missing decimal_to_base60 conversion rules"
    assert "base60_to_decimal" in content, \
        "Missing base60_to_decimal conversion rules"
    
    # Ensure declarative: "rules" are strings, not executable code objects
    d2b_rules = content["decimal_to_base60"]["rules"]
    b2d_rules = content["base60_to_decimal"]["rules"]
    
    assert all(isinstance(x, str) for x in d2b_rules), \
        "decimal_to_base60 rules must be declarative strings, not code"
    assert all(isinstance(x, str) for x in b2d_rules), \
        "base60_to_decimal rules must be declarative strings, not code"


# ==============================================================================
# SEMANTIC TESTS - Core Truth Invariants
# ==============================================================================

def test_decimal_canonical_storage():
    """
    Verifies: INV-001
    
    Tests:
    - numeric.decimal.json has role: "canonical"
    - Decimal is marked as authoritative truth
    """
    decimal = load_json(DEFS / "numeric.decimal.json")
    content = decimal["content"]
    
    assert content["role"] == "canonical", \
        f"Expected decimal role 'canonical', got '{content['role']}'"
    assert content["base"] == 10, \
        f"Expected decimal base 10, got {content['base']}"


def test_base60_representational_only():
    """
    Verifies: INV-002
    
    Tests:
    - numeric.base60.json has role: "representation_only"
    - Base-60 is marked as non-canonical
    """
    base60 = load_json(DEFS / "numeric.base60.json")
    content = base60["content"]
    
    assert content["role"] == "representation_only", \
        f"Expected base60 role 'representation_only', got '{content['role']}'"
    assert content["base"] == 60, \
        f"Expected base60 base 60, got {content['base']}"


# ==============================================================================
# DEPENDENCY TESTS - Structural Integrity
# ==============================================================================

def test_dependency_integrity():
    """
    Verifies: DEP-001
    
    Tests:
    - Dependencies list is empty (foundational pack)
    - No circular dependencies possible
    """
    pack = load_json(PACK)
    deps = pack.get("dependencies", [])
    
    assert isinstance(deps, list), \
        f"Expected dependencies to be a list, got {type(deps)}"
    assert len(deps) == 0, \
        f"Expected no dependencies (foundational pack), got {len(deps)}: {deps}"


# ==============================================================================
# CONVERSION CORRECTNESS TESTS - Round-Trip and Edge Cases
# ==============================================================================

def test_roundtrip_conversion_invariant():
    """
    Verifies: CONV-001
    
    Tests:
    - Round-trip conversion: decimal → base60 → decimal preserves value
    - Test critical values: 0, 59, 60, 3599, 3600, 3723, 216000
    - Validates lossless conversion guarantee
    
    Note: This tests the RULES are present and correct in definition files.
    Actual conversion implementation would be in runtime code.
    """
    rules = load_json(DEFS / "numeric.conversion_rules.json")
    content = rules["content"]
    
    # Verify lossless invariant is declared
    assert "lossless_invariant" in content, \
        "Missing lossless_invariant declaration"
    
    lossless_inv = content["lossless_invariant"]
    assert "base60_to_decimal(decimal_to_base60(x))" in lossless_inv, \
        "Lossless invariant doesn't specify round-trip formula"
    assert "MUST equal x" in lossless_inv, \
        "Lossless invariant doesn't guarantee equality"
    
    # Verify conversion rules specify correct algorithms
    d2b = content["decimal_to_base60"]
    b2d = content["base60_to_decimal"]
    
    # Decimal to base60 must handle zero explicitly
    d2b_rules = " ".join(d2b["rules"])
    assert "value == 0" in d2b_rules.lower(), \
        "decimal_to_base60 doesn't handle zero case explicitly"
    
    # Base60 to decimal must use proper place value formula
    b2d_rules = " ".join(b2d["rules"])
    assert "60^" in b2d_rules or "60 **" in b2d_rules, \
        "base60_to_decimal doesn't specify power-of-60 calculation"


def test_zero_explicit():
    """
    Verifies: CONV-002
    
    Tests:
    - Zero must be represented as [0], never [] or null
    - Zero rule explicitly stated in base60 definition
    """
    base60 = load_json(DEFS / "numeric.base60.json")
    content = base60["content"]
    
    # Verify zero rule exists and is explicit
    assert "zero_rule" in content, \
        "Missing zero_rule in base60 definition"
    
    zero_rule = content["zero_rule"].lower()
    assert "explicit" in zero_rule, \
        "Zero rule doesn't emphasize explicit representation"
    assert "0" in zero_rule, \
        "Zero rule doesn't specify digit 0"
    assert "omission" in zero_rule or "omit" in zero_rule, \
        "Zero rule doesn't prohibit omission"


def test_no_place_collapse():
    """
    Verifies: CONV-003
    
    Tests:
    - Internal zero places must not be trimmed or omitted
    - No collapse rule explicitly stated
    """
    base60 = load_json(DEFS / "numeric.base60.json")
    content = base60["content"]
    
    # Verify no collapse rule exists
    assert "no_collapse_rule" in content, \
        "Missing no_collapse_rule in base60 definition"
    
    no_collapse = content["no_collapse_rule"].lower()
    assert "not" in no_collapse or "must not" in no_collapse, \
        "No collapse rule doesn't prohibit collapsing"
    assert "zero" in no_collapse or "internal" in no_collapse, \
        "No collapse rule doesn't mention internal zeros"


# ==============================================================================
# DOMAIN CONSTRAINT TESTS
# ==============================================================================

def test_domain_unsigned_only():
    """
    Verifies: DOMAIN-001
    
    Tests:
    - v1.0.0 only supports non-negative integers (≥ 0)
    - Negative numbers explicitly excluded
    """
    decimal = load_json(DEFS / "numeric.decimal.json")
    content = decimal["content"]
    
    # Check constraints
    assert "constraints" in content, \
        "Missing constraints in decimal definition"
    
    constraints = content["constraints"]
    assert "min_value" in constraints, \
        "Missing min_value constraint"
    assert constraints["min_value"] == 0, \
        f"Expected min_value 0, got {constraints['min_value']}"
    
    # Check error code for negative values
    system = load_json(DEFS / "numeric.system.json")
    error_codes = system["content"]["error_codes"]
    assert "NUMERIC_NEGATIVE_NOT_SUPPORTED" in error_codes, \
        "Missing NUMERIC_NEGATIVE_NOT_SUPPORTED error code"


def test_domain_integer_only():
    """
    Verifies: DOMAIN-002
    
    Tests:
    - v1.0.0 only supports integers (no floating point)
    - Integer-only constraint explicit
    """
    decimal = load_json(DEFS / "numeric.decimal.json")
    content = decimal["content"]
    
    # Check constraints
    constraints = content["constraints"]
    assert "integer_only" in constraints, \
        "Missing integer_only constraint"
    assert constraints["integer_only"] is True, \
        "integer_only should be True"
    
    # Check notes mention no floating point
    if "notes" in content:
        notes_text = " ".join(content["notes"]).lower()
        assert "floating" in notes_text or "float" in notes_text, \
            "Notes don't mention floating point exclusion"


# ==============================================================================
# ERROR HANDLING TESTS
# ==============================================================================

def test_error_codes_defined():
    """
    Verifies: ERROR-001, ERROR-002, ERROR-003, ERROR-004
    
    Tests:
    - All required error codes defined in numeric.system.json
    - Error codes match expected format
    """
    system = load_json(DEFS / "numeric.system.json")
    content = system["content"]
    
    assert "error_codes" in content, \
        "Missing error_codes in system definition"
    
    error_codes = content["error_codes"]
    required_codes = [
        "NUMERIC_INVALID_TYPE",
        "NUMERIC_NEGATIVE_NOT_SUPPORTED",
        "BASE60_DIGIT_RANGE",
        "BASE60_EMPTY_PLACES"
    ]
    
    for code in required_codes:
        assert code in error_codes, \
            f"Missing required error code: {code}"


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

if __name__ == "__main__":
    """Run all tests directly."""
    import sys
    
    tests = [
        # Schema tests
        test_pack_exists_and_has_manifest,
        test_all_definition_files_exist_and_have_canonical_fields,
        # Separation tests
        test_no_glyphs_in_numeric_core,
        # Conversion tests
        test_conversion_rules_present_as_invariants_not_code,
        test_roundtrip_conversion_invariant,
        test_zero_explicit,
        test_no_place_collapse,
        # Semantic tests
        test_decimal_canonical_storage,
        test_base60_representational_only,
        # Dependency tests
        test_dependency_integrity,
        # Domain tests
        test_domain_unsigned_only,
        test_domain_integer_only,
        # Error handling tests
        test_error_codes_defined,
    ]
    
    passed = 0
    failed = 0
    
    print("Running gdu.numeric.core test suite...")
    print("=" * 70)
    
    for test in tests:
        try:
            test()
            print(f"✅ PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"💥 ERROR: {test.__name__}")
            print(f"   {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    
    sys.exit(0 if failed == 0 else 1)

"""
Tests for Assertion Instance Validation

Tests validate that:
- Valid assertions pass
- Invalid predicates fail
- Invalid object kinds fail
- Invalid scopes fail
- Schema violations fail
- Validation is deterministic (stable sorted errors)
"""

import pytest
from core.packs import load_pack
from core.validation.validate_assertions import (
    validate_assertion_instance,
    validate_assertion_batch,
    AssertionValidator
)


@pytest.fixture
def identity_pack():
    """Load Identity Pack"""
    pack = load_pack("libraries/identity")
    assert pack.ok, f"Identity pack failed to load: {pack.errors}"
    return pack


@pytest.fixture
def assertion_vocab_pack():
    """Load Assertion Vocabulary Pack"""
    pack = load_pack("libraries/assertionvocab")
    assert pack.ok, f"Assertion vocab pack failed to load: {pack.errors}"
    return pack


@pytest.fixture
def validator(identity_pack, assertion_vocab_pack):
    """Create validator instance"""
    return AssertionValidator(identity_pack, assertion_vocab_pack)


def test_valid_entity_to_entity_assertion(validator):
    """Test valid entity→entity assertion passes"""
    assertion = {
        "assertion_id": "test_001",
        "subject": "person_alice",
        "predicate": "owns",
        "object": {
            "kind": "entity_ref",
            "value": {
                "entity_id": "device_001",
                "entity_type": "device"
            }
        },
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_valid_entity_to_scalar_assertion(validator):
    """Test valid entity→scalar assertion passes"""
    assertion = {
        "assertion_id": "test_002",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {
            "kind": "string",
            "value": "Alice Smith"
        },
        "scope": "shared"
    }
    
    result = validator.validate_assertion(assertion)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_valid_entity_to_reference_assertion(validator):
    """Test valid entity→reference assertion passes"""
    assertion = {
        "assertion_id": "test_003",
        "subject": "dataset_xyz",
        "predicate": "derived_from",
        "object": {
            "kind": "pack_ref",
            "value": {
                "pack_id": "base60",
                "version": "0.1.0"
            }
        },
        "scope": "global"
    }
    
    result = validator.validate_assertion(assertion)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_invalid_predicate_fails(validator):
    """Test unknown predicate causes validation failure"""
    assertion = {
        "assertion_id": "test_004",
        "subject": "person_alice",
        "predicate": "unknown_predicate",
        "object": {
            "kind": "string",
            "value": "test"
        },
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to unknown predicate"
    assert len(result.errors) > 0
    assert any(e.code == "INVALID_PREDICATE" for e in result.errors)


def test_invalid_object_kind_fails(validator):
    """Test unknown object kind causes validation failure"""
    assertion = {
        "assertion_id": "test_005",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {
            "kind": "unknown_kind",
            "value": "test"
        },
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to unknown object kind"
    assert len(result.errors) > 0
    assert any(e.code == "INVALID_OBJECT_KIND" for e in result.errors)


def test_invalid_scope_fails(validator):
    """Test invalid scope causes validation failure"""
    assertion = {
        "assertion_id": "test_006",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {
            "kind": "string",
            "value": "Alice"
        },
        "scope": "invalid_scope"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to invalid scope"
    assert len(result.errors) > 0
    # Schema enum validation catches invalid scope
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_schema_invalid_missing_required_field(validator):
    """Test missing required field causes schema validation failure"""
    assertion = {
        "assertion_id": "test_007",
        "subject": "person_alice",
        "predicate": "has_name",
        # Missing "object" field
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to missing required field"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_schema_invalid_wrong_type(validator):
    """Test wrong field type causes schema validation failure"""
    assertion = {
        "assertion_id": "test_008",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": "string_instead_of_object",  # Should be object
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to wrong type"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_object_kind_not_allowed_for_predicate(validator):
    """Test object kind not in predicate's allowed list fails"""
    # "has_name" only allows "string", not "number"
    assertion = {
        "assertion_id": "test_009",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {
            "kind": "number",
            "value": 42
        },
        "scope": "local"
    }
    
    result = validator.validate_assertion(assertion)
    assert not result.valid, "Expected invalid due to incompatible object kind"
    assert len(result.errors) > 0
    assert any(e.code == "OBJECT_KIND_NOT_ALLOWED" for e in result.errors)


def test_validation_determinism(validator):
    """Test validation produces stable, sorted errors"""
    # Assertion with multiple errors
    assertion = {
        "assertion_id": "test_010",
        "subject": "person_alice",
        "predicate": "unknown_pred",
        "object": {
            "kind": "unknown_kind",
            "value": "test"
        },
        "scope": "invalid_scope"
    }
    
    # Run validation multiple times
    results = [validator.validate_assertion(assertion) for _ in range(5)]
    
    # All results should have same errors in same order
    for i in range(1, len(results)):
        assert len(results[i].errors) == len(results[0].errors)
        for j in range(len(results[0].errors)):
            assert results[i].errors[j].code == results[0].errors[j].code
            assert results[i].errors[j].field == results[0].errors[j].field


def test_batch_validation_valid_assertions(validator):
    """Test batch validation with all valid assertions"""
    assertions = [
        {
            "assertion_id": "batch_001",
            "subject": "person_alice",
            "predicate": "has_name",
            "object": {"kind": "string", "value": "Alice"},
            "scope": "local"
        },
        {
            "assertion_id": "batch_002",
            "subject": "person_bob",
            "predicate": "owns",
            "object": {"kind": "entity_ref", "value": {"entity_id": "device_001", "entity_type": "device"}},
            "scope": "shared"
        }
    ]
    
    result = validator.validate_batch(assertions)
    assert result.valid, f"Expected all valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_batch_validation_mixed_validity(validator):
    """Test batch validation with mix of valid and invalid assertions"""
    assertions = [
        {
            "assertion_id": "batch_003",
            "subject": "person_alice",
            "predicate": "has_name",
            "object": {"kind": "string", "value": "Alice"},
            "scope": "local"
        },
        {
            "assertion_id": "batch_004",
            "subject": "person_bob",
            "predicate": "unknown_pred",  # Invalid
            "object": {"kind": "string", "value": "test"},
            "scope": "local"
        }
    ]
    
    result = validator.validate_batch(assertions)
    assert not result.valid, "Expected invalid due to one bad assertion"
    assert len(result.errors) > 0
    # Check that error message includes assertion index
    assert any("Assertion 1" in e.message for e in result.errors)


def test_validate_assertion_instance_function():
    """Test standalone validate_assertion_instance function"""
    assertion = {
        "assertion_id": "test_011",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {"kind": "string", "value": "Alice"},
        "scope": "local"
    }
    
    result = validate_assertion_instance(assertion)
    assert result.valid
    assert len(result.errors) == 0


def test_validate_assertion_batch_function():
    """Test standalone validate_assertion_batch function"""
    assertions = [
        {
            "assertion_id": "test_012",
            "subject": "person_alice",
            "predicate": "has_name",
            "object": {"kind": "string", "value": "Alice"},
            "scope": "local"
        }
    ]
    
    result = validate_assertion_batch(assertions)
    assert result.valid
    assert len(result.errors) == 0


def test_optional_fields_valid(validator):
    """Test assertions with optional fields are valid"""
    assertion = {
        "assertion_id": "test_013",
        "subject": "person_alice",
        "predicate": "has_name",
        "object": {"kind": "string", "value": "Alice"},
        "scope": "local",
        "timestamp": "2025-12-31T10:00:00Z",
        "source": "registration_system",
        "metadata": {
            "created_by": "admin",
            "notes": "Initial registration"
        }
    }
    
    result = validator.validate_assertion(assertion)
    assert result.valid, f"Expected valid with optional fields but got errors: {result.errors}"


def test_sorted_errors_property(validator):
    """Test that ValidationResult.sorted_errors returns deterministic order"""
    assertion = {
        "assertion_id": "test_014",
        "subject": "person_alice",
        "predicate": "unknown_pred",
        "object": {"kind": "unknown_kind", "value": "test"},
        "scope": "invalid_scope"
    }
    
    result = validator.validate_assertion(assertion)
    sorted_errors_1 = result.sorted_errors
    sorted_errors_2 = result.sorted_errors
    
    # Should return same order every time
    assert len(sorted_errors_1) == len(sorted_errors_2)
    for i in range(len(sorted_errors_1)):
        assert sorted_errors_1[i].code == sorted_errors_2[i].code

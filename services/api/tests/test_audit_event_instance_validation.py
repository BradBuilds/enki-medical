"""
Tests for Audit Event Instance Validation

Tests validate that:
- Valid audit events pass
- Invalid event types fail
- Invalid severity fails
- Invalid scope fails
- Schema violations fail
- Validation is deterministic (stable sorted errors)
"""

import pytest
from core.packs import load_pack
from core.validation.validate_audit_events import (
    validate_audit_event_instance,
    validate_audit_event_batch,
    AuditEventValidator
)


@pytest.fixture
def audit_vocab_pack():
    """Load Audit Vocabulary Pack"""
    pack = load_pack("libraries/auditvocab")
    assert pack.ok, f"Audit vocab pack failed to load: {pack.errors}"
    return pack


@pytest.fixture
def identity_pack():
    """Load Identity Pack"""
    pack = load_pack("libraries/identity")
    assert pack.ok, f"Identity pack failed to load: {pack.errors}"
    return pack


@pytest.fixture
def validator(audit_vocab_pack, identity_pack):
    """Create validator instance"""
    return AuditEventValidator(audit_vocab_pack, identity_pack)


def test_valid_assertion_proposed_event(validator):
    """Test valid assertion.proposed event passes"""
    event = {
        "event_id": "evt_001",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "info",
        "scope": "local",
        "actor_id": "person_alice",
        "assertion_id": "assert_001"
    }
    
    result = validator.validate_event(event)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_valid_pack_loaded_event(validator):
    """Test valid pack.loaded event passes"""
    event = {
        "event_id": "evt_002",
        "event_type": "pack.loaded",
        "timestamp": "2025-12-31T09:00:00Z",
        "severity": "info",
        "scope": "local",
        "pack_id": "identity",
        "node_id": "node_primary"
    }
    
    result = validator.validate_event(event)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_valid_node_started_event(validator):
    """Test valid node.started event passes"""
    event = {
        "event_id": "evt_003",
        "event_type": "node.started",
        "timestamp": "2025-12-31T08:00:00Z",
        "severity": "info",
        "scope": "local",
        "node_id": "node_primary"
    }
    
    result = validator.validate_event(event)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_valid_usage_meter_tick_event(validator):
    """Test valid usage.meter_tick event passes"""
    event = {
        "event_id": "evt_004",
        "event_type": "usage.meter_tick",
        "timestamp": "2025-12-31T13:00:00Z",
        "severity": "info",
        "scope": "local",
        "node_id": "node_primary",
        "metadata": {
            "period": "hourly",
            "metrics": {
                "assertions_validated": 14
            }
        }
    }
    
    result = validator.validate_event(event)
    assert result.valid, f"Expected valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_invalid_event_type_fails(validator):
    """Test unknown event type causes validation failure"""
    event = {
        "event_id": "evt_005",
        "event_type": "unknown.event_type",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "info",
        "scope": "local"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to unknown event type"
    assert len(result.errors) > 0
    assert any(e.code == "INVALID_EVENT_TYPE" for e in result.errors)


def test_invalid_severity_fails(validator):
    """Test invalid severity (not in schema enum) causes schema validation failure"""
    event = {
        "event_id": "evt_006",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "invalid_severity",
        "scope": "local"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to invalid severity"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_invalid_scope_fails(validator):
    """Test invalid scope (not in schema enum) causes schema validation failure"""
    event = {
        "event_id": "evt_007",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "info",
        "scope": "invalid_scope"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to invalid scope"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_schema_invalid_missing_required_field(validator):
    """Test missing required field causes schema validation failure"""
    event = {
        "event_id": "evt_008",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        # Missing "severity" and "scope"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to missing required fields"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_schema_invalid_wrong_type(validator):
    """Test wrong field type causes schema validation failure"""
    event = {
        "event_id": "evt_009",
        "event_type": "assertion.proposed",
        "timestamp": 12345,  # Should be string, not number
        "severity": "info",
        "scope": "local"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to wrong type"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_schema_invalid_additional_properties(validator):
    """Test additional properties not allowed"""
    event = {
        "event_id": "evt_010",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "info",
        "scope": "local",
        "unknown_field": "should_not_be_here"
    }
    
    result = validator.validate_event(event)
    assert not result.valid, "Expected invalid due to additional properties"
    assert len(result.errors) > 0
    assert any(e.code == "SCHEMA_ERROR" for e in result.errors)


def test_validation_determinism(validator):
    """Test validation produces stable, sorted errors"""
    # Event with multiple errors
    event = {
        "event_id": "evt_011",
        "event_type": "unknown_event",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "invalid_severity",
        "scope": "local"
    }
    
    # Run validation multiple times
    results = [validator.validate_event(event) for _ in range(5)]
    
    # All results should have same errors in same order
    for i in range(1, len(results)):
        assert len(results[i].errors) == len(results[0].errors)
        for j in range(len(results[0].errors)):
            assert results[i].errors[j].code == results[0].errors[j].code
            assert results[i].errors[j].field == results[0].errors[j].field


def test_batch_validation_valid_events(validator):
    """Test batch validation with all valid events"""
    events = [
        {
            "event_id": "evt_012",
            "event_type": "assertion.proposed",
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": "info",
            "scope": "local"
        },
        {
            "event_id": "evt_013",
            "event_type": "pack.loaded",
            "timestamp": "2025-12-31T09:00:00Z",
            "severity": "info",
            "scope": "local",
            "pack_id": "identity"
        }
    ]
    
    result = validator.validate_batch(events)
    assert result.valid, f"Expected all valid but got errors: {result.errors}"
    assert len(result.errors) == 0


def test_batch_validation_mixed_validity(validator):
    """Test batch validation with mix of valid and invalid events"""
    events = [
        {
            "event_id": "evt_014",
            "event_type": "assertion.proposed",
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": "info",
            "scope": "local"
        },
        {
            "event_id": "evt_015",
            "event_type": "unknown_event",  # Invalid
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": "info",
            "scope": "local"
        }
    ]
    
    result = validator.validate_batch(events)
    assert not result.valid, "Expected invalid due to one bad event"
    assert len(result.errors) > 0
    # Check that error message includes event index
    assert any("Event 1" in e.message for e in result.errors)


def test_validate_audit_event_instance_function():
    """Test standalone validate_audit_event_instance function"""
    event = {
        "event_id": "evt_016",
        "event_type": "assertion.proposed",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "info",
        "scope": "local"
    }
    
    result = validate_audit_event_instance(event)
    assert result.valid
    assert len(result.errors) == 0


def test_validate_audit_event_batch_function():
    """Test standalone validate_audit_event_batch function"""
    events = [
        {
            "event_id": "evt_017",
            "event_type": "assertion.proposed",
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": "info",
            "scope": "local"
        }
    ]
    
    result = validate_audit_event_batch(events)
    assert result.valid
    assert len(result.errors) == 0


def test_optional_fields_valid(validator):
    """Test events with optional fields are valid"""
    event = {
        "event_id": "evt_018",
        "event_type": "assertion.rejected",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "error",
        "scope": "local",
        "assertion_id": "assert_bad",
        "actor_id": "service_validator",
        "reason": "Invalid predicate",
        "errors": [
            {"code": "INVALID_PREDICATE", "message": "Predicate not found"}
        ],
        "source": "validator_service",
        "metadata": {
            "validation_duration_ms": 5
        }
    }
    
    result = validator.validate_event(event)
    assert result.valid, f"Expected valid with optional fields but got errors: {result.errors}"


def test_sorted_errors_property(validator):
    """Test that ValidationResult.sorted_errors returns deterministic order"""
    event = {
        "event_id": "evt_019",
        "event_type": "unknown_event",
        "timestamp": "2025-12-31T10:00:00Z",
        "severity": "invalid_severity",
        "scope": "local"
    }
    
    result = validator.validate_event(event)
    sorted_errors_1 = result.sorted_errors
    sorted_errors_2 = result.sorted_errors
    
    # Should return same order every time
    assert len(sorted_errors_1) == len(sorted_errors_2)
    for i in range(len(sorted_errors_1)):
        assert sorted_errors_1[i].code == sorted_errors_2[i].code


def test_all_severity_levels_valid(validator):
    """Test all severity levels from vocabulary are valid"""
    severities = ["info", "warning", "error", "critical"]
    
    for severity in severities:
        event = {
            "event_id": f"evt_sev_{severity}",
            "event_type": "assertion.proposed",
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": severity,
            "scope": "local"
        }
        
        result = validator.validate_event(event)
        assert result.valid, f"Severity '{severity}' should be valid"


def test_all_scopes_valid(validator):
    """Test all scope levels from vocabulary are valid"""
    scopes = ["local", "shared", "global"]
    
    for scope in scopes:
        event = {
            "event_id": f"evt_scope_{scope}",
            "event_type": "assertion.proposed",
            "timestamp": "2025-12-31T10:00:00Z",
            "severity": "info",
            "scope": scope
        }
        
        result = validator.validate_event(event)
        assert result.valid, f"Scope '{scope}' should be valid"

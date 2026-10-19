"""
Tests for Event Emission Module

Lock readiness tests verifying:
1. ObservabilityEvent contract - required fields, types, structure
2. Event emitter invariants - sequence, uniqueness, JSONL format, disabling

Note: These test ObservabilityEvent (Phase 2 observability) NOT AuditEvent.
Schema conformance to audit_event_instance.schema.json is deferred to Phase 3.
"""

import pytest
import json
import re
import io
from pathlib import Path

from core.events import emit_event, EventEmitter, EventTypes, Severity, Scope, _get_default_emitter
from core.validation.validate_assertions import validate_assertion_instance
from core.validation.validate_audit_events import validate_audit_event_instance
from core.packs import load_pack


@pytest.fixture
def reset_emitter():
    """Reset emitter state between tests"""
    import core.events
    core.events._default_emitter = None
    yield
    core.events._default_emitter = None


@pytest.fixture
def identity_pack():
    """Load Identity Pack"""
    pack = load_pack("libraries/identity")
    assert pack.ok
    return pack


@pytest.fixture
def assertion_vocab_pack():
    """Load Assertion Vocabulary Pack"""
    pack = load_pack("libraries/assertionvocab")
    assert pack.ok
    return pack


@pytest.fixture
def audit_vocab_pack():
    """Load Audit Vocabulary Pack"""
    pack = load_pack("libraries/auditvocab")
    assert pack.ok
    return pack


class TestObservabilityEventContract:
    """Verify emitted events conform to ObservabilityEvent contract"""
    
    def test_required_fields_present(self, capsys, reset_emitter):
        """Test that all MUST fields are present in emitted event"""
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            actor_id="test_actor",
            metadata={"test": "data"}
        )
        
        captured = capsys.readouterr()
        assert captured.out.strip(), "No output captured"
        event = json.loads(captured.out.strip())
        
        # MUST fields
        assert "event_id" in event, "Missing required field: event_id"
        assert "event_type" in event, "Missing required field: event_type"
        assert "timestamp" in event, "Missing required field: timestamp"
        assert "sequence" in event, "Missing required field: sequence"
        assert "severity" in event, "Missing required field: severity"
        assert "scope" in event, "Missing required field: scope"
        assert "metadata" in event, "Missing required field: metadata"
    
    def test_field_types_correct(self, capsys, reset_emitter):
        """Test that field types match ObservabilityEvent contract"""
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            actor_id="test_actor",
            metadata={"key": "value"}
        )
        
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        
        # Type checks
        assert isinstance(event["event_id"], str), "event_id must be string"
        assert isinstance(event["event_type"], str), "event_type must be string"
        assert isinstance(event["timestamp"], str), "timestamp must be string"
        assert isinstance(event["sequence"], int), "sequence must be integer"
        assert isinstance(event["severity"], str), "severity must be string"
        assert isinstance(event["scope"], str), "scope must be string"
        assert event["metadata"] is None or isinstance(event["metadata"], dict), "metadata must be object or null"
        
        # SHOULD field types
        if "actor_id" in event:
            assert isinstance(event["actor_id"], str), "actor_id must be string"
    
    def test_sequence_field_explicit_and_monotonic(self, capsys, reset_emitter):
        """Test that sequence field exists and increases monotonically"""
        sequences = []
        for i in range(3):
            emit_event(
                event_type=EventTypes.VALIDATION_STARTED,
                severity=Severity.INFO,
                scope=Scope.LOCAL,
                actor_id="test"
            )
            captured = capsys.readouterr()
            event = json.loads(captured.out.strip())
            assert "sequence" in event, f"Event {i} missing sequence field"
            assert isinstance(event["sequence"], int), f"Event {i} sequence not integer"
            sequences.append(event["sequence"])
        
        # Verify monotonically increasing
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i-1], f"Sequence not increasing: {sequences}"
    
    def test_metadata_field_structure(self, capsys, reset_emitter):
        """Test that metadata is dict or null, not other types"""
        # Test with dict metadata
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            metadata={"key": "value", "nested": {"data": 123}}
        )
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        assert isinstance(event["metadata"], dict)
        
        # Test with null metadata
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            metadata=None
        )
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        assert event["metadata"] is None


class TestNullabilityRules:
    """Verify nullability rules for ObservabilityEvent contract"""
    
    def test_null_event_id_rejected(self, reset_emitter):
        """Test that null event_id is rejected"""
        from core.events import ObservabilityEvent, EventEmitter
        emitter = EventEmitter()
        event = ObservabilityEvent(
            event_id=None,  # NULL MUST field
            event_type="test.event",
            timestamp="2025-12-31T12:00:00.000000+00:00",
            sequence=1,
            severity="info",
            scope="local",
            metadata={}
        )
        with pytest.raises(ValueError, match="event_id.*cannot be null"):
            emitter.emit(event)
    
    def test_null_event_type_rejected(self, reset_emitter):
        """Test that null event_type is rejected"""
        from core.events import ObservabilityEvent, EventEmitter
        emitter = EventEmitter()
        event = ObservabilityEvent(
            event_id="event_1_123",
            event_type=None,  # NULL MUST field
            timestamp="2025-12-31T12:00:00.000000+00:00",
            sequence=1,
            severity="info",
            scope="local",
            metadata={}
        )
        with pytest.raises(ValueError, match="event_type.*cannot be null"):
            emitter.emit(event)
    
    def test_null_severity_rejected(self, reset_emitter):
        """Test that null severity is rejected"""
        from core.events import ObservabilityEvent, EventEmitter
        emitter = EventEmitter()
        event = ObservabilityEvent(
            event_id="event_1_123",
            event_type="test.event",
            timestamp="2025-12-31T12:00:00.000000+00:00",
            sequence=1,
            severity=None,  # NULL MUST field
            scope="local",
            metadata={}
        )
        with pytest.raises(ValueError, match="severity.*cannot be null"):
            emitter.emit(event)
    
    def test_null_metadata_accepted(self, capsys, reset_emitter):
        """Test that null metadata is accepted (metadata MAY be null)"""
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            metadata=None
        )
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        assert event["metadata"] is None  # Should NOT raise
    
    def test_empty_metadata_accepted(self, capsys, reset_emitter):
        """Test that empty dict metadata is accepted"""
        emit_event(
            event_type=EventTypes.VALIDATION_STARTED,
            severity=Severity.INFO,
            scope=Scope.LOCAL,
            metadata={}
        )
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        assert event["metadata"] == {}


class TestEventEmitterInvariants:
    """Verify event emitter maintains critical invariants"""
    
    def test_sequence_strictly_increasing(self, capsys, reset_emitter):
        """Test that sequence numbers strictly increase"""
        sequences = []
        for i in range(5):
            emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=Scope.LOCAL, actor_id="test")
            captured = capsys.readouterr()
            assert captured.out.strip(), f"No output for event {i}"
            event = json.loads(captured.out.strip())
            seq = int(event["event_id"].split("_")[1])
            sequences.append(seq)
        
        # Verify strictly increasing
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i-1], f"Sequence not increasing: {sequences}"
    
    def test_event_id_uniqueness(self, capsys):
        """Test that event IDs are unique"""
        EventEmitter._instance = None
        
        event_ids = set()
        for i in range(10):
            emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=Scope.LOCAL, actor_id="test")
            captured = capsys.readouterr()
            assert captured.out.strip()
            event = json.loads(captured.out.strip())
            event_id = event["event_id"]
            assert event_id not in event_ids, f"Duplicate event_id: {event_id}"
            event_ids.add(event_id)
        
        assert len(event_ids) == 10
    
    def test_output_is_valid_jsonl(self, capsys):
        """Test that output is valid JSON Lines format"""
        for i in range(3):
            emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=Scope.LOCAL, actor_id=f"actor_{i}")
        
        captured = capsys.readouterr()
        assert captured.out
        lines = [line for line in captured.out.split('\n') if line.strip()]
        assert len(lines) == 3
        
        for line in lines:
            event = json.loads(line)  # Will raise if invalid JSON
            assert isinstance(event, dict)
            assert "event_id" in event
    
    def test_emit_events_false_produces_no_output(self, capsys):
        """Test that emit_events=False disables output"""
        assertion = {
            "assertion_id": "test_003",
            "subject": "person_alice",
            "predicate": "has_name",
            "object": {"kind": "string", "value": "Alice"},
            "scope": "local"
        }
        
        result = validate_assertion_instance(assertion, emit_events=False)
        assert result.valid
        
        captured = capsys.readouterr()
        assert captured.out == "", f"Expected no output with emit_events=False, got: {captured.out}"
    
    def test_event_id_format(self, capsys):
        """Test event_id follows format: event_{seq}_{timestamp_ms}"""
        emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=Scope.LOCAL, actor_id="test")
        
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        event_id = event["event_id"]
        
        parts = event_id.split("_")
        assert len(parts) == 3
        assert parts[0] == "event"
        assert int(parts[1]) > 0  # Sequence
        assert int(parts[2]) > 0  # Timestamp ms
    
    def test_timestamp_is_iso8601_utc(self, capsys):
        """Test timestamp is ISO 8601 format with UTC timezone"""
        emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=Scope.LOCAL, actor_id="test")
        
        captured = capsys.readouterr()
        event = json.loads(captured.out.strip())
        timestamp = event["timestamp"]
        
        iso8601_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+00:00$'
        assert re.match(iso8601_pattern, timestamp), f"Timestamp not ISO 8601 UTC: {timestamp}"
        assert timestamp.endswith("+00:00")
    
    def test_severity_values_are_valid(self, capsys):
        """Test severity values are from allowed set"""
        valid_severities = {"info", "warning", "error", "critical"}
        
        for severity in [Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL]:
            emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=severity, scope=Scope.LOCAL, actor_id="test")
            captured = capsys.readouterr()
            event = json.loads(captured.out.strip())
            assert event["severity"] in valid_severities
    
    def test_scope_values_are_valid(self, capsys):
        """Test scope values are from allowed set"""
        valid_scopes = {"local", "shared", "global"}
        
        for scope in [Scope.LOCAL, Scope.SHARED, Scope.GLOBAL]:
            emit_event(event_type=EventTypes.VALIDATION_STARTED, severity=Severity.INFO, scope=scope, actor_id="test")
            captured = capsys.readouterr()
            event = json.loads(captured.out.strip())
            assert event["scope"] in valid_scopes

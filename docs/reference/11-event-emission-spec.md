# ENKI Event Emission Specification v1.0.0

**Status:** LOCKED (2025-12-31)  
**Phase:** 2 - Event Emission for Observability  
**Architecture:** Option B - Observability Events (NOT AuditEvent instances)  
**Dependencies:** Phase 0 (Foundation), Phase 1 (Storage Contract)

---

## 1. Purpose

This specification defines how ENKI components emit structured observability events, WITHOUT implementing storage or processing. Event emission provides visibility into system operations while maintaining strict separation from storage concerns.

**Key Principles:**
- Events are **ObservabilityEvent objects** (NOT AuditEvent instances)
- Events **emitted to stdout** as JSON lines (newline-delimited JSON)
- **NO storage** - events flow to stdout, external systems capture them
- **NO network** - no direct network calls or external dependencies
- **Deterministic ordering** - events emitted in operation order within process
- **Schema conformance deferred** - Phase 3 maps ObservabilityEvent → AuditEvent
- **Optional emission** - all validators accept `emit_events` parameter (default True)

---

## 2. Architecture Decision: Option B

### 2.1 What This Means

Phase 2 implements **Option B: Observability-Only Events**.

- Phase 2 emits `ObservabilityEvent` objects as JSONL to stdout
- These events are for **observability only** (logging, monitoring, debugging)
- `ObservabilityEvent` is **NOT** an `AuditEvent` instance
- Schema conformance to `audit_event_instance.schema.json` is **deferred to Phase 3**
- Phase 3 ingestion layer will map `ObservabilityEvent` → `AuditEvent` during storage

### 2.2 Why Option B

1. **Separation of concerns**: Observation vs auditable record storage
2. **Flexibility**: Emit rich context without schema constraints
3. **Phase boundaries**: Clear contract between Phase 2 (emit) and Phase 3 (store)
4. **Testability**: Validate ObservabilityEvent contract without schema coupling
5. **Evolution**: Mapping layer can improve without changing Phase 2

### 2.3 Non-Goals (Deferred to Phase 3)

- ❌ Validation against `audit_event_instance.schema.json`
- ❌ Persistent storage of events
- ❌ Event querying or retrieval
- ❌ Audit trail guarantees (handled by Phase 3 storage)

---

## 3. Event Emitter Module

**Location:** `core/events/__init__.py`

### 3.1 Core Components

#### ObservabilityEvent Dataclass
```python
@dataclass
class ObservabilityEvent:
    """
    Phase 2 observability event (NOT an AuditEvent instance)
    
    Required fields (MUST):
        event_id, event_type, timestamp, sequence, severity, scope, metadata
    
    Recommended fields (SHOULD):
        tenant_id, actor_id
    
    Optional fields (MAY):
        assertion_id, pack_id, node_id, target_id, and others
    """
    # MUST fields
    event_id: str          # Format: event_{seq}_{timestamp_ms}
    event_type: str        # Dot notation (e.g., "assertion.validated")
    timestamp: str         # ISO 8601 UTC
    sequence: int          # Monotonically increasing counter
    severity: str          # "info", "warning", "error", "critical"
    scope: str             # "local", "shared", "global"
    metadata: Optional[Dict[str, Any]] = None  # Arbitrary structured data
    
    # SHOULD fields
    tenant_id: Optional[str] = None
    actor_id: Optional[str] = None
    
    # MAY fields (context)
    assertion_id: Optional[str] = None
    pack_id: Optional[str] = None
    node_id: Optional[str] = None
    target_id: Optional[str] = None
```

### 3.2 Nullability Rules

**MUST fields:**
- All MUST fields MUST be present in emitted events
- `event_id`, `event_type`, `timestamp`, `sequence`, `severity`, `scope` MUST NOT be null
- `metadata` MUST be present but MAY be null or empty dict `{}`

**SHOULD fields:**
- `tenant_id`, `actor_id` MAY be null or omitted

**MAY fields:**
- All MAY fields MAY be null or omitted

**Enforcement:**
- EventEmitter validates MUST fields are non-null at emit time
- Events with null MUST fields (except metadata) are rejected before emission

#### EventEmitter Class
- **Lazy singleton pattern** - one emitter instance per process
- **Sequence counter** - monotonic event numbering starting at 1
- **JSON line output** - writes to stdout with `json.dumps()` + newline
- **Dynamic stdout resolution** - resolves `sys.stdout` at emit time (pytest compatible)
- **Thread-safe** - uses lock for counter increments

#### emit_event() Function
```python
def emit_event(
    event_type: str,
    severity: str,
    scope: str,
    actor_id: str,
    assertion_id: Optional[str] = None,
    pack_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
```

Convenience function that creates event_id, timestamp, constructs AuditEvent, and emits to stdout.

### 2.2 Event Types

**Defined in EventTypes class:**

| Event Type | Description | Emitted By |
|------------|-------------|------------|
| `validation.started` | Validation operation begins | validate_pack |
| `pack.loaded` | Pack successfully loaded | validate_pack |
| `pack.validation_failed` | Pack validation failed | validate_pack |
| `assertion.validated` | Assertion passed validation | validate_assertions |
| `assertion.rejected` | Assertion failed validation | validate_assertions |
| `audit.validated` | Audit event passed validation | validate_audit_events |
| `audit.rejected` | Audit event failed validation | validate_audit_events |
| `validation.completed` | Batch validation finished | validate_assertions, validate_audit_events |
| `usage.meter_tick` | Metering event | validate_pack |

### 2.3 Severity Levels

**Defined in Severity class:**

- `INFO` - Normal operations
- `WARNING` - Validation failures, non-critical issues
- `ERROR` - Operational errors
- `CRITICAL` - System-level failures

### 2.4 Scope Levels

**Defined in Scope class:**

- `LOCAL` - Single-node events (default for Phase 2)
- `SHARED` - Multi-node coordination (future)
- `GLOBAL` - Cross-system events (future)

---

## 3. Validator Instrumentation

### 3.1 validate_assertions.py

**Method:** `AssertionValidator.validate_assertion(assertion, emit_events=True)`

**Events Emitted:**

1. **assertion.validated** (on success)
   ```json
   {
     "event_type": "assertion.validated",
     "assertion_id": "<assertion_id>",
     "metadata": {
       "predicate": "<predicate>",
       "object_kind": "<kind>"
     }
   }
   ```

2. **assertion.rejected** (on failure)
   ```json
   {
     "event_type": "assertion.rejected",
     "assertion_id": "<assertion_id>",
     "metadata": {
       "reason": "validation_failed" | "schema_validation_failed",
       "error_count": <n>,
       "error_codes": ["CODE1", "CODE2", ...]
     }
   }
   ```

**Method:** `AssertionValidator.validate_batch(assertions, emit_events=True)`

**Events Emitted:**

3. **validation.completed** (after batch)
   ```json
   {
     "event_type": "validation.completed",
     "metadata": {
       "validation_type": "assertion_batch",
       "total_count": <n>,
       "valid_count": <n>,
       "invalid_count": <n>
     }
   }
   ```

**Batch Behavior:**
- Per-assertion events NOT emitted during batch validation
- Only completion event emitted
- Error messages include "Assertion N: " prefix

### 3.2 validate_audit_events.py

**Method:** `AuditEventValidator.validate_event(event, emit_events=True)`

**Events Emitted:**

1. **audit.validated** (on success)
   ```json
   {
     "event_type": "audit.validated",
     "metadata": {
       "validated_event_id": "<event_id>",
       "event_type": "<original_event_type>"
     }
   }
   ```

2. **audit.rejected** (on failure)
   ```json
   {
     "event_type": "audit.rejected",
     "metadata": {
       "rejected_event_id": "<event_id>",
       "reason": "validation_failed" | "schema_validation_failed",
       "error_count": <n>,
       "error_codes": ["CODE1", "CODE2", ...]
     }
   }
   ```

**Method:** `AuditEventValidator.validate_batch(events, emit_events=True)`

**Events Emitted:**

3. **validation.completed** (after batch)
   ```json
   {
     "event_type": "validation.completed",
     "metadata": {
       "validation_type": "audit_event_batch",
       "total_count": <n>,
       "valid_count": <n>,
       "invalid_count": <n>
     }
   }
   ```

**Batch Behavior:**
- Per-event events NOT emitted during batch validation
- Only completion event emitted
- Error messages include "Event N: " prefix

### 3.3 validate_pack.py (CLI Tool)

**Events Emitted:**

1. **validation.started** (before load_pack)
   ```json
   {
     "event_type": "validation.started",
     "metadata": {
       "validation_type": "pack",
       "pack_path": "<path>"
     }
   }
   ```

2. **pack.loaded** (on success)
   ```json
   {
     "event_type": "pack.loaded",
     "pack_id": "<pack_id>",
     "metadata": {
       "pack_path": "<path>",
       "version": "<version>",
       "definition_count": <n>,
       "warning_count": <n>
     }
   }
   ```

3. **pack.validation_failed** (on error)
   ```json
   {
     "event_type": "pack.validation_failed",
     "pack_id": "<pack_id>" | "unknown",
     "metadata": {
       "pack_path": "<path>",
       "error_count": <n>,
       "warning_count": <n>,
       "first_error": "<message>"
     }
   }
   ```

4. **usage.meter_tick** (always emitted at end)
   ```json
   {
     "event_type": "usage.meter_tick",
     "metadata": {
       "operation": "pack_validation",
       "result": "success" | "failure",
       "definition_count": <n> | "error_count": <n>
     }
   }
   ```

---

## 4. Event Ordering Guarantees

### 4.1 Deterministic Sequence

**MUST:**
- Events emitted in **operation order** (chronological within process)
- Sequence numbers **monotonically increase** (1, 2, 3, ...)
- Each event **MUST** have unique `event_id` within process

**Event ID Format:**
```
event_{sequence}_{timestamp_ms}
```

Example: `event_1_1767216259862`

### 4.2 Timestamp Format

**MUST:**
- ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.ffffff+00:00`
- UTC timezone (offset `+00:00`)
- Microsecond precision

Example: `2025-12-31T21:24:19.866514+00:00`

---

## 5. Output Format

### 5.1 JSON Lines (JSONL)

**MUST:**
- One JSON object per line (newline-delimited)
- UTF-8 encoding
- No trailing comma
- Terminated with `\n` (newline character)

**Field Ordering:**
- JSON object field ordering is **implementation-defined**
- Consumers MUST NOT rely on field order
- Field order MAY change between releases or implementations

### 5.2 Example JSONL Output

```json
{"event_id":"event_1_1735689600000","event_type":"assertion.validated","timestamp":"2025-12-31T12:00:00.000000+00:00","sequence":1,"severity":"info","scope":"local","metadata":{}}
{"event_id":"event_2_1735689601000","event_type":"validation.completed","timestamp":"2025-12-31T12:00:01.000000+00:00","sequence":2,"severity":"info","scope":"local","metadata":{"total_count":1}}
```

## 6. Schema Conformance

**All emitted events MUST conform to:**
- `schemas/audit_event_instance.schema.json`

**Required Fields:**
- `event_id` (string)
- `event_type` (string)
- `timestamp` (string, ISO 8601)
- `severity` (string enum)
- `scope` (string enum)
- `actor_id` (string)

**Optional Fields:**
- `assertion_id` (string)
- `pack_id` (string)
- `metadata` (object)
- `metadata` (object)
- `related_event_ids` (array of strings)
- `session_id` (string)
- `correlation_id` (string)

**Validator Responsibility:**
- Event emitter does NOT validate emitted events
- Validators MUST emit schema-conformant events
- External systems SHOULD validate events on ingestion

---

## 7. Backward Compatibility

### 7.1 API Stability

**Phase 0/1 API Preserved:**
- All validators accept original signatures
- `emit_events` parameter defaults to `True` (Phase 2 behavior)
- Tests pass with `emit_events=False` to disable emission

**Module-Level Functions:**
```python
# Preserved API signatures
validate_assertion_instance(assertion, identity_pack, assertion_vocab_pack, emit_events=True)
validate_assertion_batch(assertions, identity_pack, assertion_vocab_pack, emit_events=True)
validate_audit_event_instance(event, audit_vocab_pack, identity_pack, emit_events=True)
validate_audit_event_batch(events, audit_vocab_pack, identity_pack, emit_events=True)
```

### 7.2 Test Suite

**109/109 tests pass** with Phase 2 changes:
- 16 assertion instance validation tests
- 19 audit event instance validation tests
- 74 other foundation layer tests

**Test Compatibility:**
- Tests can disable events with `emit_events=False`
- No test changes required for Phase 2 (only additions)

---

## 8. Implementation Notes

### 8.1 What Phase 2 DOES

✅ Emits structured audit events to stdout  
✅ Provides observability into validation operations  
✅ Maintains deterministic event ordering  
✅ Conforms to audit_event_instance.schema.json  
✅ Preserves backward compatibility  
✅ Supports batch validation with aggregated events  

### 8.2 What Phase 2 DOES NOT Do

❌ Store events (NO database, NO files)  
❌ Process events (NO aggregation, NO analysis)  
❌ Transmit events (NO network calls)  
❌ Filter events (all events emitted if `emit_events=True`)  
❌ Buffer events (immediate stdout emission)  
❌ Retry failed emissions (fire-and-forget)  

### 7.3 Future Work (Not in Phase 2)

**Phase 3 - Storage Implementation:**
- Event ingestion into PostgreSQL
- Storage Contract record creation
- ProofChain integration
- Receipt generation

**Phase 4 - Processing & Analytics:**
- Event stream processing
- Aggregation and metrics
- Alert generation
- Audit trail queries

**Phase 5 - Distribution:**
- Multi-node event synchronization
- Cross-system event correlation
- Federated event streams

---

## 9. Usage Examples

### 9.1 Basic Validation with Events

```python
from core.validation.validate_assertions import validate_assertion_instance
from core.packs import load_pack

identity_pack = load_pack("libraries/identity")
assertion_vocab_pack = load_pack("libraries/assertion_vocab")

assertion = {
    "assertion_id": "assert_001",
    "subject": "person_alice",
    "predicate": "owns",
    "object": {"kind": "entity_ref", "value": {"entity_id": "device_001", "entity_type": "device"}},
    "scope": "local"
}

result = validate_assertion_instance(assertion, identity_pack, assertion_vocab_pack)
# Event emitted to stdout automatically
# Console output:
# {"event_id": "event_1_...", "event_type": "assertion.validated", ...}
```

### 9.2 Validation Without Events

```python
# For silent operation (e.g., in tests)
result = validate_assertion_instance(assertion, identity_pack, assertion_vocab_pack, emit_events=False)
# No stdout output
```

### 9.3 Capturing Events Externally

**Bash/PowerShell:**
```bash
# Redirect stdout to file
python -m core.tools.validate_pack libraries/identity/ > events.jsonl

# Pipe to jq for filtering
python -m core.tools.validate_pack libraries/identity/ | jq 'select(.severity == "error")'

# Stream to log aggregator
python script.py | tee /dev/tcp/logserver/514
```

**Python:**
```python
import sys
import json
from io import StringIO

# Capture stdout
old_stdout = sys.stdout
sys.stdout = StringIO()

# Run validation
result = validate_assertion_instance(assertion, identity_pack, assertion_vocab_pack)

# Parse emitted events
output = sys.stdout.getvalue()
sys.stdout = old_stdout

for line in output.strip().split('\n'):
    if line:
        event = json.loads(line)
        print(f"Captured event: {event['event_type']}")
```

---

## 9. Testing

### 9.1 Event Emission Tests

**File:** `tests/test_events.py` (TODO)

**Coverage:**
- EventEmitter singleton behavior
- Event ID uniqueness
- Sequence counter monotonicity
- Timestamp format validation
- JSON serialization correctness
- Thread safety (if implemented)

### 9.2 Validator Instrumentation Tests

**Existing tests verify:**
- Validators produce correct validation results
- Error messages include batch context ("Assertion N: ")
- All 109 foundation tests pass with `emit_events=True`

**Additional tests needed:**
- Event emission can be disabled with `emit_events=False`
- Correct events emitted for success/failure scenarios
- Batch validation emits only completion event

---

## 10. Appendix A: Phase 3 Mapping Requirements (Non-Implementation)

This appendix describes how Phase 3 storage layer MUST map `ObservabilityEvent` to `AuditEvent` for persistent storage. This is **informative for Phase 2** but **normative for Phase 3**.

### 10.1 Mapping Responsibility

Phase 3 ingestion is responsible for:

1. **Parsing** JSONL ObservabilityEvent stream from Phase 2 stdout
2. **Mapping** fields from ObservabilityEvent to AuditEvent schema
3. **Validating** against `audit_event_instance.schema.json`
4. **Storing** valid AuditEvent records in PostgreSQL
5. **Handling** invalid events (log mapping failures, don't drop data)

### 10.2 Field Mapping Table

| ObservabilityEvent Field | AuditEvent Field | Mapping Rule |
|-------------------------|------------------|--------------|
| `event_id` | `event_id` | Direct copy (validate format) |
| `event_type` | `event_type` | Direct copy (validate against vocabulary) |
| `timestamp` | `timestamp` | Direct copy (validate ISO 8601) |
| `sequence` | `metadata._enki_observability_sequence` | MUST store in AuditEvent.metadata._enki_observability_sequence for gap detection |
| `severity` | `severity` | Direct copy (validate enum) |
| `scope` | `scope` | Direct copy (validate enum) |
| `metadata` | `metadata` | Transform/merge as needed for schema |
| `tenant_id` | *(storage context)* | Use for partitioning, not event field |
| `actor_id` | `actor_id` | Direct copy if present |
| `assertion_id` | `assertion_id` | Direct copy if present |
| `pack_id` | `pack_id` | Direct copy if present |

### 10.3 Ingestion Error Handling

**Malformed JSONL (parse errors, invalid UTF-8):**
- Phase 3 ingestion MUST NOT crash on parse failures
- Implementation MAY drop or quarantine malformed lines
- SHOULD emit `ingestion.parse_error` ObservabilityEvent with diagnostic context

**Contract Violations (missing MUST fields, null MUST fields, invalid enums):**
- Phase 3 ingestion MUST NOT crash on contract violations
- SHOULD emit `ingestion.contract_violation` ObservabilityEvent with field details
- MAY drop or quarantine invalid events
- MUST preserve original line for forensic analysis

**Gap Detection (sequence discontinuity):**
- Phase 3 SHOULD detect sequence gaps and emit `ingestion.sequence_gap` event
- Gap detection relies on `metadata._enki_observability_sequence` field

### 10.4 Validation Rules

Phase 3 MUST:
- Validate mapped event against `audit_event_instance.schema.json`
- Reject events that fail validation (don't store invalid data)
- Emit ObservabilityEvent for mapping failures themselves (meta-events)
- Preserve original ObservabilityEvent for audit trail
- Track sequence for gap detection via `metadata._enki_observability_sequence`

### 10.5 Example Mapping

**ObservabilityEvent (Phase 2 emits):**
```json
{
  "event_id": "event_42_1735689600000",
  "event_type": "assertion.validated",
  "timestamp": "2025-12-31T12:00:00.000000+00:00",
  "sequence": 42,
  "severity": "info",
  "scope": "local",
  "actor_id": "person_alice",
  "assertion_id": "assert_001",
  "metadata": {"predicate": "has_name", "object_kind": "string"}
}
```

**AuditEvent (Phase 3 stores):**
```json
{
  "event_id": "event_42_1735689600000",
  "event_type": "assertion.validated",
  "timestamp": "2025-12-31T12:00:00.000000+00:00",
  "severity": "info",
  "scope": "local",
  "actor_id": "person_alice",
  "assertion_id": "assert_001",
  "metadata": {
    "predicate": "has_name",
    "object_kind": "string",
    "_enki_observability_sequence": 42
  }
}
```

### 10.6 Why Deferred Mapping

1. **Phase separation**: Phase 2 focused on emission, Phase 3 on storage
2. **Flexibility**: ObservabilityEvent can be richer than audit schema allows
3. **Testability**: Each phase validates its own contract
4. **Evolution**: Mapping can improve without changing Phase 2 emitters
5. **Governance**: Clear boundaries reduce coupling and improve maintainability

---

## 11. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-31 | Initial locked specification. Option B (ObservabilityEvent). Event emission for validators, CLI tools. 121/121 tests passing. |

---

## 12. Compliance

This specification:
- ✅ Conforms to ENKI governance (definition-first, vocabulary in packs)
- ✅ Uses RFC 2119 language (MUST/SHOULD/MAY)
- ✅ Maintains backward compatibility with Phase 0/1
- ✅ Provides deterministic, observable system behavior
- ✅ Separates concerns (emission ≠ storage)
- ✅ Enables external observability without internal coupling
- ✅ Defers schema conformance to Phase 3 (clear boundaries)

**Status:** LOCKED as of 2025-12-31  
**Architecture:** Option B - Observability Events  
**Next Phase:** Phase 3 - Storage Implementation (PostgreSQL, AuditEvent mapping, ProofChain)

# Audit Event Instance Specification

## Overview
This document defines the structure and validation requirements for ENKI audit event instances.

## Purpose

An **audit event instance** is a concrete historical record in ENKI that follows the vocabulary defined in the Audit Event Vocabulary Pack. While the vocabulary defines the grammar (event types, fields, severity levels), an audit event instance is an actual "historical record" using that grammar.

This specification defines:
- The JSON structure of audit event instances
- Validation rules against canonical vocabulary packs
- Field requirements and semantics
- Examples of valid audit events

This is **structure and validation only**. It does not implement event storage, processing, audit trails, log aggregation, event routing, retention policies, access control, or compliance enforcement.

## Conceptual Model

An audit event instance realizes the structure:

```
event_type + fields + severity + timestamp + scope
```

With required context:
- **event_id**: Unique identifier for this specific event
- **event_type**: Type from Audit Vocabulary Pack
- **timestamp**: When the event occurred (ISO 8601)
- **severity**: Classification from Audit Vocabulary Pack (info, warning, error, critical)
- **scope**: Visibility boundary from Identity Pack (local, shared, global)

And optional context:
- **actor_id**: Who triggered the event
- **assertion_id**: Assertion being referenced
- **pack_id**: Pack being referenced
- **node_id**: Node that generated the event
- **target_id/target_type**: What was operated on
- **source**: Where the event originated
- **reason**: Why it happened
- **errors**: Error details for failures
- **metadata**: Additional event-specific data

## Relationship to Audit Event Vocabulary Pack

Audit event instances **use** vocabulary from the Audit Event Vocabulary Pack:

| Instance Field | Vocabulary Source |
|----------------|-------------------|
| `event_type` | `audit_vocab.event_types` event_type_id values |
| `severity` | `audit_vocab.severity` severity_id values |
| `scope` | Identity Pack scope_levels |

The vocabulary defines what kinds of events exist; instances are concrete occurrences.

## Field Definitions

### Required Fields

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `event_id` | string | Unique event identifier | Pattern: `^a-z0-9?$` |
| `event_type` | string | Event type identifier | Must exist in Audit Vocabulary Pack |
| `timestamp` | string | ISO 8601 timestamp | Must be valid ISO 8601 date-time |
| `severity` | string | Severity level | Must be: `info`, `warning`, `error`, or `critical` |
| `scope` | string | Visibility scope | Must be: `local`, `shared`, or `global` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `actor_id` | string | Actor identifier |
| `assertion_id` | string | Assertion identifier |
| `pack_id` | string | Pack identifier |
| `node_id` | string | Node identifier |
| `target_id` | string | Target identifier |
| `target_type` | string | Target type |
| `source` | string or object | Event source |
| `reason` | string | Explanation |
| `errors` | array | Error details |
| `metadata` | object | Additional data |

## Validation Rules

An audit event instance is valid if:

1. **Schema Valid**: Passes JSON Schema validation against `schemas/audit_event_instance.schema.json`
2. **Event Type Valid**: The `event_type` value exists in the Audit Vocabulary Pack's event types list
3. **Severity Valid**: The `severity` value is one of: `info`, `warning`, `error`, `critical` (validated by schema enum)
4. **Scope Valid**: The `scope` value is one of: `local`, `shared`, `global` (validated by schema enum)
5. **Well-Formed IDs**: All identifier fields are well-formed strings
6. **Deterministic**: Validation produces stable, sorted error messages

Validation does NOT enforce:
- Event causality or ordering
- Actor existence or permissions
- Assertion existence
- Pack existence
- Node existence
- Temporal validity windows
- Event processing or side effects

## Examples

### Assertion Lifecycle Event

```json
{
  "event_id": "evt_001",
  "event_type": "assertion.proposed",
  "timestamp": "2025-12-31T10:00:00Z",
  "severity": "info",
  "scope": "local",
  "actor_id": "person_alice",
  "assertion_id": "assert_001"
}
```

### Pack Operation Event

```json
{
  "event_id": "evt_002",
  "event_type": "pack.loaded",
  "timestamp": "2025-12-31T09:00:00Z",
  "severity": "info",
  "scope": "local",
  "pack_id": "identity",
  "node_id": "node_primary",
  "metadata": {
    "version": "0.1.0",
    "definitions_count": 4
  }
}
```

### Node Lifecycle Event

```json
{
  "event_id": "evt_003",
  "event_type": "node.started",
  "timestamp": "2025-12-31T08:00:00Z",
  "severity": "info",
  "scope": "local",
  "node_id": "node_primary",
  "metadata": {
    "version": "0.1.0",
    "environment": "production"
  }
}
```

### Error Event

```json
{
  "event_id": "evt_004",
  "event_type": "assertion.rejected",
  "timestamp": "2025-12-31T10:15:00Z",
  "severity": "error",
  "scope": "local",
  "assertion_id": "assert_bad_001",
  "reason": "Invalid predicate",
  "errors": [
    {
      "code": "INVALID_PREDICATE",
      "message": "Predicate not found in vocabulary"
    }
  ]
}
```

## Validation Process

The validation process:

1. Load Audit Vocabulary Pack using Definition Pack Loader
2. Load Identity Pack using Definition Pack Loader (for scope validation)
3. Parse audit event instance(s) from JSON
4. Validate each event:
   - Schema validation
   - Event type vocabulary validation
   - Severity validation (schema enum)
   - Scope validation (schema enum)
5. Return validation result with sorted errors (if any)

## Non-Goals

This specification explicitly does NOT include:

- **Event Storage**: No database, no persistence layer, no log files
- **Event Processing**: No handlers, no triggers, no workflows, no side effects
- **Audit Trails**: No audit log implementation or management
- **Log Aggregation**: No centralized logging or monitoring systems
- **Event Routing**: No pub/sub, no event bus, no messaging
- **Retention Policies**: No data lifecycle or retention management
- **Access Control**: No authentication or authorization for events
- **Compliance Enforcement**: No regulatory compliance mechanisms
- **Event Correlation**: No pattern detection, no causality analysis
- **Temporal Ordering**: No event sequencing or ordering guarantees

These concerns are handled by higher-level audit systems.

## Schema Compliance

Audit event instances must validate against:
- `schemas/audit_event_instance.schema.json`

## Relationship to Existing Systems

This specification depends on:
- **Audit Event Vocabulary Pack**: For event_type and severity vocabulary
- **Identity Pack**: For scope vocabulary (`local`, `shared`, `global`)

It does not modify or extend these packs.

## Versioning

Version: 0.1.0

Changes to this specification require version increment:
- Major: Breaking changes to schema or validation rules
- Minor: New optional fields or non-breaking extensions
- Patch: Clarifications or corrections

## Implementation

Implementation is in:
- Schema: `schemas/audit_event_instance.schema.json`
- Validation: `core/validation/validate_audit_events.py`
- CLI Tool: `core/tools/validate_audit_events.py`
- Tests: `services/api/tests/test_audit_event_instance_validation.py`

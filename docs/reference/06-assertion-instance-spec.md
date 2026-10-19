# Assertion Instance Specification

## Overview
This document defines the structure and validation requirements for ENKI assertion instances.

## Purpose

An **assertion instance** is a concrete statement in ENKI that follows the vocabulary defined in the Assertion Vocabulary Pack. While the vocabulary defines the grammar (predicates, object kinds, forms), an assertion instance is an actual "sentence" using that grammar.

This specification defines:
- The JSON structure of assertion instances
- Validation rules against canonical vocabulary packs
- Field requirements and semantics
- Examples of valid assertions

This is **structure and validation only**. It does not implement storage, conflict resolution, audit logging, or networking.

## Conceptual Model

An assertion instance realizes the triple structure:

```
subject → predicate → object
```

With additional context:
- **assertion_id**: Unique identifier for this specific assertion
- **scope**: Visibility boundary (from Identity Pack)
- **timestamp**: Optional temporal context
- **source**: Optional provenance information
- **metadata**: Optional additional data

## Field Definitions

### Required Fields

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `assertion_id` | string | Unique assertion identifier | Pattern: `^a-z0-9?$` |
| `subject` | string | Entity ID of the subject | Must be a valid entity identifier |
| `predicate` | string | Predicate verb | Must exist in Assertion Vocabulary Pack |
| `object` | object | Object value with kind | See Object Structure below |
| `scope` | string | Visibility scope | Must be `local`, `shared`, or `global` (from Identity Pack) |

### Object Structure

The `object` field is an object with:

| Field | Type | Description |
|-------|------|-------------|
| `kind` | string | Object kind identifier | Must exist in Assertion Vocabulary Pack |
| `value` | any | The actual value | Type depends on kind |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 timestamp | Optional temporal context |
| `source` | string or object | Provenance information | Optional source tracking |
| `metadata` | object | Additional metadata | Optional arbitrary data |

## Validation Rules

An assertion instance is valid if:

1. **Schema Valid**: Passes JSON Schema validation against `schemas/assertion_instance.schema.json`
2. **Predicate Valid**: The `predicate` value exists in the Assertion Vocabulary Pack's predicate list
3. **Object Kind Valid**: The `object.kind` value exists in the Assertion Vocabulary Pack's object kinds list
4. **Object Kind Allowed**: The `object.kind` is in the predicate's `allowed_object_kinds` list
5. **Scope Valid**: The `scope` value is one of: `local`, `shared`, `global` (from Identity Pack)
6. **Deterministic**: Validation produces stable, sorted error messages

Validation does NOT enforce:
- Entity existence (subject/object entities need not exist in any database)
- Conflict detection or resolution
- Access control or permissions
- Temporal ordering or validity windows
- Source authority ranking

## Examples

### Entity → Entity Assertion

```json
{
  "assertion_id": "assert_001",
  "subject": "person_alice",
  "predicate": "owns",
  "object": {
    "kind": "entity_ref",
    "value": {
      "entity_id": "device_laptop",
      "entity_type": "device"
    }
  },
  "scope": "local",
  "timestamp": "2025-12-31T10:00:00Z"
}
```

### Entity → Scalar Assertion

```json
{
  "assertion_id": "assert_002",
  "subject": "person_alice",
  "predicate": "has_name",
  "object": {
    "kind": "string",
    "value": "Alice Smith"
  },
  "scope": "shared"
}
```

### Entity → Reference Assertion

```json
{
  "assertion_id": "assert_003",
  "subject": "dataset_xyz",
  "predicate": "references",
  "object": {
    "kind": "uri",
    "value": "https://example.com/source"
  },
  "scope": "global",
  "timestamp": "2025-12-31T12:00:00Z"
}
```

## Validation Process

The validation process:

1. Load Identity Pack using Definition Pack Loader
2. Load Assertion Vocabulary Pack using Definition Pack Loader
3. Parse assertion instance(s) from JSON
4. Validate each assertion:
   - Schema validation
   - Vocabulary validation (predicate, object kind, scope)
   - Predicate-object kind compatibility
5. Return validation result with sorted errors (if any)

## Non-Goals

This specification explicitly does NOT include:

- **Storage**: No database, no persistence layer
- **Conflict Resolution**: No detection or resolution of conflicting assertions
- **Audit Logging**: No tracking of validation events
- **Authentication/Authorization**: No access control
- **Licensing/Payment**: No enforcement mechanisms
- **Networking**: No sync, replication, or distribution
- **Truth Maintenance**: No reasoning or inference
- **Query Language**: No search or query capabilities

These concerns are handled by higher-level systems.

## Schema Compliance

Assertion instances must validate against:
- `schemas/assertion_instance.schema.json`

## Relationship to Existing Packs

This specification depends on:
- **Identity Pack**: For scope vocabulary (`local`, `shared`, `global`)
- **Assertion Vocabulary Pack**: For predicates, object kinds, and forms

It does not modify or extend these packs.

## Versioning

Version: 0.1.0

Changes to this specification require version increment:
- Major: Breaking changes to schema or validation rules
- Minor: New optional fields or non-breaking extensions
- Patch: Clarifications or corrections

## Implementation

Implementation is in:
- Schema: `schemas/assertion_instance.schema.json`
- Validation: `core/validation/validate_assertions.py`
- CLI Tool: `core/tools/validate_assertions.py`
- Tests: `services/api/tests/test_assertion_instance_validation.py`

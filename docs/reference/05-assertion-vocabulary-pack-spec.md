# Assertion Vocabulary Pack Specification

## Overview
This document defines the structure and content of the Assertion Vocabulary definition library.

## Purpose

The Assertion Vocabulary Pack provides canonical vocabulary for constructing assertions in ENKI systems. An **assertion** is a declarative statement expressing a relationship or property:

```
subject → predicate → object
```

This pack defines:
- **Predicates**: Canonical verbs that express relationships (is_a, owns, references, etc.)
- **Object Kinds**: Allowed object types (entity_ref, string, number, uri, etc.)
- **Forms**: Assertion templates (Entity→Entity, Entity→Scalar, Entity→Reference)
- **Conflicts**: Conflict classification labels (exclusive, temporal, scoped, etc.)
- **System**: Pack metadata and assertion conceptual model

This is a **vocabulary-only** pack. It does not implement assertion storage, validation logic, conflict resolution, or enforcement mechanisms.

## Conceptual Model

An assertion in ENKI follows the triple structure:

- **Subject**: An entity from the Identity Pack (person, organization, device, dataset, definition_pack)
- **Predicate**: A verb from the canonical predicate list (is_a, has_name, owns, etc.)
- **Object**: A value of a specified kind (entity_ref, string, number, timestamp, uri, etc.)

This vocabulary enables future systems to construct, store, and reason about assertions while maintaining semantic consistency.

## Library Structure

The Assertion Vocabulary library is organized as a definition pack containing:
- System metadata and conceptual model
- Predicate verb definitions
- Object kind definitions
- Assertion form templates
- Conflict label taxonomy

## pack.json

Metadata for the Assertion Vocabulary definition pack:
- ID: assertion_vocab
- Version: 0.1.0 (semantic versioning)
- Dependencies: references identity pack conceptually
- Registry compliance

## Definitions

### assertion_vocab.system.json
Core system properties:
- Pack purpose and conceptual model
- Subject → predicate → object structure
- Dependency note on Identity Pack vocabulary

### assertion_vocab.predicates.json
Canonical predicate verbs:
- `is_a`: Type/category relationship
- `has_name`: Name assignment
- `located_in`: Location relationship
- `owns`: Ownership relationship
- `created`: Creation relationship
- `derived_from`: Derivation relationship
- `references`: Reference relationship
- `mentions`: Mention relationship
- `has_status`: Status assignment

Each predicate specifies allowed subject entities and object kinds.

### assertion_vocab.object_kinds.json
Allowed object value types:
- `entity_ref`: Reference to an identity entity
- `string`: Text value
- `number`: Numeric value
- `boolean`: True/false value
- `timestamp`: ISO 8601 timestamp
- `pack_ref`: Reference to a definition pack
- `uri`: Uniform resource identifier

### assertion_vocab.forms.json
Canonical assertion templates:
- Entity → predicate → Entity
- Entity → predicate → Scalar
- Entity → predicate → Reference

Templates describe structure only, not validation or enforcement.

### assertion_vocab.conflicts.json
Conflict classification labels:
- `exclusive`: Mutually exclusive assertions
- `multi_valued`: Multiple values allowed
- `temporal`: Time-ordered conflicts
- `scoped`: Scope-dependent conflicts
- `source_ranked`: Source authority ranking

Labels only — conflict resolution logic is not defined in this pack.

## Schema Compliance

All definition files must validate against:
- `schemas/definition.schema.json`
- `schemas/registry_pack.schema.json` (for pack.json)

## Versioning

Definition changes require version increment:
- Major: Breaking changes to vocabulary structure
- Minor: New predicates, object kinds, or forms
- Patch: Corrections to descriptions or metadata

## Non-Goals

This pack explicitly does NOT include:
- Assertion storage mechanisms
- Assertion validation logic
- Conflict resolution algorithms
- Truth maintenance systems
- Query languages or engines
- Access control for assertions
- Audit trails or provenance tracking
- Network protocols for assertion exchange

These concerns are handled by higher-level systems that reference this vocabulary.

## Examples

See `examples/example.assertion_templates.json` for sample assertion structures using this vocabulary.

## Relationship to Identity Pack

This pack depends conceptually on the Identity Pack for:
- Subject entity types (person, organization, device, dataset, definition_pack)
- Entity scopes (local, shared, global)
- Actor types for assertion creation context

The Identity Pack vocabulary is referenced in predicate definitions but not enforced at this layer.

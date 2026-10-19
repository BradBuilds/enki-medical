# Audit Event Vocabulary Pack Specification

## Overview
This document defines the structure and content of the Audit Event Vocabulary definition library.

## Purpose

The Audit Event Vocabulary Pack provides canonical vocabulary for audit events in ENKI systems. An **audit event** is a declarative record describing an activity or state change in the system:

- Assertion lifecycle events (proposed, accepted, rejected, validated)
- Pack operations (loaded, validation_failed)
- Node activities (started, heartbeat)
- Usage tracking (meter_tick)

This pack defines:
- **Event Types**: Canonical event categories with identifiers and labels
- **Fields**: Standard audit event field vocabulary
- **Severity Levels**: Event severity classification (info, warning, error, critical)
- **System**: Pack metadata and conceptual model

This is a **vocabulary-only** pack. It does not implement event storage, processing, audit trails, log aggregation, or enforcement mechanisms.

## Conceptual Model

An audit event in ENKI captures a discrete system activity:

```
event_type + fields + severity + timestamp
```

Events describe:
- **Assertion lifecycle**: Changes to assertion state
- **System operations**: Pack loading, validation, node activities
- **Usage tracking**: Metering and resource usage

Audit events are descriptive, not prescriptive. They describe what happened, not what should happen.

## Relationship to Other Packs

This pack conceptually relates to:
- **Assertion Vocabulary Pack**: Many events describe assertion lifecycle
- **Identity Pack**: Events reference actors, entities, and scopes
- **Definition Packs**: Events track pack operations

This vocabulary enables future audit systems to record and analyze system history consistently.

## Library Structure

The Audit Event Vocabulary library is organized as a definition pack containing:
- System metadata and conceptual model
- Event type definitions
- Field vocabulary
- Severity level taxonomy

## pack.json

Metadata for the Audit Event Vocabulary definition pack:
- ID: audit_vocab
- Version: 0.1.0 (semantic versioning)
- Dependencies: none (conceptual references only)
- Registry compliance

## Definitions

### audit_vocab.system.json
Core system properties:
- Pack purpose and scope
- Relationship to assertions and system activity
- Declarative-only nature

### audit_vocab.event_types.json
Canonical audit event types:
- **Assertion events**: assertion.proposed, assertion.accepted, assertion.rejected, assertion.validated
- **Pack events**: pack.loaded, pack.validation_failed
- **Node events**: node.started, node.heartbeat
- **Usage events**: usage.meter_tick

Each event type includes identifier, label, and descriptive notes.

### audit_vocab.fields.json
Standard audit event fields:
- `actor_id`: Identity of actor performing action
- `assertion_id`: Assertion being referenced
- `pack_id`: Pack being referenced
- `node_id`: Node identifier
- `timestamp`: Event occurrence time
- `scope`: Visibility scope
- `source`: Event source

Vocabulary only — actual event structure is defined elsewhere.

### audit_vocab.severity.json
Event severity levels:
- `info`: Informational events
- `warning`: Warning conditions
- `error`: Error conditions
- `critical`: Critical issues requiring attention

## Schema Compliance

All definition files must validate against:
- `schemas/definition.schema.json`
- `schemas/registry_pack.schema.json` (for pack.json)

## Versioning

Definition changes require version increment:
- Major: Breaking changes to vocabulary structure
- Minor: New event types, fields, or severity levels
- Patch: Corrections to descriptions or metadata

## Non-Goals

This pack explicitly does NOT include:

- **Event Storage**: No database, no persistence layer, no log files
- **Event Processing**: No event handlers, no triggers, no workflows
- **Audit Trails**: No audit log implementation or management
- **Log Aggregation**: No centralized logging or monitoring
- **Event Routing**: No pub/sub, no event bus, no messaging
- **Retention Policies**: No data lifecycle management
- **Access Control**: No authentication or authorization for events
- **Compliance Enforcement**: No regulatory compliance mechanisms
- **Event Correlation**: No pattern detection or analysis

These concerns are handled by higher-level audit systems that reference this vocabulary.

## Examples

See `examples/example.audit_events.json` for sample audit event structures using this vocabulary.

## Usage Pattern

Future audit systems will:
1. Use event types from this vocabulary
2. Include fields from this vocabulary
3. Assign severity from this vocabulary
4. Store/process events according to their implementation

This pack provides the "grammar" for audit events; systems provide the "sentences" and storage.

## Relationship to Assertion Instances

Audit events and assertion instances are complementary:
- **Assertions**: State claims about entities (subject → predicate → object)
- **Audit Events**: State changes and system activities (what happened, when, by whom)

Many audit events describe assertion lifecycle, but events also capture broader system activity beyond assertions.

## Implementation

Implementation is in:
- Definitions: `libraries/audit_vocab/definitions/*.json`
- Examples: `libraries/audit_vocab/examples/example.audit_events.json`

No code implementation in this version (vocabulary only).

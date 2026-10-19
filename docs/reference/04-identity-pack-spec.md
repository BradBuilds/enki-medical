# Identity Pack Specification

## Overview
This document defines the structure and content of the Identity definition library.

## Purpose

The Identity Pack provides canonical vocabulary for identity primitives used throughout ENKI systems:
- **Actors**: Categories of entities that can perform actions (human, ai, service, node)
- **Entities**: Types of identifiable objects in the system (person, organization, device, dataset, definition_pack)
- **Scopes**: Visibility and sharing boundaries (local, shared, global)
- **System**: Pack metadata and identity formatting rules

This is a **vocabulary-only** pack. It does not implement authentication, permissions, licensing, or audit logging.

## Library Structure

The Identity library is organized as a definition pack containing:
- System metadata
- Actor category definitions
- Entity type definitions
- Scope level definitions

## pack.json

Metadata for the Identity definition pack:
- ID: identity
- Version: 0.1.0 (semantic versioning)
- Dependencies: none
- Registry compliance

## Definitions

### identity.system.json
Core system properties:
- Pack name and purpose
- Identity ID formatting requirements
- Version information

### identity.actors.json
Actor categories that can perform actions:
- `human`: Human users
- `ai`: AI agents and systems
- `service`: Automated services
- `node`: ENKI nodes

### identity.entities.json
Entity types that can be identified:
- `person`: Individual human
- `organization`: Organizational entity
- `device`: Physical or virtual device
- `dataset`: Data collection
- `definition_pack`: ENKI definition pack

### identity.scopes.json
Scope levels for visibility and sharing:
- `local`: Node-local only
- `shared`: Shared within a trust boundary
- `global`: Globally visible/accessible

## Schema Compliance

All definition files must validate against:
- `schemas/definition.schema.json`
- `schemas/registry_pack.schema.json` (for pack.json)

## Versioning

Definition changes require version increment:
- Major: Breaking changes to vocabulary structure
- Minor: New actor/entity/scope categories
- Patch: Corrections to descriptions or metadata

## Non-Goals

This pack explicitly does NOT include:
- Authentication mechanisms
- Permission or authorization rules
- License validation
- Ownership logic
- Audit event definitions
- Network protocols
- Database schemas
- API endpoints

These concerns are handled by higher-level systems that reference this vocabulary.

## Examples

See `examples/example.identity.json` for sample identity definition usage.

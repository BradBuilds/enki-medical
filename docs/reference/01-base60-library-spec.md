# Base-60 Library Specification

## Overview
This document defines the structure and content of the Base-60 definition library.

## Library Structure

The Base-60 library is organized as a definition pack containing:
- System metadata
- Numeric rules
- Glyph definitions
- Digit specifications

## pack.json

Metadata for the Base-60 definition pack:
- ID: |base60|
- Version: semantic versioning
- Dependencies: none for core pack
- Registry compliance

## Definitions

### base60.system.json
Core system properties:
- Base value (60)
- Digit range (0-59)
- Place value semantics

### base60.rules.json
Operational rules:
- Digit composition (tens + units)
- Place value calculation
- Zero handling

### base60.glyphs.json
Glyph rendering specifications:
- Style definitions
- Symbol mappings
- Rendering parameters

### base60.digits.json
Individual digit definitions:
- Digit value (0-59)
- Tens component
- Units component
- Valid glyph representations

## Schema Compliance

All definition files must validate against:
- definition.schema.json
- registry_pack.schema.json

## Versioning

Definition changes require version increment:
- Major: Breaking changes to numeric semantics
- Minor: New glyph styles or non-breaking additions
- Patch: Corrections to existing definitions


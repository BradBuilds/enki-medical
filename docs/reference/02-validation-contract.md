# Validation Contract

## Purpose
This document defines the validation requirements for ENKI Base-60 system.

## Validation Levels

### 1. Schema Validation
- JSON structure compliance
- Type checking
- Required field presence
- Format validation

### 2. Semantic Validation
- Digit range enforcement (0-59)
- Place value consistency
- Referential integrity
- No duplicate definitions

### 3. Rendering Validation
- Deterministic output (per SPINE-00 v1.0.1: same input → same output always)
- Style availability
- Symbol mapping correctness

## Validation Functions

### validate_base60_digit(d: int)
**Input:** Integer value
**Output:** |{ok: bool, errors: list[str]}|
**Rules:**
- Must be integer
- Must be >= 0
- Must be <= 59

### validate_base60_places(places: list[int])
**Input:** List of place values
**Output:** |{ok: bool, errors: list[str]}|
**Rules:**
- Must be non-empty list
- Each place must be valid digit
- No null or undefined values

### validate_definition_pack(path: str)
**Input:** Path to definition pack
**Output:** |{ok: bool, errors: list[str], warnings: list[str]}|
**Rules:**
- pack.json must exist and be valid
- All referenced definitions must exist
- No circular dependencies
- Version format must be semantic
- All definitions must pass schema validation

## Error Codes

| Code | Meaning |
|------|---------|
| BASE60_DIGIT_RANGE | Digit outside 0-59 |
| BASE60_INVALID_TYPE | Wrong type (e.g., string instead of int) |
| BASE60_EMPTY_PLACES | Empty place list |
| BASE60_NULL_VALUE | Null or undefined value |
| SCHEMA_VIOLATION | JSON schema validation failed |
| MISSING_DEFINITION | Referenced definition not found |
| DUPLICATE_ID | Definition ID appears multiple times |
| VERSION_FORMAT | Invalid version string |

## Validation Guarantees

The validation layer MUST guarantee:
1. No invalid input reaches rendering functions
2. All errors are caught before state changes
3. Error messages are deterministic and clear (per SPINE-00 v1.0.1)
4. Validation results are reproducible

**Determinism Requirements (SPINE-00 v1.0.1):**
- Errors sorted by (error_code, pack_id, primary_ref, message)
- JSON uses RFC 8785 JCS canonicalization with Unicode NFC normalization
- No timestamps or random data in validation outputs
- Cross-platform reproducibility guaranteed

See docs/spine/SPINE-00-foundations.md for complete specification.

## Testing Requirements

Each validation function must have tests for:
- Valid input (passes)
- Boundary cases
- Invalid type
- Out of range
- Edge cases (empty, null, etc.)


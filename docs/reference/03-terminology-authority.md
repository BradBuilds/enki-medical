# ENKI Terminology Authority - Definition Fields

**Date:** 2025-12-31  
**Status:** ✅ LOCKED  
**Authority:** Canonical Schema

---

## Official Terminology

The following field names are **canonical** and **immutable** for ENKI definition files:

### Primary Fields

| Canonical Name | Type | Required | Description |
|----------------|------|----------|-------------|
| `id` | string | ✅ Yes | Unique identifier (e.g., `base60.system`) |
| `type` | string | ✅ Yes | Definition type (`system`, `rules`, `glyphs`, `digits`, `custom`) |
| `version` | string | ✅ Yes | Semantic version (e.g., `0.1.0`) |
| `content` | object | ✅ Yes | Definition-specific content |
| `description` | string | ⚠️ Optional | Human-readable description |
| `metadata` | object | ⚠️ Optional | Metadata (created, modified, author) |
| `dependencies` | array | ⚠️ Optional | List of dependency IDs |

---

## Authority Source

**The canonical source of truth is:**
```
schemas/definition.schema.json
```

This schema:
- Requires `["id", "type", "version", "content"]`
- Defines `id` pattern: `^a-z0-9?$`
- Defines `type` enum: `["system", "rules", "glyphs", "digits", "custom"]`
- Defines `version` pattern: `^\d+\.\d+\.\d+$` (semantic versioning)

**Rule:** All definition files MUST validate against this schema.

---

## ❌ Prohibited Terminology

The following terms are **NOT canonical** and must NOT appear in definition files:

| Prohibited | Canonical | Notes |
|------------|-----------|-------|
| `definition_id` | `id` | Use `id` only |
| `kind` | `type` | Use `type` only |
| `def_id` | `id` | Use `id` only |
| `defType` | `type` | Use `type` only (snake_case) |

**These are forbidden to prevent terminology drift.**

---

## Verification

### Current State: ✅ COMPLIANT

All Base-60 definitions correctly use canonical terminology:

```json
{
  "id": "base60.system",           ✅ Correct
  "type": "system",                 ✅ Correct
  "version": "0.1.0",               ✅ Correct
  "content": { ... }                ✅ Correct
}
```

**NOT:**
```json
{
  "definition_id": "base60.system", ❌ WRONG
  "kind": "system",                 ❌ WRONG
}
```

### Pack Loader: ✅ COMPLIANT

The pack loader correctly implements canonical terminology:
- Validates against `schemas/definition.schema.json`
- Uses `definition.id` and `definition.type` in Python code
- All tests use canonical field names
- No internal aliases or mappings

### Test Coverage: ✅ VERIFIED

All 74 tests pass using canonical terminology:
- Schema validation enforces `id` and `type`
- Invalid field names are rejected
- No tests use `definition_id` or `kind`

---

## Historical Context

If earlier planning documents or informal discussions mentioned `definition_id` or `kind`, those terms were **superseded** by the canonical schema.

**Timeline:**
1. Schema created with `id` and `type` fields
2. Base-60 definitions implemented following schema
3. Pack loader built to schema specification
4. **Result:** Consistent terminology throughout system

**No migration needed** - system was built correctly from start.

---

## Internal Code Guidelines

### Python Code (Correct)
```python
# ✅ Correct usage
definition.id
definition.type
result.index.by_id
result.index.by_type

# ❌ Wrong - don't use these
definition.definition_id
definition.kind
result.index.by_kind
```

### JSON Files (Correct)
```json
{
  "id": "base60.system",
  "type": "system"
}
```

### Documentation (Correct)
When referring to fields:
- ✅ "The definition's `id` field"
- ✅ "The `type` must be one of..."
- ❌ "The `definition_id` specifies..."
- ❌ "The `kind` of definition..."

---

## Enforcement

### Schema Validation
The pack loader enforces canonical terminology through JSON schema validation:
```python
# This will FAIL if using wrong field names
jsonschema.validate(instance=def_data, schema=definition_schema)
```

### Code Review Checklist
When reviewing new packs or code:
- ✅ All definitions use `id` and `type`
- ✅ No references to `definition_id` or `kind`
- ✅ Python code uses `.id` and `.type` attributes
- ✅ Documentation uses canonical terms

### Future Packs
All future definition packs MUST:
1. Validate against `schemas/definition.schema.json`
2. Use `id` and `type` fields
3. Follow canonical terminology in all metadata

---

## Why This Matters

**Authority clarity prevents:**
- Mixed terminology across packs
- Validator conditionals (`if 'id' in data or 'definition_id' in data`)
- Documentation inconsistency
- Developer confusion
- Schema drift

**The principle:**
> Schemas are canonical. Code follows schemas. No exceptions.

---

## Declaration

As of **2025-12-31**, the following terminology is **locked and immutable**:

| Field | Canonical Name | Status |
|-------|----------------|--------|
| Identifier | `id` | 🔒 LOCKED |
| Definition Type | `type` | 🔒 LOCKED |
| Version | `version` | 🔒 LOCKED |
| Content | `content` | 🔒 LOCKED |

**Any deviation from these terms constitutes a schema violation.**

---

## Conclusion

ENKI uses **`id` and `type`** as canonical field names, as defined in `schemas/definition.schema.json`.

This terminology is:
- ✅ Locked in schema
- ✅ Implemented in all definitions
- ✅ Enforced by pack loader
- ✅ Verified by tests
- ✅ Documented comprehensively

**No terminology drift exists. Authority is clear. System is compliant.**

---

**Authority:** `schemas/definition.schema.json`  
**Implementation:** Pack Loader v1.0.0  
**Verification:** 74/74 tests passing  
**Status:** 🔒 LOCKED ✅

# PHASE 2 SPECIFICATION — LDU-W Workable Layer

**Status:** SPECIFICATION (locked once acceptance tests pass)  
**Date:** 2026-01-13  
**Scope:** Defines contract for Local Workable Definition Universe (LDU-W)  
**Predecessor:** PHASE 1 (LDU-T) ✅ COMPLETE  

---

## Core Concept: Claim vs Canonical

```
LDU-T (Temporary):
├─ Raw text, speech, API messages
├─ resolution = null (always — no meaning decided)
└─ Ambiguity preserved

LDU-W (Workable):  ← PHASE 2
├─ Derived workable interpretations built ON TOP of LDU-T
├─ claim = actual meaning/definition (workable, locally valid)
├─ canonical_resolution = null (always — not authority-backed)
├─ Explicitly scoped: domain + culture + community + time_period
└─ Immutable once written (like LDU-T)

GDU (Governed):  ← PHASE 3+
├─ Canonical, cryptographically signed
├─ canonical_resolution = actual authority (e.g., ISO, IETF)
├─ Admission ceremony required
└─ Never modifiable without new ceremony
```

**Key Rule:** LDU-W stores a **proposed interpretation** with full accountability to origin (LDU-T). NOT canonical, NOT final, but real and immutable.

---

## Immutability Rules

### Immutable (blocked by trigger):
- `source_ldu_t_ids` — Never change where this came from
- `claim` — The workable definition itself (what we're claiming)
- `gdu_shape` — What GDU structure this targets
- `scope_*` (domain, culture, community, time_period) — Scope cannot shift
- `derivation_method` — How was this interpretation made?
- `term` — The term being defined (primary index)

### Mutable (updates allowed):
- `metadata` — Tags, notes, reviewer feedback
- `status` — Review status (draft → reviewed → ready_for_promotion)
- `version` — Incremented on metadata/status change
- `updated_at` — Timestamp of last change

### Never Exists:
- `resolution` — LDU-W never has this. If promoting to GDU later, a separate ceremony sets canonical values.
- `canonical_resolution` — Set to NULL in schema as documentation, never written to

---

## Scope Model (Explicit, Non-Null)

Every definition must declare:

```json
{
  "term": "example",
  "claim": "workable meaning goes here",
  "scope": {
    "domain": "medical",           // e.g., "medical", "legal", "software"
    "culture": "US English",       // e.g., "US English", "UK English", "ISO"
    "community": "hospital-X",     // e.g., "ISO", "IETF", "hospital-network-A"
    "time_period": "2020-2030"     // e.g., "2020-2030", "current", "historical"
  }
}
```

All four fields REQUIRED, non-empty strings, NFC-normalized.

---

## Lineage: Traceable to LDU-T

Every LDU-W definition must declare which LDU-T entries it's derived from:

```json
{
  "source_ldu_t_ids": [
    "ldu_t_entry_001",
    "ldu_t_entry_042",
    "ldu_t_entry_099"
  ]
}
```

Adapter validates: all IDs must exist in `ldu_t_entries` table at INSERT time.

Forward query available: "Show me all LDU-W definitions that reference this LDU-T entry"

---

## GDU Shape Declaration

LDU-W doesn't auto-detect GDU shape; it **declares** which shape it targets:

```json
{
  "gdu_shape": {
    "structure": "simple_definition",  // or "hierarchical", "parametric", etc.
    "target_universe": "GDU",
    "version": "1.0"
  }
}
```

This is checked against known GDU shapes (validates conformance pattern, not content).

---

## Three-Layer Enforcement (Mirroring PHASE 1)

### Layer 1: JSON Schema
- `scope` object with all 4 fields required, non-empty
- `source_ldu_t_ids` minItems 1 (not empty)
- `claim` required, non-empty string
- `term` required, non-empty, alphanumeric + underscore
- No `resolution` field allowed
- `canonical_resolution` explicitly set to null (documentation)

### Layer 2: Adapter (Python)
- `validate_ldu_w_full()` before any INSERT
- Reject entries missing scope fields
- Reject entries with non-existent source_ldu_t_ids
- Reject entries with `resolution` or `canonical_resolution != null`
- Force `canonical_resolution = null` on all writes

### Layer 3: Database (PostgreSQL)
- `scope_domain`, `scope_culture`, `scope_community`, `scope_time_period` all NOT NULL
- `source_ldu_t_ids` TEXT[] NOT NULL CHECK (array_length(source_ldu_t_ids, 1) > 0)
- `universe` CHECK (universe = 'LDU-W')
- `canonical_resolution` NOT NULL DEFAULT NULL (contradictory, but documents "never touches this")
- BEFORE UPDATE trigger blocks all immutable fields

---

## No GDU Authority at LDU-W

**Hard rule:** LDU-W entries NEVER have:
- `promoted = true`
- `admitted_to_gdu = true`
- `canonical_status = "official"`
- Any cryptographic signature

LDU-W is **proposed, scoped, immutable but local**. Promotion happens in PHASE 3+ via admission ceremony.

Validator: `validate_ldu_w_no_gdu_write()` rejects any entry claiming GDU authority.

---

## API Surface (Adapter Methods)

```python
class LDUWAdapter:
    def insert_definition(entry, validate=True) → (success, msg, definition_id)
    def update_metadata(definition_id, metadata_updates, updated_by)
    def update_status(definition_id, new_status, updated_by)
    def get_definition_by_id(definition_id) → dict or None
    def get_definitions_by_scope(domain, culture, community, time_period=None) → list
    def get_definitions_by_ldu_t_source(ldu_t_entry_id) → list
    def get_definitions_by_term(term, domain=None) → list
    def batch_insert(entries, derivation_method, ingestion_actor) → receipt
```

---

## Acceptance Test Contract

**TEST A: Scope Enforcement**
- A1: Schema rejects missing scope fields
- A2: Adapter rejects missing scope fields
- A3: Database CHECK constraint blocks null scope on INSERT

**TEST B: Lineage Enforcement**
- B1: Adapter rejects non-existent source_ldu_t_ids
- B2: Adapter accepts valid source_ldu_t_ids
- B3: Forward query works: "which LDU-W definitions cite this LDU-T entry?"

**TEST C: Immutability**
- C1: Insert valid definition
- C2: Trigger blocks UPDATE to claim
- C3: Trigger blocks UPDATE to scope_*
- C4: Trigger ALLOWS UPDATE to metadata/status

**TEST D: GDU Authority Block**
- D1: Reject entry with `promoted=true`
- D2: Reject entry with `canonical_resolution != null`
- D3: Reject entry claiming GDU signature

**TEST E: Batch Performance**
- E1: Insert 100 valid definitions in < 10 seconds
- E2: Receipts recorded correctly
- E3: Scope index query (domain + culture) in < 10ms

---

## Ready for Implementation

DB schema → JSON schema → Validators → Adapter → Tests (in that order).

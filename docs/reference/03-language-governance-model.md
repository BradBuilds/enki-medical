# Language Governance Model

**Version:** 1.0.0  
**Status:** LOCKED  
**Date:** 2026-01-13  
**Supersedes:** None  
**Authority:** SPINE-S1.2  

---

## EXECUTIVE SUMMARY

This document establishes the **semantic governance contract** for linguistic meaning in the ENKI system.

It defines:
- **What may be canonical** (GDU: Governed Definition Universe)
- **What must be local** (LDU: Local Definition Universe)
- **How meaning is represented without interpretation**
- **How definitions are promoted from local to canonical**

**Critical Principle**: The system stores ambiguity explicitly and defers resolution. Meaning is relationships between concepts, not text interpretation.

---

## 1. AUTHORITY BOUNDARIES

### 1.1 The Three-Universe Contract

| Universe | Full Name | Allowed | Forbidden | Purpose | Mutability |
|----------|-----------|---------|-----------|---------|------------|
| **GDU** | Governed Definition Universe | Shapes, relation types, feature spaces, invariants | Words, slang, corpora, context, interpretation | Live computation, canonical reference | Immutable (ceremony-gated) |
| **LDU-T** | Local Definition Universe (Temporary) | Raw text, claims, ambiguity, conflicting meanings, corpus data | Canonical status, global authority | Preservation, experimentation | Mutable (local writes) |
| **LDU-W** | Local Definition Universe (Workable) | GDU-shaped definitions, validated mappings, local constraints | Runtime authority without promotion | Validation, staging | Mutable (validation-gated) |

### 1.2 Dependency Rules (INVARIANT)

**Rule 1.2.1**: GDU definitions NEVER depend on LDU definitions.  
**Rule 1.2.2**: LDU definitions MUST map to GDU shapes to be computationally usable.  
**Rule 1.2.3**: LDU-W definitions MAY be promoted to GDU via admission ceremony.  
**Rule 1.2.4**: LDU-T data MAY be shaped into LDU-W via validation.  

**Violation Consequence**: Any violation of 1.2.1 invalidates the entire definition set.

---

## 2. GDU LANGUAGE PACK SPECIFICATION

### 2.1 What the Language Pack IS

The language pack defines:
- **How meaning is represented** (semantic relations exist)
- **What kinds of meaning exist** (hypernymy, polysemy, speech acts)
- **What relationships are allowed** (relation types enumerated)
- **What feature spaces exist** (phonological features, morphological processes)
- **What symbol systems exist** (scripts, glyphs)

### 2.2 What the Language Pack IS NOT

The language pack does NOT:
- Decide what a word "means" in context
- Resolve ambiguity
- Choose between interpretations
- Define corpus-specific vocabulary
- Enforce cultural interpretation
- Contain executable logic

### 2.3 Language Pack Definition Types

All GDU language definitions fall into these categories:

| Definition Type | Role | Examples | Authority |
|----------------|------|----------|-----------|
| **Ontology Anchors** | Root domain establishment | `language.system` | Declares governed domain |
| **Shape Constraints** | Structural requirements | `language.scripts`, `language.phonology` | What structures are valid |
| **Relation Enumerations** | Allowed relationship types | `language.semantics` | What connections exist |
| **Feature Spaces** | Dimensional constraints | `language.morphology` | What transformations are possible |
| **Intent Classifications** | Pragmatic categories | `language.pragmatics` | What actions are signaled |
| **Symbol Metadata** | Deterministic rendering | `language.glyphs.*` | How symbols are represented |
| **Lookup Indexes** | Acceleration structures | `language.indexes` | Where to find things |

---

## 3. LDU SPECIFICATION

### 3.1 LDU-T (Temporary / Raw)

**Purpose**: Preserve ambiguity and raw linguistic data without collapsing interpretation.

**Allowed Content**:
- Raw text (verbatim sentences, paragraphs, transcripts)
- Speech transcriptions with timing metadata
- Corpus annotations (conflicting allowed)
- Slang, neologisms, evolving usage
- Multiple conflicting interpretations of the same text
- Provenance metadata (source, timestamp, context)

**Storage Requirements**:
- MUST preserve original form
- MUST NOT resolve ambiguity
- MUST track provenance
- MAY contain conflicting claims
- MAY be incomplete or inconsistent

**Example LDU-T Entry**:
```json
{
  "id": "ldu_t_book_001_sentence_42",
  "source": "Book: 'Example Novel', page 42",
  "text": "His car was sick.",
  "ambiguity_preserved": true,
  "semantic_candidates": [
    {
      "term": "sick",
      "candidate_meanings": [
        {"type": "literal", "maps_to_gdu": "language.semantics.synonymy", "candidate": "ill"},
        {"type": "metaphor", "maps_to_gdu": "language.semantics.synonymy", "candidate": "damaged"},
        {"type": "slang", "maps_to_gdu": "language.semantics.polysemy", "candidate": "impressive"}
      ]
    }
  ],
  "resolution": null,
  "provenance": {
    "ingestion_timestamp": "2026-01-13T16:00:00Z",
    "ingestion_method": "book_parser_v1"
  }
}
```

### 3.2 LDU-W (Workable / Validated)

**Purpose**: Hold validated, GDU-shaped definitions that are not yet globally canonical.

**Allowed Content**:
- Definitions conforming to GDU schemas
- Local semantic extensions (validated against `language.semantics` relation types)
- Domain-specific vocabulary (validated against GDU shape requirements)
- Candidate definitions awaiting promotion

**Validation Requirements**:
- MUST conform to GDU schemas
- MUST reference GDU relation types
- MUST NOT claim canonical authority
- MAY extend GDU vocabulary within allowed relation types
- MAY be promoted to GDU via ceremony

**Example LDU-W Entry**:
```json
{
  "id": "ldu_w_medical_term_hypertension",
  "status": "workable",
  "gdu_shape_conformance": true,
  "definition": {
    "term": "hypertension",
    "semantic_relations": [
      {
        "relation_type": "language.semantics.hypernymy",
        "parent": "medical_condition"
      },
      {
        "relation_type": "language.semantics.synonymy",
        "synonym": "high_blood_pressure"
      }
    ]
  },
  "validation": {
    "gdu_relation_types_used": [
      "language.semantics.hypernymy",
      "language.semantics.synonymy"
    ],
    "schema_valid": true
  },
  "promotion_candidate": true,
  "evidence_required": ["medical_authority_review", "usage_corpus_validation"]
}
```

---

## 4. SEMANTIC MAPPING RULES

### 4.1 The Core Principle

**Meaning is relationships between concepts, not text.**

Text is a pointer. Meaning is a graph.

### 4.2 Mapping Pipeline (Conceptual)

```
Raw Text (LDU-T)
    ↓
Ambiguity Enumeration
    ↓
GDU Shape Validation
    ↓
Semantic Candidate Mapping (references GDU relation types)
    ↓
LDU-W (Validated)
    ↓
[Optional] Promotion to GDU via Ceremony
```

### 4.3 Forbidden Patterns

**Pattern 1: Canonical Interpretation Without Evidence**
```
❌ FORBIDDEN:
{
  "text": "His car was sick.",
  "meaning": "damaged",  // ← Collapsed ambiguity
  "authority": "GDU"     // ← False authority claim
}

✅ ALLOWED:
{
  "text": "His car was sick.",
  "semantic_candidates": ["ill", "damaged", "slang_positive"],
  "resolution": null,    // ← Ambiguity preserved
  "authority": "LDU-T"
}
```

**Pattern 2: GDU Definition Depending on Corpus**
```
❌ FORBIDDEN:
// In GDU definition
{
  "id": "language.semantics.sick",
  "meaning": "damaged",  // ← Corpus-specific interpretation in GDU
  "evidence": "corpus_analysis"
}

✅ ALLOWED:
// In GDU definition
{
  "id": "language.semantics",
  "semantic_relations": {
    "polysemy": "one word, multiple related senses"  // ← Shape only
  }
}

// In LDU-W
{
  "term": "sick",
  "relation_type": "language.semantics.polysemy",
  "senses": ["ill", "damaged", "slang_positive"]
}
```

**Pattern 3: Runtime Logic in Definitions**
```
❌ FORBIDDEN:
{
  "id": "language.phonology",
  "pronunciation_engine": "function(text) { ... }"  // ← Executable code
}

✅ ALLOWED:
{
  "id": "language.phonology",
  "phoneme_inventory": {
    "consonants": { "total": 42, "features": [...] }  // ← Data only
  }
}
```

---

## 5. PROMOTION CEREMONIES

### 5.1 LDU-W → GDU Promotion Criteria

A definition in LDU-W qualifies for GDU promotion if:

**Criterion 5.1.1**: Conforms to GDU schemas (validated)  
**Criterion 5.1.2**: References only GDU relation types (no external dependencies)  
**Criterion 5.1.3**: Has evidence of global applicability (not context-specific)  
**Criterion 5.1.4**: Has community review approval (governance process)  
**Criterion 5.1.5**: Does not conflict with existing GDU definitions  

### 5.2 Promotion Review Process

**Step 1: Nomination**
- LDU-W definition is nominated for promotion
- Evidence package is submitted (usage data, authoritative sources, validation reports)

**Step 2: Technical Validation**
- Schema conformance verified
- GDU dependency check (must pass Rule 1.2.1)
- Namespace collision check
- Hash computation

**Step 3: Community Review**
- Open review period (minimum 14 days)
- Domain expert approval required
- Conflict resolution (if conflicting definitions exist)

**Step 4: Admission Ceremony**
- Definition added to active set
- Content hash computed
- Activation record created
- Immutability sealed

**Step 5: Publication**
- Definition becomes GDU canonical
- LDU-W entry marked as "promoted"
- Dependent systems notified

### 5.3 Rejection Handling

If promotion is rejected:
- Definition remains in LDU-W (still valid locally)
- Rejection reason recorded
- Re-nomination allowed after revision

---

## 6. INGESTION SCENARIOS (Reference)

See `docs/04-language-ingestion-scenarios.md` for concrete examples.

**Minimum Required Scenarios**:
1. **Book Sentence** ("sick car" example) — Proves ambiguity preservation
2. **Speech → Phonology** — Proves modal independence
3. **API Event → Pragmatics** — Proves agent-readiness

---

## 7. GOVERNANCE INVARIANTS

### 7.1 Immutability Rules

**Invariant 7.1.1**: Once a definition is admitted to GDU, it NEVER changes.  
**Invariant 7.1.2**: Versioning is the only mechanism for evolution (new version = new definition).  
**Invariant 7.1.3**: Content hashes MUST remain stable across identical inputs.  

### 7.2 Determinism Rules

**Invariant 7.2.1**: Same inputs → same outputs (no randomness).  
**Invariant 7.2.2**: No external API calls in validation.  
**Invariant 7.2.3**: No time-dependent behavior (except timestamp recording).  

### 7.3 Separation of Concerns

**Invariant 7.3.1**: GDU contains shapes, not meanings.  
**Invariant 7.3.2**: LDU contains meanings, not authority.  
**Invariant 7.3.3**: Promotion is the only bridge (ceremony-gated).  

---

## 8. VIOLATION HANDLING

### 8.1 Detection

Violations are detected via:
- Schema validation (automated)
- Dependency analysis (automated)
- Community review (manual)
- Audit trails (automated)

### 8.2 Consequences

| Violation Type | Consequence | Remediation |
|----------------|-------------|-------------|
| GDU depends on LDU | Definition rejected | Remove LDU dependency |
| Runtime logic in definition | Ceremony fails | Remove executable code |
| Ambiguity collapsed prematurely | Ingestion warning | Preserve ambiguity in LDU-T |
| False authority claim | Validation error | Correct universe assignment |
| Schema non-conformance | Validation error | Fix schema violations |

### 8.3 Appeals Process

If a rejection is disputed:
- Evidence may be re-submitted
- Community review may be requested
- Governance board (if established) makes final decision

---

## 9. EVOLUTION AND VERSIONING

### 9.1 GDU Evolution

GDU vocabulary evolves via:
- **New definitions** (promoted from LDU-W via ceremony)
- **New versions** (existing definitions versioned, old versions remain)
- **Never modification** (immutability preserved)

### 9.2 This Document's Evolution

This governance model itself is versioned:
- **Version 1.0.0**: Initial language governance contract
- **Future versions**: Must be approved via governance process
- **Backward compatibility**: Old versions remain accessible

---

## 10. BINDING CLAUSES

### 10.1 Authority

This document is **LOCKED** and governs all language-related definitions in ENKI.

### 10.2 Precedence

In case of conflict:
1. SPINE-S1.2 governance rules (highest authority)
2. This document (language-specific governance)
3. Implementation-specific policies (lowest authority)

### 10.3 Amendments

Amendments to this document require:
- Formal proposal
- Community review (minimum 30 days)
- Governance board approval
- New version number
- Ceremony admission

---

## 11. EXAMPLES AND NON-EXAMPLES

### 11.1 Valid GDU Definitions

✅ **language.semantics** (relation types enumerated)
```json
{
  "id": "language.semantics",
  "type": "custom",
  "version": "0.1.0",
  "content": {
    "semantic_relations": {
      "synonymy": "words with same/similar meaning",
      "antonymy": "words with opposite meaning",
      "hypernymy": "is-a relationships (superordinate)"
    }
  }
}
```

✅ **language.scripts** (shape constraints only)
```json
{
  "id": "language.scripts",
  "type": "rules",
  "version": "0.1.0",
  "content": {
    "scripts": {
      "latin": {
        "expected_glyphs": 1114,
        "v0_1_0_included_glyphs": 251,
        "completeness": "partial"
      }
    }
  }
}
```

### 11.2 Invalid GDU Definitions

❌ **Word meanings in GDU**
```json
{
  "id": "language.vocabulary.sick",  // ← Wrong universe
  "meanings": ["ill", "damaged", "cool"]  // ← Corpus-specific
}
```

❌ **Executable logic in GDU**
```json
{
  "id": "language.phonology",
  "pronunciation_function": "def pronounce(text): ..."  // ← Code
}
```

### 11.3 Valid LDU-T Entries

✅ **Raw text with ambiguity**
```json
{
  "id": "ldu_t_001",
  "text": "His car was sick.",
  "ambiguity_preserved": true,
  "semantic_candidates": ["ill", "damaged", "slang_positive"],
  "resolution": null
}
```

### 11.4 Valid LDU-W Entries

✅ **Validated definition awaiting promotion**
```json
{
  "id": "ldu_w_medical_001",
  "term": "hypertension",
  "semantic_relations": [
    {
      "relation_type": "language.semantics.hypernymy",
      "parent": "medical_condition"
    }
  ],
  "gdu_shape_conformance": true,
  "promotion_candidate": true
}
```

---

## 12. REFERENCE IMPLEMENTATION

Current GDU language pack:
- **Pack ID**: `language`
- **Version**: `0.1.0`
- **Definitions**: 10
- **Ceremony Status**: Admitted (2026-01-13)
- **Transcript Hash**: `sha256:d178213048e99f4d2d70a317c6e1eb5503a6eec544f459839a57d3c4e70356e0`

See:
- `libraries/language/pack.json`
- `docs/LANGUAGE_PACK_SCHEMA_REFERENCE.md`
- `storage/admission/language_v1/validation_transcript.json`

---

## 13. GLOSSARY

**GDU**: Governed Definition Universe — canonical, immutable, ceremony-admitted definitions  
**LDU-T**: Local Definition Universe (Temporary) — raw text, ambiguity preserved  
**LDU-W**: Local Definition Universe (Workable) — validated, GDU-shaped, promotion-ready  
**Promotion**: Process of moving LDU-W definition to GDU via ceremony  
**Shape**: Structural constraint (what is allowed, not what it means)  
**Meaning**: Relationship between concepts (graph, not text)  
**Ambiguity Preservation**: Storing multiple interpretations without collapsing to one  
**Semantic Candidate**: Possible meaning mapped to GDU relation type  
**Provenance**: Origin, timestamp, and context metadata  

---

## 14. CHANGE LOG

| Version | Date | Change | Authority |
|---------|------|--------|-----------|
| 1.0.0 | 2026-01-13 | Initial language governance contract | SPINE-S1.2 |

---

## 15. ACKNOWLEDGMENTS

This governance model formalizes the GDU/LDU separation principle and the "meaning is relationships" philosophy established during language pack development (2026-01-13).

---

**END OF DOCUMENT**

**Status**: LOCKED  
**Next Document**: `docs/04-language-ingestion-scenarios.md`  
**Related Documents**: `docs/01-base60-library-spec.md`, `docs/LANGUAGE_PACK_SCHEMA_REFERENCE.md`

# Language Promotion Ceremonies

**Version:** 1.0.0  
**Status:** LOCKED  
**Date:** 2026-01-13  
**Supersedes:** None  
**Authority:** SPINE-S1.2  
**Governance Contract:** `docs/03-language-governance-model.md`  
**Ingestion Scenarios:** `docs/04-language-ingestion-scenarios.md`  

---

## EXECUTIVE SUMMARY

This document defines **how meaning becomes canonical** without collapsing ambiguity, erasing history, or centralizing authority.

Promotion ceremonies are the **bridge from LDU-W to GDU**. They are:
- **Evidence-based** (not opinion-based)
- **Version-preserving** (not erasure-based)
- **Conflict-tolerant** (not consensus-forced)
- **Provenance-tracked** (not anonymous)

**Critical Principle**: Promotion does NOT mean "this is the only correct meaning." It means "this meaning has sufficient evidence for global reference."

---

## 1. THE PROMOTION PROBLEM

### 1.1 What We're Solving

**Problem**: How do you promote local definitions (LDU-W) to canonical status (GDU) when:
- Meanings are contextual, not absolute
- Evidence is distributed, not centralized
- Interpretations conflict legitimately
- Language evolves continuously
- Authority is contested

**Non-Solution**: Declare one meaning "correct" and reject others.

**Actual Solution**: Promote definitions that have **sufficient evidence of global applicability** while preserving conflicting interpretations as separate canonical entries.

### 1.2 What Promotion Is NOT

❌ **Promotion is NOT**:
- A vote on which meaning is "right"
- A mechanism to eliminate ambiguity
- A way to enforce cultural interpretation
- A centralized authority decision
- An erasure of alternative meanings

✅ **Promotion IS**:
- Evidence-based validation of global applicability
- Version-controlled addition to canonical set
- Conflict-preserving (multiple meanings can coexist)
- Provenance-tracked (all evidence recorded)
- Governance-gated (ceremony required)

---

## 2. EVIDENCE REQUIREMENTS

### 2.1 What Counts as "Global Enough"

A definition is **globally applicable** if it meets ONE OR MORE of these criteria:

| Criterion | Description | Evidence Required | Example |
|-----------|-------------|-------------------|---------|
| **Cross-Domain Usage** | Used across multiple unrelated contexts | 3+ domain corpora showing usage | "sick" (medical) vs "sick" (slang) — separate promotions |
| **Authoritative Source** | Recognized by domain authority | Published standard, dictionary entry, regulatory definition | Medical terminology from WHO |
| **Historical Stability** | Stable usage over extended period | 10+ years of consistent usage evidence | "knight" (medieval warrior) |
| **Technical Necessity** | Required for interoperability | API spec, protocol definition, standard | HTTP status codes |
| **Community Consensus** | Broad agreement in specific community | Governance review + approval | Specialized jargon in established field |

**Critical Rule**: Evidence MUST be verifiable and traceable. No anonymous claims.

### 2.2 Evidence Package Structure

```json
{
  "evidence_package": {
    "definition_id": "ldu_w_medical_001_hypertension",
    "term": "hypertension",
    "promotion_request_id": "promo_req_2026_01_13_001",
    "evidence": {
      "criterion": "authoritative_source",
      "sources": [
        {
          "source_type": "medical_authority",
          "authority": "World Health Organization",
          "document": "ICD-11 Classification",
          "url": "https://icd.who.int/browse11/l-m/en#/http://id.who.int/icd/entity/1380071536",
          "publication_date": "2022-01-01",
          "verification_method": "url_fetch",
          "verification_timestamp": "2026-01-13T10:00:00Z"
        },
        {
          "source_type": "corpus_usage",
          "corpus": "PubMed Medical Literature",
          "usage_count": 125000,
          "date_range": "2010-2025",
          "verification_method": "corpus_query",
          "verification_timestamp": "2026-01-13T10:05:00Z"
        }
      ],
      "global_applicability_justification": "Medical term with standardized definition used globally across healthcare systems"
    },
    "semantic_relations": [
      {
        "relation_type": "language.semantics.hypernymy",
        "parent": "cardiovascular_disease",
        "gdu_conformance": true
      },
      {
        "relation_type": "language.semantics.synonymy",
        "synonym": "high_blood_pressure",
        "gdu_conformance": true
      }
    ],
    "conflicts": {
      "conflicting_definitions": [],
      "conflict_resolution": "no_conflicts"
    }
  }
}
```

### 2.3 Insufficient Evidence

❌ **Examples of INSUFFICIENT evidence**:
- "I think this word means X"
- "Everyone I know uses it this way"
- "It's obvious from context"
- Single-source corpus without verification
- Anonymous submissions

✅ **Remediation**: Gather verifiable sources, establish traceability, document provenance.

---

## 3. CONFLICT RESOLUTION

### 3.1 The Core Principle

**Multiple canonical meanings can coexist.**

Conflict does NOT require choosing one "winner." It requires establishing that each conflicting interpretation has sufficient evidence.

### 3.2 Conflict Taxonomy

| Conflict Type | Description | Resolution Strategy |
|---------------|-------------|---------------------|
| **Polysemy** | Same word, related meanings | Promote both as separate GDU entries with shared etymology |
| **Homonymy** | Same word, unrelated meanings | Promote both as separate GDU entries with distinct IDs |
| **Diachronic Shift** | Meaning changed over time | Version both: `term.v1` (historical) and `term.v2` (modern) |
| **Domain-Specific** | Different meanings in different fields | Promote with domain tags: `term.medical`, `term.legal` |
| **Cultural Variant** | Different interpretations across cultures | Promote with culture tags: `term.en_US`, `term.en_UK` |

### 3.3 Conflict Resolution Examples

#### Example 1: Polysemy ("bank")

**Scenario**: "bank" has multiple related meanings.

**Resolution**: Promote as separate entries with shared root.

```json
{
  "gdu_entries": [
    {
      "id": "language.vocabulary.bank.financial",
      "term": "bank",
      "sense": "financial_institution",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.hypernymy",
          "parent": "financial_institution"
        }
      ],
      "evidence": {
        "criterion": "authoritative_source",
        "sources": ["Federal Reserve definitions", "Banking regulations"]
      },
      "related_senses": ["language.vocabulary.bank.river"]
    },
    {
      "id": "language.vocabulary.bank.river",
      "term": "bank",
      "sense": "river_edge",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.hypernymy",
          "parent": "geographic_feature"
        }
      ],
      "evidence": {
        "criterion": "cross_domain_usage",
        "sources": ["Geographic terminology", "Hydrology texts"]
      },
      "related_senses": ["language.vocabulary.bank.financial"]
    }
  ]
}
```

**Key Observation**: Both promoted. Neither erased. Relationship preserved.

---

#### Example 2: Domain-Specific Conflict ("latency")

**Scenario**: "latency" means different things in medicine vs computing.

**Resolution**: Promote both with domain tags.

```json
{
  "gdu_entries": [
    {
      "id": "language.vocabulary.latency.medical",
      "term": "latency",
      "domain": "medical",
      "definition": "period between infection and symptom onset",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.hypernymy",
          "parent": "temporal_interval"
        }
      ],
      "evidence": {
        "criterion": "authoritative_source",
        "sources": ["Medical dictionaries", "Epidemiology texts"]
      }
    },
    {
      "id": "language.vocabulary.latency.computing",
      "term": "latency",
      "domain": "computing",
      "definition": "delay between request and response",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.hypernymy",
          "parent": "temporal_delay"
        }
      ],
      "evidence": {
        "criterion": "technical_necessity",
        "sources": ["Network protocol specs", "Computing standards"]
      }
    }
  ]
}
```

**Key Observation**: Domain tag prevents collision. Both valid. System can choose based on context.

---

#### Example 3: Diachronic Shift ("awful")

**Scenario**: "awful" meant "full of awe" (positive) historically, now means "terrible" (negative).

**Resolution**: Version both. Historical meaning preserved.

```json
{
  "gdu_entries": [
    {
      "id": "language.vocabulary.awful.v1",
      "term": "awful",
      "version": "historical",
      "temporal_range": "pre-1800",
      "definition": "inspiring awe, worthy of reverence",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.synonymy",
          "synonym": "awe-inspiring"
        }
      ],
      "evidence": {
        "criterion": "historical_stability",
        "sources": ["Historical text corpora 1400-1800"]
      },
      "status": "historical"
    },
    {
      "id": "language.vocabulary.awful.v2",
      "term": "awful",
      "version": "modern",
      "temporal_range": "post-1800",
      "definition": "extremely bad or unpleasant",
      "semantic_relations": [
        {
          "relation_type": "language.semantics.synonymy",
          "synonym": "terrible"
        },
        {
          "relation_type": "language.semantics.antonymy",
          "opposite": "wonderful"
        }
      ],
      "evidence": {
        "criterion": "cross_domain_usage",
        "sources": ["Modern text corpora 1800-2025"]
      },
      "status": "active"
    }
  ]
}
```

**Key Observation**: History NOT erased. Both versions canonical. Semantic shift documented.

---

### 3.4 Unresolvable Conflicts

**Scenario**: Two definitions claim authority but evidence is insufficient for both.

**Resolution**:
1. If one has sufficient evidence → promote that one
2. If neither has sufficient evidence → reject both, remain in LDU-W
3. If evidence is contested → escalate to governance review

**Critical Rule**: Promotion requires positive evidence, not absence of objection.

---

## 4. VERSIONING WITHOUT ERASURE

### 4.1 The Immutability Principle

**Once promoted, definitions are NEVER modified.**

Changes require new versions:
- `term.v1` → `term.v2` (both exist)
- `term.medical.v1` → `term.medical.v2` (both exist)
- `term.2020` → `term.2025` (both exist)

### 4.2 Version Lifecycle

```
LDU-W Definition Created
    ↓
Evidence Package Assembled
    ↓
Promotion Ceremony (v1.0.0)
    ↓
GDU Entry: term.v1 (IMMUTABLE)
    ↓
[Years pass, meaning evolves]
    ↓
New LDU-W Definition Created (term.v2)
    ↓
Evidence Package Assembled (v2)
    ↓
Promotion Ceremony (v2.0.0)
    ↓
GDU Entry: term.v2 (IMMUTABLE)
    ↓
Both term.v1 and term.v2 coexist
```

### 4.3 Deprecation (Not Deletion)

If a meaning becomes obsolete:
- Mark as `status: deprecated`
- Add `deprecated_date`
- Add `superseded_by: term.v2`
- NEVER delete

```json
{
  "id": "language.vocabulary.gay.v1",
  "term": "gay",
  "version": "historical",
  "definition": "joyful, carefree",
  "status": "deprecated",
  "deprecated_date": "1960-01-01",
  "superseded_by": "language.vocabulary.gay.v2",
  "semantic_relations": [
    {
      "relation_type": "language.semantics.synonymy",
      "synonym": "joyful"
    }
  ],
  "evidence": {
    "criterion": "historical_stability",
    "sources": ["Historical text corpora 1800-1960"]
  }
}
```

**Key Observation**: Historical meaning preserved. Not erased. Clearly marked as deprecated.

---

## 5. PROMOTION CEREMONY SPECIFICATION

### 5.1 Ceremony Phases

| Phase | Name | Duration | Activities | Gate |
|-------|------|----------|-----------|------|
| **Phase 1** | Nomination | 1 day | LDU-W definition nominated, evidence package submitted | Evidence completeness check |
| **Phase 2** | Technical Validation | 3-5 days | Schema validation, GDU conformance check, hash computation, conflict detection | Technical validation pass |
| **Phase 3** | Community Review | 14-30 days | Public review period, domain expert consultation, conflict resolution | Review approval (no blocking objections with evidence) |
| **Phase 4** | Governance Decision | 1-3 days | Final approval by governance board (if established) or automated if uncontested | Approval decision |
| **Phase 5** | Admission | 1 day | Add to active set, compute transcript hash, publish activation record | Immutability sealed |

### 5.2 Phase 1: Nomination

**Inputs**:
- LDU-W definition ID
- Evidence package
- Promotion request metadata

**Validation Checks**:
- Evidence package has required fields
- At least one evidence criterion met
- Sources are verifiable
- Semantic relations reference GDU

**Outputs**:
- Promotion request ID
- Evidence completeness report
- Proceed to Phase 2 OR reject with reasons

```json
{
  "phase": "nomination",
  "promotion_request_id": "promo_req_2026_01_13_001",
  "ldu_w_definition_id": "ldu_w_medical_001_hypertension",
  "nominator": "user_medical_expert_123",
  "nomination_timestamp": "2026-01-13T08:00:00Z",
  "evidence_completeness": {
    "criterion_met": "authoritative_source",
    "sources_count": 2,
    "sources_verifiable": true,
    "semantic_relations_count": 2,
    "gdu_conformance": true
  },
  "status": "nomination_complete",
  "next_phase": "technical_validation"
}
```

---

### 5.3 Phase 2: Technical Validation

**Validation Checks**:
- Schema conformance (GDU definition schema)
- GDU relation existence (all referenced relations exist)
- Namespace collision check (ID not already used)
- Content hash computation
- Conflict detection (search for existing definitions with same term)

**Outputs**:
- Validation report
- Content hash
- Conflict report
- Proceed to Phase 3 OR reject with technical errors

```json
{
  "phase": "technical_validation",
  "promotion_request_id": "promo_req_2026_01_13_001",
  "validation_report": {
    "timestamp": "2026-01-13T08:30:00Z",
    "validator": "gdu_promotion_validator_v1.0.0",
    "checks": [
      {
        "check_type": "schema_conformance",
        "result": "pass",
        "schema": "gdu_definition.schema.json"
      },
      {
        "check_type": "gdu_relation_existence",
        "relations_checked": [
          "language.semantics.hypernymy",
          "language.semantics.synonymy"
        ],
        "result": "pass"
      },
      {
        "check_type": "namespace_collision",
        "proposed_id": "language.vocabulary.hypertension",
        "result": "pass",
        "collision_detected": false
      },
      {
        "check_type": "content_hash",
        "result": "pass",
        "hash": "sha256:a1b2c3d4e5f6..."
      },
      {
        "check_type": "conflict_detection",
        "result": "no_conflicts",
        "existing_definitions_with_term": []
      }
    ],
    "overall_status": "pass"
  },
  "next_phase": "community_review"
}
```

---

### 5.4 Phase 3: Community Review

**Duration**: 14-30 days (depends on complexity and controversy)

**Activities**:
- Public review period (definition published to review portal)
- Domain expert consultation (experts in relevant field invited to review)
- Evidence verification (independent verification of sources)
- Conflict resolution (if conflicting definitions emerge)

**Review Outcomes**:
- **Approve**: No blocking objections with evidence
- **Approve with Modifications**: Minor adjustments required
- **Defer**: More evidence needed
- **Reject**: Insufficient evidence or unresolvable conflicts

**Blocking Objection**: An objection is "blocking" ONLY if:
1. It provides counter-evidence of equal or greater quality
2. It identifies a technical violation of governance rules
3. It demonstrates GDU dependency rule violation

**Non-Blocking Feedback**: Suggestions, preferences, or opinions without counter-evidence.

```json
{
  "phase": "community_review",
  "promotion_request_id": "promo_req_2026_01_13_001",
  "review_period": {
    "start_date": "2026-01-13T09:00:00Z",
    "end_date": "2026-01-27T09:00:00Z",
    "duration_days": 14
  },
  "review_activities": {
    "domain_expert_reviews": [
      {
        "expert_id": "expert_medical_terminology_456",
        "expertise": "medical_terminology",
        "review_date": "2026-01-15T10:00:00Z",
        "recommendation": "approve",
        "comments": "Definition aligns with WHO ICD-11 classification"
      },
      {
        "expert_id": "expert_cardiology_789",
        "expertise": "cardiology",
        "review_date": "2026-01-16T14:00:00Z",
        "recommendation": "approve",
        "comments": "Consistent with clinical usage in cardiology"
      }
    ],
    "public_comments": [
      {
        "commenter_id": "user_123",
        "comment": "Should include ICD-10 code as well",
        "blocking": false,
        "type": "suggestion"
      }
    ],
    "blocking_objections": [],
    "evidence_verification": {
      "sources_verified": 2,
      "verification_method": "automated_url_fetch",
      "verification_status": "all_verified"
    }
  },
  "review_outcome": "approve",
  "next_phase": "governance_decision"
}
```

---

### 5.5 Phase 4: Governance Decision

**Decision Makers** (in order of precedence):
1. **Automated Approval**: If no blocking objections after review period
2. **Domain Governance Board**: If domain-specific board exists
3. **General Governance Board**: If contentious or cross-domain
4. **Fallback**: SPINE-S1.2 governance rules

**Decision Criteria**:
- Evidence sufficient?
- Technical validation passed?
- No unresolved blocking objections?
- Governance rules followed?

**Possible Decisions**:
- **Approve**: Proceed to admission
- **Approve with Conditions**: Minor changes required (re-validate)
- **Defer**: Request more evidence
- **Reject**: Insufficient evidence or rule violations

```json
{
  "phase": "governance_decision",
  "promotion_request_id": "promo_req_2026_01_13_001",
  "decision": {
    "timestamp": "2026-01-27T10:00:00Z",
    "decision_maker": "automated_approval",
    "decision_type": "approve",
    "rationale": "No blocking objections during 14-day review period. Technical validation passed. Evidence verified.",
    "conditions": []
  },
  "next_phase": "admission"
}
```

---

### 5.6 Phase 5: Admission

**Activities**:
- Add definition to active set
- Compute transcript hash (all evidence + definition + metadata)
- Generate activation record
- Publish to canonical registry
- Seal immutability

**Outputs**:
- GDU definition (now canonical)
- Activation record (ceremony proof)
- Transcript hash (deterministic ceremony fingerprint)
- Publication timestamp

```json
{
  "phase": "admission",
  "promotion_request_id": "promo_req_2026_01_13_001",
  "admission_record": {
    "timestamp": "2026-01-27T11:00:00Z",
    "gdu_definition_id": "language.vocabulary.hypertension",
    "version": "1.0.0",
    "content_hash": "sha256:a1b2c3d4e5f6...",
    "transcript_hash": "sha256:f1e2d3c4b5a6...",
    "activation_id": "activation_hypertension_2026_01_27",
    "immutability_sealed": true
  },
  "publication": {
    "published_to": "gdu_canonical_registry",
    "publication_url": "https://registry.enki.example/language/vocabulary/hypertension",
    "publication_timestamp": "2026-01-27T11:01:00Z"
  },
  "ceremony_complete": true
}
```

**Key Observation**: Ceremony is deterministic, auditable, and produces verifiable proof.

---

## 6. AUTHORITY AND APPROVAL

### 6.1 Who Has Authority?

**Authority is NOT centralized.** It is distributed based on:

| Authority Type | Who | Scope | Precedence |
|----------------|-----|-------|------------|
| **Technical Gatekeeping** | Automated validators | Schema conformance, GDU dependency rules | Highest (mandatory) |
| **Domain Expertise** | Domain experts | Evidence quality, domain-specific validity | High (advisory) |
| **Community Consensus** | Open review participants | General scrutiny, conflict detection | Medium (advisory) |
| **Governance Board** | Elected or appointed board | Final decision on contentious cases | High (binding if established) |
| **Fallback Rules** | SPINE-S1.2 governance | Automated approval if no blocking objections | Medium (procedural) |

### 6.2 Approval Threshold

**Default**: Promotion is approved if:
1. Technical validation passes (mandatory)
2. Evidence meets at least one criterion (mandatory)
3. No blocking objections with counter-evidence after review period (mandatory)
4. Domain expert approval (if domain board exists) (conditional)

**Escalation**: If any of the above fail, escalate to governance board.

### 6.3 Appeals Process

If a promotion is rejected:
1. Nominator receives detailed rejection report
2. Nominator may:
   - Gather additional evidence and re-submit
   - Request governance board review
   - Contest technical validation errors
3. Governance board (if exists) reviews appeal
4. Final decision is binding

---

## 7. FORBIDDEN PATTERNS

### 7.1 Anti-Pattern 1: Voting on Meaning

❌ **Forbidden**:
```
"Let's vote: Does 'literally' mean figuratively?"
→ 51% say no, 49% say yes
→ Promote "no" meaning, reject "yes" meaning
```

✅ **Correct**:
```
Evidence Package 1: "literally" (traditional usage)
- Sources: Dictionaries 1800-2000
- Criterion: Historical stability
→ Promote as language.vocabulary.literally.v1

Evidence Package 2: "literally" (intensifier usage)
- Sources: Modern corpora 2000-2025
- Criterion: Cross-domain usage
→ Promote as language.vocabulary.literally.v2

Both coexist. No vote. Both valid.
```

---

### 7.2 Anti-Pattern 2: Authority Without Evidence

❌ **Forbidden**:
```
"I'm a linguistics professor, trust me, this is the correct meaning."
→ Promote without evidence package
```

✅ **Correct**:
```
Evidence Package:
- Nominator: linguistics_professor_123
- Sources: Peer-reviewed papers, authoritative dictionaries
- Criterion: Authoritative source
- Verification: URLs, citations, timestamps
→ Promote with full evidence trail
```

---

### 7.3 Anti-Pattern 3: Erasure of History

❌ **Forbidden**:
```
"The old meaning is obsolete, delete it and replace with new meaning."
→ term.v1 deleted
→ term.v2 replaces it
```

✅ **Correct**:
```
term.v1 (status: deprecated, superseded_by: term.v2)
term.v2 (status: active, supersedes: term.v1)
Both exist. History preserved.
```

---

### 7.4 Anti-Pattern 4: Context-Specific Promotion

❌ **Forbidden**:
```
"In my company's codebase, 'refactor' means rewrite."
→ Promote as global definition
```

✅ **Correct**:
```
This is context-specific, NOT globally applicable.
→ Remains in LDU-W (local definition)
→ Not promoted to GDU
→ Company can use it locally via LDU
```

---

## 8. PROMOTION METRICS AND TRANSPARENCY

### 8.1 Public Metrics

All promotion ceremonies publish metrics:
- Total nominations
- Approval rate
- Rejection reasons (aggregated)
- Average review duration
- Evidence quality distribution

### 8.2 Ceremony Transparency

All ceremonies are auditable:
- Nomination timestamp
- Review participants
- Evidence sources
- Decision rationale
- Activation record

**Privacy**: Commenter IDs may be pseudonymous, but evidence must be verifiable.

### 8.3 Success Criteria

A promotion ceremony is successful if:
- Deterministic (same inputs → same outputs)
- Auditable (all steps recorded)
- Evidence-based (no opinion-only decisions)
- Conflict-preserving (ambiguity not collapsed)
- Immutable (once admitted, never changed)

---

## 9. IMPLEMENTATION ROADMAP

### 9.1 Phase 1: Tooling (Not Yet Implemented)

**Required Tools**:
- Evidence package validator
- GDU relation existence checker
- Conflict detection analyzer
- Review portal (public interface)
- Activation record generator

### 9.2 Phase 2: Governance (Partially Defined)

**Required Governance**:
- Domain expert registry (who are the experts?)
- Review period policies (14 days? 30 days?)
- Governance board structure (if needed)
- Appeals process details

### 9.3 Phase 3: Infrastructure (Not Yet Implemented)

**Required Infrastructure**:
- LDU-W storage (workable definitions)
- Promotion request queue
- Review collaboration tools
- Publication registry

### 9.4 Phase 4: First Ceremony (Proof of Concept)

**Recommended First Promotion**:
- Term: "hypertension" (medical)
- Evidence: WHO ICD-11, medical literature
- Expected outcome: Clean approval (low controversy)
- Purpose: Validate ceremony process

---

## 10. CROSS-REFERENCE TO BASE60 AND LANGUAGE PACK CEREMONIES

### 10.1 Similarities

| Aspect | Base60/Language Ceremony | Meaning Promotion Ceremony |
|--------|--------------------------|----------------------------|
| **Determinism** | Content hash, transcript hash | Evidence hash, transcript hash |
| **Immutability** | Once admitted, never changed | Once admitted, never changed |
| **Provenance** | All sources tracked | All evidence tracked |
| **Validation** | Schema + namespace checks | Schema + GDU conformance checks |
| **Audit Trail** | Activation record | Activation record |

### 10.2 Differences

| Aspect | Base60/Language Ceremony | Meaning Promotion Ceremony |
|--------|--------------------------|----------------------------|
| **What's Admitted** | Shapes, feature spaces, relation types | Meanings, vocabulary, semantic links |
| **Evidence Required** | Technical specification | Usage evidence, authoritative sources |
| **Conflict Resolution** | Namespace collision = reject | Multiple meanings = promote both |
| **Authority** | Technical correctness | Evidence quality + domain expertise |
| **Review Period** | Minimal (technical only) | Extended (community + experts) |

### 10.3 Governance Continuity

**Shared Principles**:
1. Immutability after admission
2. Deterministic ceremonies
3. Provenance tracking
4. No external dependencies (GDU rule 1.2.1)
5. Separation of concerns (GDU = shapes, LDU = meanings)

**This continuity ensures**: Promotion ceremonies feel like natural extensions of the existing governance model, not a separate system.

---

## 11. EXAMPLES: COMPLETE PROMOTION CEREMONIES

### Example 1: Medical Term ("anemia")

**Phase 1: Nomination**
```json
{
  "promotion_request_id": "promo_req_anemia_001",
  "ldu_w_definition_id": "ldu_w_medical_anemia_001",
  "term": "anemia",
  "nominator": "medical_expert_456",
  "nomination_timestamp": "2026-02-01T08:00:00Z"
}
```

**Phase 2: Technical Validation**
```json
{
  "validation_status": "pass",
  "gdu_conformance": true,
  "namespace_collision": false,
  "content_hash": "sha256:abc123..."
}
```

**Phase 3: Community Review**
```json
{
  "review_period": "14 days",
  "domain_expert_approvals": 3,
  "blocking_objections": 0,
  "evidence_verified": true
}
```

**Phase 4: Governance Decision**
```json
{
  "decision": "approve",
  "decision_maker": "automated_approval",
  "rationale": "No blocking objections, evidence verified"
}
```

**Phase 5: Admission**
```json
{
  "gdu_definition_id": "language.vocabulary.anemia",
  "version": "1.0.0",
  "content_hash": "sha256:abc123...",
  "transcript_hash": "sha256:def456...",
  "activation_id": "activation_anemia_2026_02_15",
  "ceremony_complete": true
}
```

**Result**: `language.vocabulary.anemia` is now canonical.

---

### Example 2: Conflicting Meanings ("crane")

**Scenario**: "crane" (bird) vs "crane" (machine)

**Phase 1-2**: Both nominated separately, both pass technical validation.

**Phase 3**: Review identifies potential collision.

**Conflict Resolution**:
```json
{
  "conflict_type": "homonymy",
  "resolution_strategy": "promote_both_with_distinct_ids",
  "proposed_ids": [
    "language.vocabulary.crane.bird",
    "language.vocabulary.crane.machine"
  ]
}
```

**Phase 4**: Both approved.

**Phase 5**: Both admitted with distinct IDs.

**Result**:
- `language.vocabulary.crane.bird` (canonical)
- `language.vocabulary.crane.machine` (canonical)
- Both coexist, no collision, context determines usage

---

### Example 3: Evolving Slang ("yeet")

**Scenario**: "yeet" (slang for throwing with force) nominated for promotion.

**Evidence Package**:
```json
{
  "criterion": "cross_domain_usage",
  "sources": [
    {
      "corpus": "Social media text 2014-2025",
      "usage_count": 500000,
      "verification_method": "corpus_query"
    },
    {
      "corpus": "News articles 2018-2025",
      "usage_count": 2000,
      "verification_method": "corpus_query"
    }
  ],
  "global_applicability": "Widely used slang term, cross-generational recognition"
}
```

**Review Outcome**: Approved (evidence sufficient for slang category).

**Admission**:
```json
{
  "gdu_definition_id": "language.vocabulary.yeet",
  "version": "1.0.0",
  "category": "slang",
  "temporal_note": "Originated 2014, popularized 2018-2020",
  "status": "active"
}
```

**Key Observation**: Slang CAN be promoted if evidence is sufficient. Not limited to "formal" language.

---

## 12. GOVERNANCE INVARIANTS (REINFORCED)

### 12.1 Immutability
Once promoted, definitions are immutable. Changes require new versions.

### 12.2 Evidence-Based
Promotions require verifiable evidence. Opinions without evidence are not sufficient.

### 12.3 Conflict-Tolerant
Multiple meanings can coexist. Ambiguity is preserved, not collapsed.

### 12.4 Provenance-Tracked
All evidence sources, review participants, and decisions are recorded.

### 12.5 Deterministic
Same evidence + same rules → same outcome (reproducible ceremonies).

---

## 13. BINDING CLAUSES

### 13.1 Authority
This document is **LOCKED** and governs all meaning promotion ceremonies in ENKI.

### 13.2 Precedence
In case of conflict:
1. SPINE-S1.2 governance rules (highest)
2. `docs/03-language-governance-model.md` (semantic contract)
3. This document (promotion procedures)
4. Implementation-specific policies (lowest)

### 13.3 Amendments
Amendments require:
- Formal proposal
- Community review (30 days minimum)
- Governance board approval
- New version number
- Ceremony admission (this document would be re-versioned)

---

## 14. SUMMARY: THE COMPLETE GOVERNANCE FOUNDATION

With this document, the language governance foundation is complete:

| Document | Purpose | Status |
|----------|---------|--------|
| `03-language-governance-model.md` | Defines GDU/LDU separation, authority boundaries, forbidden patterns | LOCKED ✅ |
| `04-language-ingestion-scenarios.md` | Proves the model works with concrete examples | LOCKED ✅ |
| `05-language-promotion-ceremonies.md` | Defines how meanings become canonical | LOCKED ✅ |

**You can now build LDU infrastructure without risking semantic corruption.**

---

## 15. NEXT STEPS

### Option 2: LDU Infrastructure (Now Safe to Build)

With governance complete, you can now build:
- LDU-T storage (raw linguistic data)
- LDU-W validation (GDU-shaped definitions)
- Promotion tooling (ceremony automation)
- Review portal (community interface)

### Option 5: GDU Extension (Additional Vocabularies)

Extend the language pack:
- More scripts (Arabic, Hebrew, Han, etc.)
- More semantic relations (causation, temporal, spatial)
- More pragmatic patterns (indirect speech acts, implicature)

### Option 6: First Promotion Ceremony (Proof of Concept)

Execute a real promotion ceremony:
- Choose a simple term (e.g., "hypertension")
- Assemble evidence package
- Run through all 5 phases
- Generate activation record
- Validate governance model in practice

---

## GLOSSARY

**Promotion**: Process of moving LDU-W definition to GDU via ceremony  
**Evidence Package**: Verifiable sources supporting global applicability  
**Blocking Objection**: Objection with counter-evidence (not just opinion)  
**Domain Tag**: Identifier indicating specialized field (medical, legal, etc.)  
**Diachronic Shift**: Meaning change over time (historical linguistics)  
**Activation Record**: Ceremony proof (immutability sealed)  
**Transcript Hash**: Deterministic hash of entire ceremony (audit fingerprint)  

---

## CHANGE LOG

| Version | Date | Change | Authority |
|---------|------|--------|-----------|
| 1.0.0 | 2026-01-13 | Initial promotion ceremony specification | SPINE-S1.2 |

---

## ACKNOWLEDGMENTS

This document completes the governance triad established during language pack development (2026-01-13):
1. Governance model (shapes vs meanings)
2. Ingestion scenarios (proof of concept)
3. Promotion ceremonies (LDU-W → GDU bridge)

**Meaning without guessing. Authority without centralization. Computation without interpretation. Governance without paralysis.**

---

**END OF DOCUMENT**

**Status**: LOCKED  
**Previous Document**: `docs/04-language-ingestion-scenarios.md`  
**Related Documents**: `docs/03-language-governance-model.md`, `libraries/language/pack.json`, `scripts/governance/run_admission_ceremony.py`

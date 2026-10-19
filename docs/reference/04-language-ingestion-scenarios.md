# Language Ingestion Scenarios

**Version:** 1.0.0  
**Status:** LOCKED  
**Date:** 2026-01-13  
**Supersedes:** None  
**Authority:** SPINE-S1.2  
**Governance Contract:** `docs/03-language-governance-model.md`  

---

## EXECUTIVE SUMMARY

This document provides **concrete ingestion scenarios** that prove the language governance model works in practice.

Each scenario demonstrates:
- **Ambiguity preservation** (no premature collapse)
- **GDU/LDU separation** (shapes vs meanings)
- **Semantic mapping** (relationships, not text)
- **Provenance tracking** (auditable origin)

**Three Required Scenarios**:
1. **Book Sentence** ("sick car") — Proves ambiguity preservation
2. **Speech → Phonology** — Proves modal independence
3. **API Event → Pragmatics** — Proves agent-readiness

---

## SCENARIO 1: BOOK SENTENCE INGESTION

### 1.1 Input

**Raw Text**: `"His car was sick."`  
**Source**: Book "Example Novel", page 42  
**Context**: Character describing vehicle condition (context ambiguous)  

### 1.2 Pipeline Step-by-Step

#### Step 1: Raw Ingestion (Entry to LDU-T)

The text enters the system **exactly as written**, with no interpretation.

```json
{
  "id": "ldu_t_book_001_sentence_42",
  "universe": "LDU-T",
  "source": {
    "type": "book",
    "title": "Example Novel",
    "author": "Jane Doe",
    "page": 42,
    "isbn": "978-3-16-148410-0"
  },
  "text": "His car was sick.",
  "ambiguity_preserved": true,
  "resolution_status": "unresolved",
  "provenance": {
    "ingestion_timestamp": "2026-01-13T16:00:00Z",
    "ingestion_method": "book_parser_v1.2.0",
    "ingestion_actor": "automated_ingest_service"
  },
  "metadata": {
    "language_detected": "en",
    "sentence_structure": "subject-verb-complement",
    "tokens": ["His", "car", "was", "sick", "."]
  }
}
```

**Critical Observation**: No meaning assigned. No interpretation made. Text is preserved verbatim.

---

#### Step 2: Ambiguity Enumeration

The system identifies **terms with multiple possible meanings** and enumerates semantic candidates.

```json
{
  "id": "ldu_t_book_001_sentence_42",
  "text": "His car was sick.",
  "ambiguity_analysis": {
    "ambiguous_terms": [
      {
        "term": "sick",
        "position": 4,
        "candidate_meanings": [
          {
            "candidate_id": "sick_literal_illness",
            "type": "literal",
            "description": "physically ill or unwell",
            "maps_to_gdu": "language.semantics.synonymy",
            "gdu_relation": {
              "relation_type": "language.semantics.synonymy",
              "synonym_of": "ill"
            },
            "confidence": null,
            "evidence": null
          },
          {
            "candidate_id": "sick_metaphor_damaged",
            "type": "metaphor",
            "description": "broken, malfunctioning, damaged",
            "maps_to_gdu": "language.semantics.synonymy",
            "gdu_relation": {
              "relation_type": "language.semantics.synonymy",
              "synonym_of": "damaged"
            },
            "confidence": null,
            "evidence": null
          },
          {
            "candidate_id": "sick_slang_positive",
            "type": "slang",
            "description": "impressive, cool, excellent",
            "maps_to_gdu": "language.semantics.polysemy",
            "gdu_relation": {
              "relation_type": "language.semantics.polysemy",
              "note": "slang usage distinct from literal meaning"
            },
            "confidence": null,
            "evidence": null
          }
        ],
        "ambiguity_type": "polysemy",
        "resolution_required": true
      }
    ]
  },
  "resolution": null
}
```

**Critical Observation**: All candidates preserved. No single meaning chosen. Confidence = null (no guessing).

---

#### Step 3: GDU Shape Validation

The system validates that all semantic candidates **map to valid GDU relation types**.

```json
{
  "validation_report": {
    "timestamp": "2026-01-13T16:00:01Z",
    "validator": "gdu_shape_validator_v1.0.0",
    "status": "valid",
    "checks": [
      {
        "check_type": "gdu_relation_existence",
        "target": "language.semantics.synonymy",
        "result": "pass",
        "evidence": {
          "gdu_pack": "language",
          "gdu_version": "0.1.0",
          "definition_id": "language.semantics",
          "relation_confirmed": true
        }
      },
      {
        "check_type": "gdu_relation_existence",
        "target": "language.semantics.polysemy",
        "result": "pass",
        "evidence": {
          "gdu_pack": "language",
          "gdu_version": "0.1.0",
          "definition_id": "language.semantics",
          "relation_confirmed": true
        }
      },
      {
        "check_type": "schema_conformance",
        "result": "pass",
        "schema": "ldu_t_entry.schema.json",
        "validation_errors": []
      }
    ]
  }
}
```

**Critical Observation**: Candidates are valid because they reference GDU relation types. System can compute with them.

---

#### Step 4: Contextual Clues (Optional Enrichment)

If additional context is available, it can be added **without collapsing ambiguity**.

```json
{
  "id": "ldu_t_book_001_sentence_42",
  "text": "His car was sick.",
  "contextual_clues": {
    "preceding_sentences": [
      "He turned the key. Nothing happened.",
      "The engine made a grinding noise."
    ],
    "following_sentences": [
      "He called a mechanic.",
      "The repair would cost two thousand dollars."
    ],
    "speaker_intent_hints": [
      {
        "hint_type": "mechanical_context",
        "evidence": ["engine", "grinding noise", "mechanic", "repair"],
        "favors_candidate": "sick_metaphor_damaged",
        "confidence": "contextual_support",
        "does_not_eliminate_other_candidates": true
      }
    ]
  },
  "resolution": null
}
```

**Critical Observation**: Context provides hints but does NOT force resolution. All candidates remain valid.

---

#### Step 5: LDU-W Candidate Creation

If a system needs to **compute with a specific interpretation**, it creates an LDU-W entry.

```json
{
  "id": "ldu_w_book_001_interpretation_damaged",
  "universe": "LDU-W",
  "source_ldu_t": "ldu_t_book_001_sentence_42",
  "interpretation": {
    "term": "sick",
    "chosen_candidate": "sick_metaphor_damaged",
    "semantic_relations": [
      {
        "relation_type": "language.semantics.synonymy",
        "source_term": "sick",
        "target_term": "damaged",
        "context": "vehicle_malfunction"
      }
    ]
  },
  "gdu_shape_conformance": true,
  "validation": {
    "gdu_relation_types_used": ["language.semantics.synonymy"],
    "schema_valid": true,
    "references_gdu_only": true
  },
  "evidence": {
    "contextual_clues": ["engine", "grinding noise", "mechanic", "repair"],
    "confidence": "high_contextual_support",
    "alternative_interpretations_preserved": true
  },
  "status": "workable",
  "promotion_candidate": false,
  "reason_not_promoted": "context-specific interpretation, not globally applicable"
}
```

**Critical Observation**: LDU-W entry is **one interpretation**, not the only interpretation. Original LDU-T entry unchanged.

---

### 1.3 Key Proofs

✅ **Ambiguity Preserved**: Original text never modified  
✅ **Multiple Interpretations Coexist**: LDU-T has 3 candidates, LDU-W has 1 chosen  
✅ **Provenance Tracked**: Every step has timestamp, actor, method  
✅ **GDU Shapes Validated**: All semantic relations reference GDU  
✅ **No Premature Collapse**: Resolution = null until explicit LDU-W creation  

---

## SCENARIO 2: SPEECH → PHONOLOGY → SEMANTICS

### 2.1 Input

**Audio Transcription**: `"The knight rode through the night."`  
**Source**: Speech recording, speaker ID "speaker_001"  
**Context**: Spoken sentence with homophone ambiguity  

### 2.2 Pipeline Step-by-Step

#### Step 1: Transcription to LDU-T

```json
{
  "id": "ldu_t_speech_001_utterance_15",
  "universe": "LDU-T",
  "source": {
    "type": "speech",
    "recording_id": "recording_2026_01_13_001",
    "speaker_id": "speaker_001",
    "timestamp_start": "2026-01-13T14:30:05.200Z",
    "timestamp_end": "2026-01-13T14:30:07.800Z",
    "duration_ms": 2600
  },
  "transcription": {
    "text": "The knight rode through the night.",
    "transcription_confidence": 0.92,
    "transcription_method": "speech_to_text_v2.1.0"
  },
  "phonological_features_raw": {
    "note": "Extracted without semantic interpretation",
    "features": [
      {
        "word_index": 1,
        "word": "knight",
        "ipa_transcription": "/naɪt/",
        "phonemes": [
          {"symbol": "n", "type": "consonant", "features": ["nasal", "alveolar", "voiced"]},
          {"symbol": "aɪ", "type": "vowel", "features": ["diphthong", "front_to_high"]},
          {"symbol": "t", "type": "consonant", "features": ["stop", "alveolar", "voiceless"]}
        ],
        "stress_pattern": "primary",
        "syllable_count": 1
      },
      {
        "word_index": 4,
        "word": "night",
        "ipa_transcription": "/naɪt/",
        "phonemes": [
          {"symbol": "n", "type": "consonant", "features": ["nasal", "alveolar", "voiced"]},
          {"symbol": "aɪ", "type": "vowel", "features": ["diphthong", "front_to_high"]},
          {"symbol": "t", "type": "consonant", "features": ["stop", "alveolar", "voiceless"]}
        ],
        "stress_pattern": "primary",
        "syllable_count": 1
      }
    ]
  },
  "homophone_detected": true,
  "ambiguity_preserved": true,
  "resolution": null
}
```

**Critical Observation**: Phonological features extracted **without deciding what words mean**. Homophones identified but not resolved.

---

#### Step 2: Phonological Feature Validation Against GDU

```json
{
  "validation_report": {
    "timestamp": "2026-01-13T14:30:08Z",
    "validator": "phonology_validator_v1.0.0",
    "status": "valid",
    "checks": [
      {
        "check_type": "phoneme_feature_validation",
        "phoneme": "n",
        "features": ["nasal", "alveolar", "voiced"],
        "gdu_reference": "language.phonology",
        "result": "pass",
        "evidence": {
          "gdu_definition": "language.phonology",
          "manner": "nasals",
          "place": "alveolar",
          "voicing": "voiced",
          "feature_space_membership": true
        }
      },
      {
        "check_type": "phoneme_feature_validation",
        "phoneme": "aɪ",
        "features": ["diphthong", "front_to_high"],
        "gdu_reference": "language.phonology",
        "result": "pass",
        "evidence": {
          "gdu_definition": "language.phonology",
          "vowels_total": 8,
          "suprasegmentals": ["stress", "tone", "length", "nasalization"],
          "feature_space_membership": true
        }
      }
    ]
  }
}
```

**Critical Observation**: Phonological features validated against GDU feature space. No audio files needed. Modal independence proven.

---

#### Step 3: Semantic Candidate Mapping

```json
{
  "id": "ldu_t_speech_001_utterance_15",
  "ambiguity_analysis": {
    "homophone_pairs": [
      {
        "phonetic_form": "/naɪt/",
        "word_candidates": [
          {
            "spelling": "knight",
            "semantic_relations": [
              {
                "relation_type": "language.semantics.hypernymy",
                "parent": "warrior",
                "parent_gdu_conformance": true
              },
              {
                "relation_type": "language.semantics.hypernymy",
                "parent": "historical_role",
                "parent_gdu_conformance": true
              }
            ]
          },
          {
            "spelling": "night",
            "semantic_relations": [
              {
                "relation_type": "language.semantics.antonymy",
                "opposite": "day",
                "opposite_gdu_conformance": true
              },
              {
                "relation_type": "language.semantics.hypernymy",
                "parent": "time_period",
                "parent_gdu_conformance": true
              }
            ]
          }
        ],
        "disambiguation_required": true,
        "resolution": null
      }
    ]
  }
}
```

**Critical Observation**: Semantic candidates mapped to GDU relation types. Both homophones valid. No single choice forced.

---

#### Step 4: Context-Based Resolution Hint (Optional)

```json
{
  "id": "ldu_t_speech_001_utterance_15",
  "contextual_analysis": {
    "syntactic_structure": {
      "subject": {
        "position": 1,
        "candidates": ["knight", "night"],
        "expected_category": "noun",
        "semantic_constraint": "agent_capable_of_riding"
      },
      "verb": {
        "position": 2,
        "word": "rode",
        "requires_animate_subject": true
      }
    },
    "semantic_constraint_check": {
      "candidate": "knight",
      "satisfies_animate_subject": true,
      "favored_by_syntax": true
    },
    "resolution_hint": {
      "favored_candidate": "knight",
      "confidence": "high_syntactic_support",
      "alternative_preserved": true
    }
  },
  "resolution": null
}
```

**Critical Observation**: Syntactic constraints provide hints but do NOT eliminate alternatives. Ambiguity still preserved in LDU-T.

---

### 2.3 Key Proofs

✅ **Modal Independence**: Phonological features extracted without audio files  
✅ **GDU Feature Space Validation**: All phonemes validated against `language.phonology`  
✅ **Homophone Preservation**: Both "knight" and "night" remain valid  
✅ **Semantic Mapping**: Candidates reference GDU relation types (hypernymy, antonymy)  
✅ **No Forced Resolution**: Context provides hints, not decisions  

---

## SCENARIO 3: API EVENT → PRAGMATICS

### 3.1 Input

**API Request**:
```http
POST /admin/disable-account HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGc...
Content-Type: application/json

{
  "account_id": "user_12345",
  "message": "Please disable this account immediately",
  "reason": "policy_violation",
  "requester_role": "admin"
}
```

### 3.2 Pipeline Step-by-Step

#### Step 1: Event Ingestion to LDU-T

```json
{
  "id": "ldu_t_api_event_001",
  "universe": "LDU-T",
  "source": {
    "type": "api_event",
    "endpoint": "/admin/disable-account",
    "method": "POST",
    "timestamp": "2026-01-13T15:45:00Z",
    "requester_id": "admin_user_789",
    "requester_role": "admin"
  },
  "event_data": {
    "account_id": "user_12345",
    "message": "Please disable this account immediately",
    "reason": "policy_violation"
  },
  "linguistic_content": {
    "text": "Please disable this account immediately",
    "modality": "written_command",
    "context": "administrative_action"
  },
  "ambiguity_preserved": true,
  "resolution": null
}
```

**Critical Observation**: Event ingested as-is. Message text preserved verbatim. No action taken yet.

---

#### Step 2: Semantic Analysis

```json
{
  "id": "ldu_t_api_event_001",
  "semantic_analysis": {
    "text": "Please disable this account immediately",
    "semantic_components": [
      {
        "component": "disable",
        "semantic_relations": [
          {
            "relation_type": "language.semantics.antonymy",
            "opposite": "enable",
            "gdu_reference": "language.semantics"
          },
          {
            "relation_type": "language.semantics.hypernymy",
            "parent": "state_change_action",
            "gdu_reference": "language.semantics"
          }
        ]
      },
      {
        "component": "immediately",
        "semantic_relations": [
          {
            "relation_type": "language.semantics.hypernymy",
            "parent": "temporal_modifier",
            "gdu_reference": "language.semantics"
          }
        ],
        "pragmatic_signal": "urgency"
      }
    ]
  }
}
```

**Critical Observation**: Semantic content analyzed. Relations mapped to GDU. No action decided yet.

---

#### Step 3: Pragmatic Analysis

```json
{
  "id": "ldu_t_api_event_001",
  "pragmatic_analysis": {
    "speech_act_classification": {
      "primary_act": "directive",
      "gdu_reference": "language.pragmatics",
      "gdu_definition": {
        "speech_act": "directive",
        "definition": "attempting to get addressee to do something"
      },
      "evidence": [
        "imperative_verb: disable",
        "temporal_urgency: immediately",
        "authority_context: admin_role"
      ]
    },
    "politeness_strategy": {
      "marker": "Please",
      "strategy_type": "positive_face",
      "gdu_reference": "language.pragmatics",
      "effect": "softens_directive"
    },
    "contextual_factors": {
      "authority_level": "high",
      "requester_role": "admin",
      "endpoint_authorization": "required",
      "pragmatic_force": "command_with_authority"
    }
  }
}
```

**Critical Observation**: Pragmatic intent classified using GDU speech acts. Context matters but doesn't change semantic meaning.

---

#### Step 4: Semantic vs Pragmatic Separation

```json
{
  "id": "ldu_t_api_event_001",
  "meaning_analysis": {
    "semantic_meaning": {
      "what_is_said": "A request to change account state to disabled, with urgency",
      "semantic_relations": [
        "disable ← antonym → enable",
        "disable ← hypernym → state_change_action",
        "immediately ← hypernym → temporal_modifier"
      ]
    },
    "pragmatic_meaning": {
      "what_is_being_done": "Issuing a command with administrative authority",
      "speech_act": "directive",
      "authority_context": "admin",
      "expected_response": "immediate_compliance",
      "politeness_level": "formal_but_direct"
    },
    "separation_proof": {
      "same_semantics_different_pragmatics": [
        {
          "text": "Please disable this account immediately",
          "context": "admin",
          "pragmatics": "command",
          "expected_action": "execute"
        },
        {
          "text": "Please disable this account immediately",
          "context": "unauthorized_user",
          "pragmatics": "request_without_authority",
          "expected_action": "reject"
        }
      ],
      "proof": "Same words, same semantics, different pragmatic force based on context"
    }
  }
}
```

**Critical Observation**: Semantics = what is said. Pragmatics = what is done. Context determines action, not wording.

---

#### Step 5: LDU-W Action Plan

```json
{
  "id": "ldu_w_api_action_001",
  "universe": "LDU-W",
  "source_ldu_t": "ldu_t_api_event_001",
  "action_plan": {
    "action_type": "account_state_change",
    "target_state": "disabled",
    "authorization_validated": true,
    "requester_role": "admin",
    "pragmatic_classification": "directive",
    "semantic_validation": {
      "gdu_relations_used": [
        "language.semantics.antonymy",
        "language.semantics.hypernymy"
      ],
      "gdu_speech_act": "language.pragmatics (directive)"
    }
  },
  "execution_policy": {
    "if_authorized": "execute_immediately",
    "if_unauthorized": "reject_with_403",
    "audit_required": true,
    "provenance_preserved": true
  },
  "gdu_shape_conformance": true,
  "status": "workable"
}
```

**Critical Observation**: Action plan created only after validation. Authorization checked. Pragmatics determines execution, not just text.

---

### 3.3 Key Proofs

✅ **Agent-Ready**: System understands intent (directive) not just text  
✅ **Semantic/Pragmatic Separation**: Same words = different actions based on context  
✅ **GDU Speech Acts**: Classifications reference `language.pragmatics`  
✅ **Authority Matters**: Pragmatic force depends on requester role  
✅ **Auditable**: Every step tracked with provenance  

---

## CROSS-SCENARIO INVARIANTS

### Invariant 1: Ambiguity Preservation

**All scenarios**: Original input never modified. Multiple interpretations coexist.

### Invariant 2: GDU Shape Validation

**All scenarios**: Every semantic/pragmatic/phonological claim validated against GDU definitions.

### Invariant 3: Provenance Tracking

**All scenarios**: Every entry has timestamp, method, actor, source.

### Invariant 4: No Premature Collapse

**All scenarios**: Resolution = null until explicit LDU-W entry created.

### Invariant 5: Separation of Concerns

**All scenarios**: GDU = shapes. LDU-T = raw data. LDU-W = validated interpretations.

---

## IMPLEMENTATION NOTES

### Note 1: These Are Conceptual Pipelines

These scenarios describe **how the system should think**, not exact implementation details.

### Note 2: LDU Storage Not Yet Implemented

LDU-T and LDU-W storage layers do not exist yet. These scenarios define **what they must do**.

### Note 3: Validation Tooling Required

Before building LDU infrastructure, validation tools must exist:
- GDU relation existence checker
- Schema conformance validator
- Dependency analyzer

### Note 4: Promotion Not Covered Here

These scenarios do not include promotion ceremonies. See `docs/03-language-governance-model.md` Section 5.

---

## NEXT STEPS

### Option 4: Promotion Ceremonies (Conceptual)

Define how LDU-W definitions are reviewed and promoted to GDU.

### Option 2: LDU Infrastructure (Implementation)

Build storage, validation, and mapping services for LDU-T and LDU-W.

### Option 5: GDU Extension (Additional Vocabularies)

Extend language pack with more scripts, relations, pragmatic patterns.

**Recommendation**: Option 4 next (promotion ceremonies) to complete governance before infrastructure.

---

## REFERENCE IMPLEMENTATION STATUS

**GDU Language Pack**: Admitted (v0.1.0)  
**LDU-T Storage**: Not implemented  
**LDU-W Validation**: Not implemented  
**Promotion Ceremonies**: Not implemented  
**Ingestion Pipelines**: Not implemented  

**Current Phase**: Governance specification complete. Ready for infrastructure design.

---

## GLOSSARY

**Scenario**: Concrete example showing pipeline from input → LDU-T → validation → LDU-W  
**Modal Independence**: Ability to work with features (phonology) without raw data (audio)  
**Homophone**: Words with same pronunciation, different meanings (knight/night)  
**Speech Act**: Pragmatic classification (directive, assertive, etc.)  
**Pragmatic Force**: What action is signaled by context, not just words  
**Semantic Candidate**: Possible meaning mapped to GDU relation type  
**Resolution Hint**: Contextual evidence favoring one candidate (without eliminating others)  

---

## CHANGE LOG

| Version | Date | Change | Authority |
|---------|------|--------|-----------|
| 1.0.0 | 2026-01-13 | Initial ingestion scenarios | SPINE-S1.2 |

---

## ACKNOWLEDGMENTS

These scenarios formalize the ingestion philosophy established during language governance model development (2026-01-13).

---

**END OF DOCUMENT**

**Status**: LOCKED  
**Previous Document**: `docs/03-language-governance-model.md`  
**Related Documents**: `docs/LANGUAGE_PACK_SCHEMA_REFERENCE.md`, `libraries/language/pack.json`

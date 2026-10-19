# Definition Registry & Resolution Model

**Status:** Authoritative Specification  
**Governance:** Semantic Integrity  
**Audience:** Core developers, auditors, security reviewers

---

## Purpose

This document defines how ENKI:

- Prevents semantic drift
- Resolves definition meaning at scale
- Handles duplicate human terminology safely
- Enforces global vs local meaning authority

---

## Canonical Addressing

In ENKI, **meaning is addressed exclusively by:**

```
(id, version)
```

Human-readable labels are:
- Optional
- Non-authoritative
- Never used for resolution

---

## Duplicate Words Are Allowed

Multiple definitions may use the same human term:

- "account"
- "case"
- "alert"
- "device"

This is **not a conflict**.

Example:
- `finance.account`
- `identity.account`
- `audit.alert`
- `medical.alert`

These are distinct meanings by design.

---

## What Constitutes a Conflict

A conflict exists only when:

- Two definitions claim to represent the **same canonical meaning**
- Resolution is required at a system boundary
- No explicit authority is declared

Conflicts are semantic, not lexical.

---

## Global Definition Registry

ENKI maintains a **Global Definition Registry** that records:

- Canonical definition IDs
- Namespace ownership
- Supersession relationships
- Deprecation notices

### Registry Properties

- Append-only
- Cryptographically linked
- Auditable
- Never rewritten

The registry does NOT:
- Store data
- Execute logic
- Interpret meaning

It records **commitments of meaning**.

---

## Local vs Global Definitions

### Global Definitions
- Chain-approved
- Immutable
- Universally authoritative

### Local Definitions
- Node-scoped
- Temporarily permitted
- Must resolve at checkpoints

Local definitions allow innovation without corrupting global meaning.

---

## Forced Resolution Checkpoints

ENKI requires definition alignment at:

- Storage persistence
- Cross-node communication
- Audit emission
- Export operations

If a local definition conflicts with global meaning:
- ENKI halts
- Resolution is required
- No silent substitution occurs

---

## Resolution Rules (Deterministic)

1. Resolution is by exact `id`
2. Version selection is explicit
3. Highest-version fallback is allowed **only if declared**
4. Label similarity is ignored
5. Missing authority results in rejection

---

## Supersession Model

Definitions may supersede prior definitions:

- Supersession is explicit
- History remains intact
- Both meanings remain auditable

Supersession never mutates the past.

---

## Security Implications

This model prevents:
- Semantic poisoning
- Slow meaning drift
- Reconstruction attacks via repeated queries
- Label-based ambiguity

Meaning attacks become **visible, discrete events**.

---

## Summary

- Meaning is resolved by (`id`, `version`)
- Words do not confer authority
- Global registry anchors truth
- Local meaning is allowed, but temporary
- All resolution is explicit

**ENKI treats meaning as a first-class security boundary.**

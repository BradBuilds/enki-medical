# Update Bundles & Pack Activation

**Status:** Authoritative Specification  
**Governance:** Forward-Only  
**Audience:** Security, operations, compliance

---

## Purpose

This document defines ENKI's update model for:

- Definition packs
- System behavior
- Validation rules

ENKI explicitly rejects rollback-based update strategies.

---

## Core Update Principle

> **ENKI never rolls back state.  
> ENKI only appends new signed truth.**

History is immutable. Corrections are additive.

---

## Update Bundle Definition

An update bundle contains:

- One or more definition packs
- Pack manifests
- Cryptographic signatures
- Optional registry updates

Bundles are:
- Verified offline
- Applied locally
- Activated explicitly

---

## Verification Phase (No Authority Required)

Before activation:
- All signatures are verified
- Hashes are checked
- Dependencies are validated

Verification does NOT modify system state.

---

## Activation Phase (Human Presence Required)

Activation requires:

- Watch-backed cryptographic key
- Physical proximity to node
- Explicit approval window

Activation is:
- Time-bounded
- Scope-limited
- Audited

---

## Append-Only Activation Event

Successful activation emits a chain event recording:

- Operator identity
- Key identifier (not secret)
- Proximity proof
- Activated pack IDs + versions
- Artifact hashes
- Approval window

This event becomes part of the immutable audit chain.

---

## No Rollback Policy

ENKI does NOT support:
- State rollback
- Definition removal
- History rewriting

If an update is incorrect:
- A new update supersedes it
- Supersession is explicit
- Past meaning remains visible

---

## Failure Handling

If activation fails:
- No partial state is committed
- No packs are activated
- No history is altered

ENKI fails closed.

---

## Enterprise Extensions

Optional enterprise configurations may require:
- Dual human presence
- Multi-key ceremonies
- Staggered activation windows

These do not alter core update principles.

---

## Summary

- Updates are verified, then activated
- Activation requires human presence
- All changes are append-only
- Rollback does not exist
- Truth remains auditable forever

**ENKI treats updates as truth commitments, not configuration changes.**

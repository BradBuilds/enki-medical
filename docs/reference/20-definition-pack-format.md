# ENKI Definition Pack Format

**Status:** Authoritative Specification  
**Governance:** Definition-First  
**Mutation Policy:** Append-Only  
**Audience:** Core developers, auditors, integrators

---

## Purpose

This document defines how ENKI stores, validates, and loads **large-scale definition sets** using **definition packs**.

Definition packs are the only supported mechanism for grouping, distributing, and activating definitions at scale.  
Flat or ad-hoc definition loading is explicitly prohibited.

---

## Core Principle

> **ENKI does not load directories.  
> ENKI loads signed definition packs.**

All definitions are:
- Individually schema-validated
- Addressed by canonical (`id`, `version`)
- Activated only through an explicit pack manifest
- Governed by append-only chain events

---

## Definition Pack Structure

A definition pack is a directory or archive with the following structure:

```
<pack-name>/
  pack.json
  defs/
    <definition-id>__<version>.json
    <definition-id>__<version>.json
```

### Required Components

| Component | Required | Description |
|---------|----------|-------------|
| `pack.json` | ✅ Yes | Pack manifest (entry point) |
| `defs/` | ✅ Yes | Definition files |
| Signatures | ✅ Yes (for activation) | Cryptographic validation |

---

## Definition Files

Each file in `defs/` MUST:

- Validate against `schemas/definition.schema.json`
- Use **only canonical fields**:
  - `id`
  - `type`
  - `version`
  - `content`
- Be immutable once published

### Filename Convention (Deterministic, Non-Authoritative)

```
<id>__<version>.json
```

Example:

```
audit.event.alert_triggered__1.0.0.json
```

**Rule:**  
Filenames are for human navigation only.  
Canonical identity is derived from file contents.

---

## Pack Manifest (`pack.json`)

The pack manifest is the **sole authority** for pack loading.

It declares:
- Which definitions belong to the pack
- Which versions are included
- Which other packs or definitions are required
- Hashes used for integrity verification

### Conceptual Manifest Responsibilities

The manifest MUST enable ENKI to:

1. Verify pack integrity before loading
2. Validate all definitions deterministically
3. Resolve dependencies explicitly
4. Reject partial or ambiguous packs

**ENKI will never infer pack contents by directory scanning.**

---

## Dependency Declaration

Packs may declare dependencies on:

- Other packs
- Specific definition IDs
- Minimum versions

Dependencies are:
- Explicit
- Non-optional
- Validated at load time

If dependencies cannot be satisfied, **pack activation is rejected**.

---

## Immutability Rules

Once a definition version is published:

- ❌ It MUST NOT be modified
- ❌ It MUST NOT be deleted
- ❌ It MUST NOT be overridden silently

Corrections are made by:
- Publishing a new version
- Appending a superseding chain event
- Preserving historical meaning

---

## Scale Guarantees

This model supports:

- Tens of thousands of definitions
- Deterministic loading time
- O(1) definition lookup by `id`
- No semantic ambiguity at runtime

---

## Enforcement

Pack loader enforces:

- Schema validation on every definition
- Hash verification for every file
- Manifest completeness
- Dependency satisfaction

Failure at any step results in **fail-closed rejection**.

---

## Summary

- Definitions live in packs
- Packs are loaded via manifests
- Manifests are verified, not inferred
- Definitions are immutable
- Scale does not introduce ambiguity

**Authority is explicit. Meaning is preserved.**

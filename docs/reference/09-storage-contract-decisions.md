# Storage Contract Decision Sheet

**Status:** LOCKED  
**Version:** 1.0  
**Date:** 2025-12-31  
**Authority:** Phase 1 Governance Lock  
**Purpose:** Immutable architectural choices for ENKI Storage Contract

---

## Purpose

This document locks all ambiguous design choices for the ENKI Storage Contract. These decisions are required for determinism, interoperability, and cross-implementation verification. Once marked LOCKED, these choices are immutable for Phase 1.

**What This Document Is:**
- A decision lock for contract-level requirements
- The foundation for the Storage Contract Specification
- A compatibility guarantee across implementations

**What This Document Is NOT:**
- Implementation guidance (SQL schemas, indexes, drivers)
- Performance tuning recommendations
- Operational policies (backup, scaling, monitoring)

---

## LOCKED DECISIONS

### 1. Hash Algorithm
**Decision:** MUST use SHA-256  
**Rationale:** Universal support, stable, deterministic across implementations  
**Future:** MAY support additional algorithms with explicit `hash_alg` field, but SHA-256 is baseline

### 2. JSON Canonicalization
**Decision:** MUST use RFC 8785 (JSON Canonicalization Scheme)  
**Rationale:** Standardized, deterministic, interoperable  
**Application:** All CID computation for JSON-based records  
**Reference:** https://www.rfc-editor.org/rfc/rfc8785.html

### 3. Signature Algorithm
**Decision:** SHOULD support cryptographic signatures on checkpoints  
**Baseline:** If signatures enabled, MUST support Ed25519  
**Rationale:** Modern, compact, fast, widely supported  
**Future:** MAY support additional schemes with explicit `sig_alg` field

### 4. CID Excluded Fields
**Decision:** CID computation MUST exclude:
- `rid` (storage-assigned record ID)
- `commit_time` (storage-assigned timestamp)
- `receipt_id` (transaction receipt reference)
- `chain_hash` (proofchain metadata)
- Any storage-specific metadata fields

**Rationale:** CID represents content identity, not storage lifecycle

**Encoding:** Canonical encoding is lowercase hexadecimal; implementations MAY provide Base-60 encoding as alternate representation

### 4a. Receipt Digest Core
**Decision:** Receipt digest MUST include:
- `txid`
- `tenant_id`
- `pack_reference` (pack_id + version)
- `accepted_records` (array of `{cid, accept_index}` only)
- `rejected_items` (array of `{input_hash, error_codes, reason?}`)
- `outcome`

**Decision:** Receipt digest MUST exclude:
- `commit_time` (enables cross-node determinism)
- `rid` values in accepted_records (storage-assigned, informational)
- `chain_hash`, `previous_chain_hash` (computed after digest)
- Signatures or post-commit metadata

**Rationale:** Receipt digest must prove "what was submitted under which rules and what happened" without node-specific timing. Including pack_reference prevents validation rule substitution attacks.

### 5. Tenant Model
**Tenant ID Format:** Canonical string identifier; MAY be Base-60 ID  
**Isolation:** MUST enforce tenant isolation at query/contract level  
**Physical vs Logical:** Implementation-defined (separate DBs, schemas, or filtered queries)  
**Cross-Tenant References:** FORBIDDEN in Phase 1

**Rationale:** Security boundary is required; implementation strategy is flexible

### 6. Transaction Ordering
**Decision:** RID MUST provide strict total ordering of all records
**Mechanism:** Each accepted record MUST have an `accept_index` (0-based position within transaction)
**Rationale:** RID is authoritative for ordering; commit_time is informational (may have clock skew/restarts)

### 7. Path Canonicalization
**Decision:** File paths MUST be canonicalized as:
- Separator: always `/` (forward slash)
- Unicode: NFC (Canonical Composition)
- Case: treat as case-sensitive (storage preserves exact case)
- Relativity: paths are relative to workspace root
- Forbidden: `..` (parent directory traversal)

**Rationale:** Cross-platform determinism and security

### 8. Record Type Catalog
**Core Record Types (Phase 1 v1.0.0):**
- `Assertion` (validated truth claims)
- `AuditEvent` (system history)
- `FileArtifact` (content-addressed file)
- `FileLocator` (path → artifact binding)
- `FolderSnapshot` (manifest-based folder state)
- `Receipt` (transaction outcome)
- `Checkpoint` (proofchain summary)

**Future Extensions:** MAY add Claim, Conflict, or other record types with explicit versioning

**Phase 1 Exclusions:** Claim and Conflict records intentionally deferred to maintain scope clarity

### 9. Batch Size & Timeout Limits
**Decision:** Implementation MAY impose limits  
**Requirement:** MUST return explicit error codes when limits exceeded  
**Rationale:** Operational constraints vary; contract requires explicit failure modes

### 10. Checkpoint Frequency
**Decision:** MUST support checkpoints; frequency is implementation-defined  
**Requirement:** Checkpoints MUST be monotonic and cover contiguous receipt ranges  
**Rationale:** Operational policy varies; contract requires correctness guarantees

### 11. File Size Limits
**Decision:** Implementation MAY impose limits  
**Requirement:** MUST reject with explicit error code if artifact exceeds limit  
**Rationale:** Storage constraints vary; contract requires explicit rejection

### 11a. Verifier Role Separation
**Decision:** Storage stores artifacts/snapshots; verification against filesystem is a separate Verifier role
**Storage Responsibilities:** Store FileArtifact, FileLocator, FolderSnapshot records; provide retrieval queries
**Verifier Responsibilities:** Read filesystem, compute artifact_cid from bytes, compare to stored manifests
**Rationale:** Storage implementations may be remote or service-based; requiring filesystem access couples storage to deployment model

### 12. Snapshot Triggers
**Decision:** Implementation-defined (manual, automatic, policy-driven)  
**Requirement:** MUST support explicit snapshot creation via storage interface  
**Rationale:** Workflow flexibility; contract requires capability

---

## NON-DECISIONS (Implementation Freedom)

The following are explicitly NOT locked by this decision sheet:

- Database technology (PostgreSQL is selected for ENKI Node, but contract is DB-agnostic)
- Table schemas, indexes, or query optimization strategies
- Connection pooling, caching, or performance tuning
- Backup, replication, or disaster recovery mechanisms
- Monitoring, logging, or observability tools
- API endpoint design (Phase 4)
- Serialization format for network transmission (Phase 5)

---

## DECISION AUTHORITY

**Locked By:** Phase 1 Storage Contract Specification Process  
**Date:** 2025-12-31  
**Status:** IMMUTABLE for Phase 1  
**Change Process:** Requires governance decision + new phase + version increment

---

## COMPATIBILITY GUARANTEE

Any implementation conforming to these decisions and the Storage Contract Specification (10-storage-contract-spec.md) MUST:
- Produce identical CIDs for identical content
- Produce verifiable proofchains
- Support cross-implementation snapshot verification
- Accept records validated by any conforming validator

---

**END OF DECISION SHEET**

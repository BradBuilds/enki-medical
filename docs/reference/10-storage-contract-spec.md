# ENKI Storage Contract Specification

**Status:** AUTHORITATIVE  
**Version:** 1.0.0  
**Date:** 2025-12-31  
**Phase:** Phase 1 — Storage Contract Definition  
**Authority:** This document governs all ENKI storage implementations

---

## Document Conventions

This specification uses RFC 2119 keywords:
- **MUST** / **REQUIRED** / **SHALL**: Absolute requirement
- **MUST NOT** / **SHALL NOT**: Absolute prohibition
- **SHOULD** / **RECOMMENDED**: Strong recommendation, may have valid reasons to ignore
- **SHOULD NOT** / **NOT RECOMMENDED**: Strong discouragement
- **MAY** / **OPTIONAL**: Truly optional

---

## 1. Overview & Scope

### 1.1 Purpose

The ENKI Storage Contract defines an append-only, tamper-evident, blockchain-style verification ledger for storing validated, deterministic records. This specification is **implementation-independent**: it does not prescribe database technology, table schemas, or persistence mechanisms.

### 1.2 What This Specification Defines

- Record types and their canonical structure
- Content identity (CID) computation rules
- Transaction model and receipt structure
- ProofChain integrity model (hash chain + checkpoints)
- Validation tier requirements
- File and folder verification model
- Required storage operations and query patterns
- Error codes and failure modes
- Guarantees and invariants

### 1.3 What This Specification Does NOT Define

- Database selection (PostgreSQL, SQLite, etc.)
- SQL schemas, indexes, or query optimization
- Serialization format for network transmission
- API endpoint design (Phase 4)
- Authentication or authorization mechanisms (Phase 4)
- User interface or client libraries

### 1.4 Design Principles

1. **Strict at the ledger boundary, flexible before it**
2. **No ambiguous data enters storage as canonical fact**
3. **All stored data MUST be verifiable, hashable, and replayable**
4. **Corrections happen via append-only records, never mutation**
5. **Files are first-class verifiable artifacts**

---

## 2. Core Concepts

### 2.1 Content ID (CID)

**Definition:** A deterministic hash of a record's canonical content.

**Purpose:**
- Content identity (two records with identical content have identical CID)
- Idempotency detection (duplicate submissions)
- Verification and audit trail
- Cross-implementation interoperability

**Computation Rules:**
1. Canonicalize record using RFC 8785 (JSON Canonicalization Scheme)
2. Exclude storage-assigned fields: `rid`, `commit_time`, `receipt_id`, `chain_hash`, and any storage metadata
3. Compute SHA-256 hash of canonical bytes
4. Encode as lowercase hexadecimal string (64 characters) — REQUIRED baseline
5. Implementations MAY provide Base-60 encoding as alternate representation

**Note:** CID computation for records differs from pack content hashing. For pack-level content hash semantics (including file handling, Unicode normalization, and cross-platform determinism), see docs/spine/SPINE-00-foundations.md.

**Requirements:**
- CID computation MUST be deterministic
- Identical content MUST produce identical CID across all implementations
- CID canonical encoding MUST be lowercase hexadecimal
- Base-60 encoding (if provided) MUST be bijective with hexadecimal
- CID MUST NOT change after record acceptance

**Example (pseudo-algorithm):**
```
canonical_json = rfc8785_canonicalize(record_without_storage_fields)
cid = sha256(canonical_json).hex()
```

### 2.2 Record ID (RID)

**Definition:** A storage-assigned unique identifier for each accepted record.

**Properties:**
- Compact alphanumeric encoding (base-55, uses 55-character alphabet)
- Assigned at acceptance time (transaction commit)
- **Authoritative ordering key** for all record sequences
- Used for pagination, cursors, and stable ordering
- Strictly monotonically increasing within tenant scope

**Implementation Note:**
- RIDs are stored as 64-bit integers internally for efficient ordering
- Displayed as compact alphanumeric strings (e.g., "2", "Z", "32", "3A")
- This encoding is DISTINCT from the semantic Base-60 library used for assertion depth visualization
- See [01-base60-library-spec.md](01-base60-library-spec.md) for the semantic sexagesimal system

**Requirements:**
- RID MUST be unique within tenant
- RID MUST be assigned only after successful validation
- RID MUST provide strict total ordering (no ties)
- When ordering ambiguity exists, RID is the tiebreaker

### 2.3 Time Model

#### 2.3.1 Commit Time

**Definition:** Storage-assigned timestamp representing ledger acceptance time.

**Properties:**
- Assigned at transaction commit
- ISO 8601 format with timezone (UTC RECOMMENDED)
- SHOULD be non-decreasing (clock skew and restarts may cause exceptions)
- RID is the authoritative ordering key, not `commit_time`

**Requirements:**
- `commit_time` MUST be assigned by storage, never by client
- `commit_time` MUST be included in receipts and records
- `commit_time` SHOULD use high-precision timestamps (millisecond or better)
- When ordering records, implementations MUST use RID, not `commit_time`
- `commit_time` is informational and for human readability

#### 2.3.2 Event Time

**Definition:** Client-supplied timestamp representing when an event occurred.

**Properties:**
- Non-authoritative
- Subject to plausibility validation
- ISO 8601 format with timezone

**Requirements:**
- `event_time` MAY be rejected if implausible relative to `commit_time`
- `event_time` MUST NOT be used for ordering guarantees
- Validation SHOULD flag `event_time` > `commit_time` + tolerance
- Validation SHOULD flag `event_time` < `commit_time` - max_backdate

---

## 3. Record Types

### 3.0 Phase 1 Record Types

This specification defines the following record types for Phase 1:
1. **Assertion** — Validated truth claims
2. **AuditEvent** — Immutable system history
3. **FileArtifact** — Content-addressed files
4. **FileLocator** — Path-to-artifact bindings
5. **FolderSnapshot** — Folder state manifests
6. **Receipt** — Transaction outcomes
7. **Checkpoint** — ProofChain summaries

All records MUST be validated according to their instance specifications before storage acceptance. Storage implementations MUST reject invalid records.

### 3.1 Assertion

**Purpose:** Validated truth claims about entities and their relationships.

**Specification Reference:** See [Assertion Instance Spec](06-assertion-instance-spec.md)  
**Schema:** `schemas/assertion_instance.schema.json`

**Core Fields:**
- `assertion_id`: Unique identifier (Base-60)
- `subject`: Entity reference
- `predicate`: Vocabulary-validated predicate
- `object`: Value conforming to predicate's object kind
- `form`: Assertion form (`entity_to_entity`, `entity_to_scalar`, etc.)
- `scope`: Visibility scope (`local`, `shared`, `global`)
- `tenant_id`: Tenant isolation boundary
- `provenance`: Attribution (actor, timestamp, source)

**Storage Fields (assigned at acceptance):**
- `rid`: Record ID
- `cid`: Content ID
- `commit_time`: Ledger acceptance timestamp

**Validation:** MUST pass all four validation tiers (see §5)

### 3.2 Audit Event

**Purpose:** Immutable system history records.

**Specification Reference:** See [Audit Event Instance Spec](08-audit-event-instance-spec.md)  
**Schema:** `schemas/audit_event_instance.schema.json`

**Core Fields:**
- `event_id`: Unique identifier (Base-60)
- `event_type`: Vocabulary-validated event type (dot notation)
- `severity`: `info` | `warning` | `error` | `critical`
- `actor`: Entity performing action
- `tenant_id`: Tenant isolation boundary
- `event_time`: When event occurred (non-authoritative)
- `event_data`: Structured event payload

**Storage Fields:**
- `rid`: Record ID
- `cid`: Content ID
- `commit_time`: Ledger acceptance timestamp

**Validation:** MUST pass schema and vocabulary validation

### 3.3 FileArtifact

**Purpose:** Content-addressed file storage with immutable content hash.

**Core Fields:**
- `artifact_cid`: SHA-256 hash of raw file bytes (hexadecimal)
- `byte_length`: File size in bytes
- `content_type`: MIME type (OPTIONAL, e.g., `application/json`)
- `tenant_id`: Tenant isolation boundary

**Storage Fields:**
- `rid`: Record ID
- `commit_time`: Ledger acceptance timestamp

**Computation Rules:**
```
artifact_cid = sha256(file_bytes).hex()
```

**Requirements:**
- `artifact_cid` MUST be computed from raw file bytes (no metadata)
- Identical file content MUST produce identical `artifact_cid`
- Implementation MAY impose file size limits; MUST reject with explicit error if exceeded
- Implementation MAY deduplicate storage by `artifact_cid` (store once, reference many)

### 3.4 FileLocator

**Purpose:** Binds a file path to a content-addressed artifact at a specific point in time.

**Core Fields:**
- `locator_id`: Unique identifier (Base-60)
- `canonical_path`: Normalized relative path (see §3.7 for rules)
- `workspace_root`: Workspace or root identifier
- `artifact_cid`: Reference to FileArtifact
- `observed_at`: When this binding was observed (commit_time)
- `tenant_id`: Tenant isolation boundary

**Storage Fields:**
- `rid`: Record ID
- `cid`: Content ID (of locator record, not file)
- `commit_time`: Ledger acceptance timestamp

**Requirements:**
- `artifact_cid` MUST reference an existing FileArtifact or be accepted in same transaction
- `canonical_path` MUST conform to path canonicalization rules (§3.7)
- Multiple locators MAY reference the same `artifact_cid` (same content, different paths/times)

### 3.5 FolderSnapshot

**Purpose:** Tamper-evident folder state verification using flat manifest approach.

**Core Fields:**
- `snapshot_id`: Unique identifier (Base-60)
- `workspace_root`: Workspace or root identifier
- `snapshot_digest`: SHA-256 hash of canonical manifest
- `manifest_entry_count`: Number of files in snapshot
- `merkle_root`: OPTIONAL Merkle tree root for inclusion proofs
- `created_at`: When snapshot was created (commit_time of snapshot record)
- `tenant_id`: Tenant isolation boundary

**Storage Fields:**
- `rid`: Record ID
- `commit_time`: Ledger acceptance timestamp

**Manifest Storage:**
- Manifest entries MAY be stored inline as an array or by reference (e.g., as linked artifacts)
- Implementations MUST guarantee manifest entries are retrievable via `list_snapshot_entries(snapshot_id)`
- The canonical manifest MUST always be reconstructible for verification

**Manifest Entry Structure:**
```json
{
  "path": "schemas/assertion_instance.schema.json",
  "artifact_cid": "a1b2c3...",
  "byte_length": 4567
}
```

**Snapshot Digest Computation:**
1. Canonicalize each entry: `{path, artifact_cid, byte_length}`
2. Sort entries by `path` (lexicographic, case-sensitive)
3. Serialize using RFC 8785
4. Compute SHA-256 hash

**Requirements:**
- All referenced `artifact_cid` values MUST exist or be accepted in same transaction
- `manifest_entries` MUST be deterministically ordered (by path)
- `snapshot_digest` MUST be verifiable by recomputing from `manifest_entries`
- Merkle root (if present) SHOULD be computable from canonical manifest

**Use Cases:**
- Prove entire folder state at a point in time
- Verify schema consistency across nodes
- Detect unauthorized file modifications
- Audit definition pack integrity

### 3.6 Receipt

**Purpose:** Immutable transaction outcome record.

**Core Fields:**
- `txid`: Transaction ID (Base-60)
- `tenant_id`: Tenant scope
- `pack_reference`: Definition Pack identifier and version
- `accepted_records`: Array of `{cid, accept_index}` for successfully accepted records
- `rejected_items`: Array of `{input_hash, error_codes[], reason}` for rejected items
- `outcome`: `FULL_ACCEPT` | `PARTIAL_ACCEPT` | `FULL_REJECT`

**Storage Fields (assigned at commit):**
- `rid`: Record ID
- `commit_time`: Ledger acceptance timestamp
- `receipt_digest`: SHA-256 hash of canonical receipt core
- `chain_hash`: ProofChain hash (see §6)
- `previous_chain_hash`: Previous receipt's chain hash

**Receipt Digest Computation:**
```
canonical_core = {
  txid,
  tenant_id,
  pack_reference,
  accepted_records: [{cid, accept_index}, ...],
  rejected_items: [{input_hash, error_codes, reason?}, ...],
  outcome
}
receipt_digest = sha256(rfc8785_canonicalize(canonical_core))
```

**Exclusions from Digest:**
- `commit_time` (storage-assigned, varies by node)
- `rid` in accepted_records (storage-assigned, informational only)
- `chain_hash`, `previous_chain_hash` (computed after digest)
- Signatures or other post-commit metadata

**Requirements:**
- Every transaction MUST produce exactly one receipt
- Receipts MUST be immutable after creation
- `accept_index` MUST reflect submission order (0-based)
- `rejected_items` MUST include all validation failures with explicit error codes
- `accepted_records` MAY include `rid` for convenience, but it MUST NOT affect digest

### 3.7 Path Canonicalization Rules

**Separator:** Always `/` (forward slash)  
**Unicode Normalization:** NFC (Canonical Composition)  
**Case Handling:** Treat as case-sensitive (preserve exact case)  
**Relativity:** Paths are relative to `workspace_root`  
**Forbidden Patterns:**
- `..` (parent directory traversal)
- Absolute paths (e.g., `/`, `C:\`)
- Trailing slashes (except for root)

**Examples:**
- Valid: `schemas/assertion.schema.json`
- Valid: `libraries/identity/pack.json`
- Invalid: `../secrets/keys.txt`
- Invalid: `C:\Users\data\file.json`

---

## 4. Validation Model

Validation is **staged** and **explicit**. Records advance through tiers sequentially; failure at any tier results in rejection.

### 4.1 Tier 1: Canonicalization

**Purpose:** Ensure deterministic representation.

**Operations:**
- Field ordering (per schema)
- Base-60 normalization
- String normalization (Unicode NFC)
- JSON encoding (UTF-8)

**Outcome:** PASS or REJECT  
**Failure Action:** Reject record immediately; include in `rejected_items`

### 4.2 Tier 2: Definition Pack Validation

**Purpose:** Enforce vocabulary and schema correctness.

**Operations:**
- JSON schema validation
- Required field presence
- Type correctness
- Vocabulary term validation (predicates, event types, etc.)
- Invariant rules (e.g., predicate ↔ object kind compatibility)

**Outcome:** VALID or INVALID  
**Failure Action:** Reject record; include validation errors in receipt

### 4.3 Tier 3: Reference & Dependency Validation

**Purpose:** Ensure referential integrity.

**Operations:**
- Check referenced records exist or are accepted in same transaction
- Validate artifact_cid references (FileLocator → FileArtifact)
- Enforce dependency-atomic rules

**Outcome:** VALID or INCOMPLETE  
**Failure Action:** Reject dependent records; include dependency errors in receipt

**Dependency-Atomic Rule:**
A record CANNOT be accepted if its prerequisites are missing or rejected in the same transaction.

### 4.4 Tier 4: Policy Validation

**Purpose:** Enforce operational policies.

**Operations:**
- `event_time` plausibility checks
- Duplicate CID detection (idempotency)
- Rate limits (OPTIONAL, implementation-defined)
- Tenant-specific policies (OPTIONAL)

**Outcome:** VALID or POLICY_VIOLATION  
**Failure Action:** Reject or warn (policy-defined)

**Requirements:**
- Duplicate CID submission SHOULD return `DUPLICATE_CID` error code
- Policy violations MUST include explicit error codes
- Implementations MAY skip policy validation if disabled

### 4.5 Validation Output

All validation results MUST be explicit:
- `VALID`: Record accepted
- `INVALID`: Schema or vocabulary error
- `INCOMPLETE`: Missing dependencies
- `POLICY_VIOLATION`: Policy check failed
- `DUPLICATE_CID`: Idempotent resubmission

**Note:** Ambiguous or conflicting submissions MUST be resolved before storage. Phase 1 does not define Claim or Conflict record types; use attributed Assertions with provenance and conflict labels from vocabulary.

---

## 5. Transaction Model

### 5.1 Transaction Envelope

All writes occur within a conceptual **transaction envelope**:
```
Transaction {
  tenant_id: TenantID
  pack_reference: PackReference
  records: Record[]
}
```

**Properties:**
- Atomic at the dependency level (dependency-atomic)
- Produces exactly one receipt
- MAY result in partial acceptance

### 5.2 Dependency-Atomic Semantics

**Rule:** A record cannot be accepted if its dependencies are missing or rejected within the same transaction.

**Example:**
```
Transaction contains:
- FileArtifact A
- FileArtifact B
- FileLocator L1 → A (accepted)
- FileLocator L2 → C (rejected: C missing)
```

**Outcome:** PARTIAL_ACCEPT
- A, B, L1 accepted
- L2 rejected with `MISSING_DEPENDENCY` error

### 5.3 Transaction Outcomes

- `FULL_ACCEPT`: All submitted records accepted
- `PARTIAL_ACCEPT`: Some records accepted, some rejected
- `FULL_REJECT`: All records rejected

### 5.4 Receipt Structure

**Required Fields:**
```json
{
  "txid": "base60-id",
  "commit_time": "2025-12-31T23:59:59.123Z",
  "tenant_id": "tenant-01",
  "pack_reference": {
    "pack_id": "assertion_vocab",
    "version": "0.1.0"
  },
  "accepted_records": [
    {"cid": "a1b2c3...", "accept_index": 0, "rid": "1A2B3C"},
    {"cid": "d4e5f6...", "accept_index": 1, "rid": "1A2B3D"}
  ],
  "rejected_items": [
    {
      "input_hash": "g7h8i9...",
      "error_codes": ["MISSING_DEPENDENCY"],
      "reason": "Referenced artifact_cid not found"
    }
  ],
  "outcome": "PARTIAL_ACCEPT",
  "receipt_digest": "receipt-hash-xyz..."
}
```

**Requirements:**
- Receipts MUST be immutable
- Receipts MUST be verifiable (digest recomputation)
- `accept_index` MUST reflect submission order
- `rejected_items` MUST include sufficient detail for debugging

---

## 6. ProofChain Model

### 6.1 Purpose

The ProofChain provides **tamper-evident, blockchain-grade integrity** without relying on public blockchains.

### 6.2 Hash Chain

Receipts form an append-only hash chain.

**Computation Order:**
1. Compute `receipt_digest` from canonical receipt core (§3.6)
2. Compute `chain_hash = SHA256(previous_chain_hash || receipt_digest)`
3. Store receipt with both `receipt_digest` and `chain_hash`

**Chain Formula:**
```
chain_hash_n = SHA256(chain_hash_{n-1} || receipt_digest_n)
```

**Initialization:**
```
chain_hash_0 = SHA256("ENKI_GENESIS_" || tenant_id)
```

**Requirements:**
- Chain MUST start with genesis hash
- `receipt_digest` MUST be computed before `chain_hash`
- Each receipt MUST include both `chain_hash` and `previous_chain_hash`
- Chain MUST be verifiable by recomputing from genesis

### 6.3 Checkpoints

**Purpose:** Summarize ranges of receipts for efficient verification.

**Structure:**
```json
{
  "checkpoint_id": "base60-checkpoint-id",
  "tenant_id": "tenant-01",
  "range_start_txid": "1A2B3C",
  "range_end_txid": "9X8Y7Z",
  "checkpoint_root_hash": "root-hash-abc...",
  "previous_checkpoint_hash": "prev-checkpoint-xyz...",
  "created_at": "2025-12-31T23:59:59.123Z",
  "signature": "OPTIONAL base64-encoded-signature"
}
```

**Checkpoint Root Hash Computation:**
```
checkpoint_root_hash = SHA256(
  range_start_txid ||
  range_end_txid ||
  final_chain_hash_in_range ||
  previous_checkpoint_hash
)
```

**Requirements:**
- Checkpoints MUST cover contiguous receipt ranges
- Checkpoints MUST be monotonic (no gaps)
- Checkpoints SHOULD be cryptographically signed (Ed25519 RECOMMENDED)
- Signature MUST cover checkpoint_root_hash

### 6.4 Verification

**Chain Verification:**
1. Start from genesis hash
2. Recompute chain_hash for each receipt
3. Verify continuity: `chain_hash_n == SHA256(chain_hash_{n-1} || receipt_digest_n)`

**Checkpoint Verification:**
1. Verify checkpoint_root_hash computation
2. Verify signature (if present)
3. Verify checkpoint covers expected receipt range

**Tamper Detection:**
Any modification to a receipt will:
- Change its `receipt_digest`
- Break the hash chain from that point forward
- Invalidate all subsequent checkpoints

---

## 7. Tenant Isolation

### 7.1 Requirements

- Storage MUST enforce tenant isolation at the query/contract level
- Cross-tenant reads MUST be forbidden (Phase 1)
- Cross-tenant references MUST be forbidden (Phase 1)
- Tenant ID MUST be validated and normalized

### 7.2 Tenant ID Format

**Type:** Canonical string identifier  
**MAY:** Use Base-60 ID format  
**Normalization:** Unicode NFC, case-sensitive

**Examples:**
- `tenant-01`
- `1A2B3C` (Base-60)
- `org:acme:workspace:prod`

### 7.3 Implementation Strategies (NOT SPECIFIED)

The contract does NOT specify:
- Logical isolation (filtered queries)
- Physical isolation (separate schemas or databases)
- Hybrid approaches

Implementations MUST choose a strategy that guarantees isolation.

---

## 8. File & Folder Verification

### 8.1 Purpose

Files are **first-class verifiable artifacts** tied to the ledger. This enables:
- Proof of file content at a point in time
- Detection of unauthorized modifications
- Schema and definition pack integrity verification
- Tie between database records and actual file state

### 8.2 Required Queries

Implementations MUST support:

#### 8.2.1 Resolve Artifact by CID
```
resolve_artifact(artifact_cid) → FileArtifact | NOT_FOUND
```

#### 8.2.2 List Snapshot Entries
```
list_snapshot_entries(snapshot_id) → ManifestEntry[] | NOT_FOUND
```

#### 8.2.3 Get File State by Path
```
get_file_state(workspace_root, path, snapshot_id) → {artifact_cid, byte_length} | NOT_FOUND
```

#### 8.2.4 Get Latest Snapshot
```
get_latest_snapshot(workspace_root, tenant_id) → FolderSnapshot | NOT_FOUND
```

**Note on Verification:**
Snapshot verification against actual filesystem state is performed by a **Verifier** role, not by storage. Storage provides the queries above; verification logic computes artifact hashes from file bytes and compares against stored manifests. See §8.5 for verification model.

### 8.3 Tracked Roots

Implementations SHOULD support snapshots for:
- `schemas/` (schema governance)
- `libraries/` (definition packs)
- `docs/` (specification governance)
- Other governed directories (implementation-defined)

### 8.4 Snapshot Creation

**Trigger:** Implementation-defined (manual, automatic, policy-driven)  
**Requirement:** MUST support explicit snapshot creation via storage interface

**Recommended Triggers:**
- Definition pack load
- Schema change
- Periodic checkpoints (daily, weekly)
- On-demand via admin command

### 8.5 Verification Model (Verifier Role)

**Separation of Concerns:**
- **Storage** stores artifacts, locators, and snapshots
- **Verifier** (separate role) validates filesystem state against stored snapshots

**Verifier Responsibilities:**
- Read actual file bytes from filesystem
- Compute artifact_cid for each file
- Retrieve snapshot manifest from storage via `list_snapshot_entries()`
- Compare computed CIDs to manifest entries
- Report mismatches (modified, missing, added files)

**Storage Contract Does NOT Require:**
- Storage implementations to access filesystem directly
- Storage implementations to compute hashes from file bytes
- Storage implementations to perform verification

**What Storage MUST Provide:**
- Queries to retrieve artifacts, locators, and snapshot manifests
- Guarantees that manifest entries are always retrievable
- Snapshot digest computation from canonical manifest

---

## 9. Required Storage Operations

### 9.1 Write Operations

#### 9.1.1 Submit Transaction
```
submit_transaction(
  tenant_id: TenantID,
  pack_reference: PackReference,
  records: Record[]
) → Receipt
```

**Behavior:**
- Validate all records (4-tier validation)
- Enforce dependency-atomic rules
- Assign RIDs and commit_time to accepted records
- Generate receipt with outcome

#### 9.1.2 Create Snapshot
```
create_snapshot(
  tenant_id: TenantID,
  workspace_root: String,
  manifest_entries: [{path, artifact_cid, byte_length}, ...]
) → FolderSnapshot
```

**Behavior:**
- Validate all referenced `artifact_cid` values exist
- Create FolderSnapshot record with canonical manifest
- Compute `snapshot_digest` from manifest
- Assign RID and commit_time
- Return snapshot record

**Note:** Artifact creation and CID computation occur before snapshot creation (via separate transactions or same transaction with dependency ordering). Storage does not require access to raw file bytes.

### 9.2 Read Operations

#### 9.2.1 Get Record by RID
```
get_by_rid(tenant_id: TenantID, rid: RID) → Record | NOT_FOUND
```

#### 9.2.2 Get Record by CID
```
get_by_cid(tenant_id: TenantID, cid: CID) → Record | NOT_FOUND
```

#### 9.2.3 List Records
```
list_records(
  tenant_id: TenantID,
  record_type: RecordType,
  cursor: RID | null,
  limit: int
) → {records: Record[], next_cursor: RID | null}
```

**Requirements:**
- MUST support cursor-based pagination
- MUST return results in RID order
- MUST respect tenant isolation

#### 9.2.4 Get Receipt
```
get_receipt(tenant_id: TenantID, txid: TXID) → Receipt | NOT_FOUND
```

### 9.3 Verification Operations

#### 9.3.1 Verify Chain
```
verify_chain(
  tenant_id: TenantID,
  start_txid: TXID | null,
  end_txid: TXID | null
) → {valid: bool, break_point: TXID | null}
```

#### 9.3.2 Verify Checkpoint
```
verify_checkpoint(checkpoint_id: CheckpointID) → {valid: bool, errors: []}
```

---

## 10. Error Codes & Outcomes

### 10.1 Validation Error Codes

| Code | Meaning |
|------|---------|
| `SCHEMA_VIOLATION` | JSON schema validation failed |
| `INVALID_VOCABULARY` | Term not in definition pack |
| `TYPE_MISMATCH` | Value type incorrect for field |
| `MISSING_REQUIRED_FIELD` | Required field absent |
| `INVALID_PREDICATE_FORM` | Predicate incompatible with form |
| `MISSING_DEPENDENCY` | Referenced record not found |
| `DUPLICATE_CID` | Idempotent resubmission detected |
| `EVENT_TIME_IMPLAUSIBLE` | event_time violates policy |
| `TENANT_ISOLATION_VIOLATION` | Cross-tenant reference attempted |
| `PATH_CANONICALIZATION_ERROR` | Path violates rules (e.g., contains `..`) |
| `FILE_TOO_LARGE` | Artifact exceeds size limit |
| `BATCH_SIZE_EXCEEDED` | Transaction too large |
| `TIMEOUT` | Transaction exceeded time limit |

### 10.2 Storage Error Codes

| Code | Meaning |
|------|---------|
| `TENANT_NOT_FOUND` | Tenant ID invalid or not provisioned |
| `NOT_FOUND` | Record does not exist |
| `CHAIN_BREAK_DETECTED` | ProofChain integrity violation |
| `CHECKPOINT_INVALID` | Checkpoint verification failed |
| `STORAGE_UNAVAILABLE` | Temporary storage failure |

---

## 11. Guarantees & Invariants

### 11.1 MUST Guarantees

1. **Append-Only Immutability:** Accepted records MUST NEVER be modified or deleted
2. **Deterministic Hashing:** CID computation MUST be deterministic across implementations
3. **Tamper-Evident History:** ProofChain MUST detect any modification to receipts
4. **Durable Commits:** Once a receipt is returned, data MUST be durable (survived crash)
5. **Tenant Isolation:** Cross-tenant reads and references MUST be impossible
6. **Stable Pagination:** Cursor-based pagination MUST return consistent results
7. **Replayability:** All transactions MUST be replayable from receipts
8. **Auditability:** All state changes MUST be traceable via audit events and receipts

### 11.2 SHOULD Guarantees

1. **High-Precision Timestamps:** commit_time SHOULD have millisecond or better precision
2. **Cryptographic Signatures:** Checkpoints SHOULD be signed with Ed25519
3. **Efficient Verification:** Checkpoint verification SHOULD not require full chain replay

### 11.3 Invariants

- `RID` is strictly monotonically increasing within tenant scope
- `RID` provides total ordering for all records
- `commit_time` SHOULD be non-decreasing (but RID is authoritative for ordering)
- `RID` is unique per tenant
- `CID` uniquely identifies content (collision probability negligible)
- Every accepted record has exactly one RID and one CID
- Every transaction produces exactly one receipt
- Receipts form a valid hash chain from genesis
- `receipt_digest` is deterministic across implementations (excludes node-specific metadata)

---

## 12. What Storage MUST NOT Store

### 12.1 Forbidden Data

Storage implementations MUST NOT persist:
- Ephemeral conversation state (prompts, reasoning traces)
- Temporary validation artifacts (intermediate results)
- Raw LLM prompts or responses (unless explicitly structured as records)
- Secrets, private keys, or credentials
- Cache-only derived data (e.g., computed indexes not part of contract)

### 12.2 Rationale

The ledger stores **canonical facts**, not **process artifacts**. Ambiguity, drafts, and reasoning MUST be resolved before submission. Only receipts record rejected attempts.

---

## 13. Handling Ambiguity (Phase 1 Approach)

### 13.1 Problem Statement

Human conversation may be ambiguous or contradictory. The storage contract addresses this:

**Core Principle:** Ambiguity MUST NOT be stored as canonical fact.

### 13.2 Phase 1 Mechanisms

**Available in v1.0.0:**
- **Attributed Assertions:** Use provenance fields to record "who said what"
- **Validation Errors:** Reject ambiguous submissions with explicit error codes
- **Draft States:** Keep unresolved conversations outside storage
- **Supersession:** New assertions can supersede old ones (append-only correction)
- **Conflict Labels:** Use assertion conflict types from vocabulary (`exclusive`, `temporal`, etc.)

### 13.3 Future Record Types (Post-Phase 1)

The following record categories MAY be defined in future versions:
- **Claim Records:** Explicit "Person A said X" without truth commitment
- **Conflict Markers:** Structured conflict resolution metadata
- **Discussion Threads:** Conversation context without canonical assertion

These are intentionally excluded from Phase 1 to maintain scope clarity.

---

## 14. Compliance & Conformance

### 14.1 Conformance Requirements

An implementation is **conformant** if it:
1. Implements all MUST requirements in this specification
2. Adheres to locked decisions in 09-storage-contract-decisions.md
3. Produces interoperable CIDs and receipts
4. Passes a conformance test suite (Phase 3)

### 14.2 Interoperability

Conformant implementations MUST:
- Accept records validated by any conformant validator
- Produce identical CIDs for identical content
- Verify receipts and checkpoints from other conformant implementations

---

## 15. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-31 | Initial Storage Contract Specification (Phase 1) |

---

## 16. References

- [Storage Contract Decision Sheet](09-storage-contract-decisions.md)
- ENKI MASTER PLAN
- [Validation Contract](02-validation-contract.md)
- [Assertion Instance Spec](06-assertion-instance-spec.md)
- [Audit Event Instance Spec](08-audit-event-instance-spec.md)
- RFC 2119: Key words for use in RFCs to Indicate Requirement Levels
- RFC 8785: JSON Canonicalization Scheme (JCS)

---

**END OF SPECIFICATION**

# GDU Update Security & ENKI Overlay Network

**Status:** Authoritative Specification  
**Governance:** Security Architecture & Network Protocol  
**Audience:** Core developers, security architects, network engineers  
**Created:** 2026-01-09  
**Depends On:** 
- 25-gdu-core-master-plan.md
- [26-gdu-library-structure.md](26-gdu-library-structure.md)

**Authority:** This document defines update security mechanisms and overlay network architecture

---

## Purpose

This document establishes:

1. **GDU Update Security:** Spine-gated update flow preventing malicious modifications to the definition universe
2. **ENKI Overlay Network:** Secondary addressing layer providing identity-based routing over IP carriers

Both systems are **fail-closed** and **cryptographically bound to GDU state**.

---

## Core Principles

> **Security Principle:**  
> GDU updates require explicit human approval with physical presence verification.  
> All approvals sign exact cryptographic digests, never abstract intentions.

> **Network Principle:**  
> IP is the carrier only. ENKI addresses represent identity, policy, and routing authority.  
> All network activity is cryptographically bound to GDU state via receipts.

---

# PART A — GDU Update Security (Spine-Gated)

## Threat Model

### Threat 1: Malicious Pack Injection

**Attack Vector:**
- Attacker submits pack with malicious definitions
- Pack appears valid but contains backdoors, semantic trojans, or policy bypasses
- Goal: Inject unauthorized logic into GDU

**Impact:**
- Corrupted semantic foundation
- All downstream computation compromised
- Undetected privilege escalation

**Mitigation:**
- Cryptographic signature verification
- Dependency validation
- Diff-based risk classification
- Human-in-the-loop approval
- Immutable audit trail

---

### Threat 2: Semantic Drift

**Attack Vector:**
- Attacker modifies definition meaning over time
- Small, incremental changes accumulate
- Original intent gradually corrupted
- Goal: Redefine terms to enable unauthorized actions

**Impact:**
- Loss of semantic stability
- Contracts become meaningless
- Historical data misinterpreted

**Mitigation:**
- Versioning with explicit supersession
- Deprecation notices
- Compatibility declarations
- Breaking change detection
- Diff review showing semantic changes

---

### Threat 3: Rollback Attack

**Attack Vector:**
- Attacker replaces current GDU with older, vulnerable version
- Exploits patched vulnerabilities
- Bypasses recent security enhancements
- Goal: Reintroduce known weaknesses

**Impact:**
- Re-exposure to fixed vulnerabilities
- Security regression
- Loss of recent improvements

**Mitigation:**
- Monotonic version counters
- Activation timestamp chains
- Anti-rollback verification
- Digest history validation

---

### Threat 4: Dependency Poisoning

**Attack Vector:**
- Attacker compromises a low-level pack
- Many higher-level packs depend on compromised pack
- Transitive trust exploited
- Goal: Widespread compromise through supply chain

**Impact:**
- Cascading corruption
- Difficult to detect source
- Wide attack surface

**Mitigation:**
- Recursive dependency validation
- Trust boundary enforcement
- Isolated pack verification
- Explicit dependency declarations

---

### Threat 5: Toolchain Compromise

**Attack Vector:**
- Attacker compromises pack builder, validator, or admission tools
- Malicious code injected during build process
- Digital signatures applied to compromised artifacts
- Goal: Bypass security checks at source

**Impact:**
- Trust anchor compromised
- Signatures meaningless
- Validation bypassed

**Mitigation:**
- Reproducible builds
- Multi-party verification
- Separate validation environments
- Tool integrity checks
- Witness signatures

---

### Threat 6: Human Error

**Attack Vector:**
- Legitimate operator makes configuration mistake
- Wrong pack activated
- Incompatible versions mixed
- Goal: None (accident)

**Impact:**
- Service disruption
- Data inconsistency
- Rollback required

**Mitigation:**
- Diff review before activation
- Compatibility validation
- Dry-run simulation
- Clear approval interface
- Undo capability

---

## Spine-Gated Update Flow

The **Spine** is the governance-controlled update pipeline. All GDU updates MUST flow through the Spine.

### Overview

```
LDU (drafts) 
    ↓
[Phase 1] Intake
    ↓
[Phase 2] Canonicalization + Validation
    ↓
[Phase 3] Dependency + Authority Validation
    ↓
[Phase 4] Diff + Risk Classification
    ↓
[Phase 5] Dual-Run / Conformance (Optional)
    ↓
[Phase 6] Watch-Based Approval Ceremony
    ↓
[Phase 7] Atomic Activation
    ↓
GDU (production)
```

---

### Phase 1: Intake

**Purpose:** Accept proposed updates from LDU and assign tracking identifiers.

**Inputs:**
- Pack directory (from LDU)
- Submitter identity
- Intent declaration (new pack, update, deprecation)

**Process:**
1. Assign unique intake ID: `INTAKE-{timestamp}-{hash}`
2. Compute initial pack hash
3. Record submission metadata
4. Move to staging area
5. Emit `IntakeReceived` event

**Outputs:**
- Intake record (immutable)
- Staging location
- Tracking ID

**Failure Modes:**
- Invalid directory structure → Reject immediately
- Missing pack.json → Reject immediately
- Duplicate submission → Reject with reference to original

**Security Invariant:**  
Intake does NOT trust content. All validation happens in subsequent phases.

---

### Phase 2: Canonicalization + Validation

**Purpose:** Normalize format and validate against schemas.

**Inputs:**
- Staged pack from Phase 1
- Intake ID
- Schema definitions

**Process:**
1. **Canonicalization:**
   - Sort all JSON keys deterministically
   - Normalize whitespace
   - Remove comments
   - Validate UTF-8 encoding
   - Compute canonical hash

2. **Schema Validation:**
   - Validate pack.json against `schemas/registry_pack.schema.json`
   - Validate each definition against `schemas/definition.schema.json`
   - Check required fields
   - Validate types
   - Verify ID/version consistency

3. **Structural Validation:**
   - Verify filename matches `{id}__{version}.json` convention
   - Check for duplicate definitions
   - Validate version semantics (semver)
   - Ensure no reserved IDs

**Outputs:**
- Canonicalized pack (deterministic)
- Validation transcript
- Canonical pack hash
- List of definitions with hashes

**Failure Modes:**
- Schema violation → Fail with detailed error report
- Canonicalization error → Fail with file/line information
- Duplicate ID+version → Fail with conflict reference

**Security Invariant:**  
Only canonicalized, schema-valid packs proceed. No exceptions.

---

### Phase 3: Dependency + Authority Validation

**Purpose:** Verify dependencies exist and submitter has authority.

**Inputs:**
- Canonicalized pack from Phase 2
- Current GDU state
- Submitter identity
- Authority rules (from GDU policy/)

**Process:**

1. **Dependency Resolution:**
   - Extract all referenced definitions (base_entity, attributes, etc.)
   - For each reference:
     - Check if exists in current GDU
     - Verify version compatibility
     - Build dependency graph
   - Detect circular dependencies
   - Identify new vs updated definitions

2. **Authority Validation:**
   - Lookup submitter identity in GDU
   - Check permissions for namespace (e.g., `entity.*`, `attribute.color.*`)
   - Verify signature chain
   - Validate delegation if present
   - Check policy constraints (approval count, review period)

3. **Conflict Detection:**
   - Check for semantic conflicts with existing definitions
   - Verify namespace ownership
   - Detect supersession claims
   - Validate deprecation notices

**Outputs:**
- Dependency graph
- Authority verification result
- Conflict report (if any)
- Transitively affected definitions list

**Failure Modes:**
- Missing dependency → Fail with dependency list
- Authority violation → Fail with permission denial
- Namespace conflict → Fail with ownership proof requirement
- Circular dependency → Fail with cycle trace

**Security Invariant:**  
Only authorized changes to owned namespaces proceed. No unauthorized modifications.

---

### Phase 4: Diff + Risk Classification

**Purpose:** Compute precise changes and classify update risk.

**Inputs:**
- Canonicalized pack from Phase 2
- Dependency graph from Phase 3
- Current GDU state

**Process:**

1. **Diff Computation:**
   - For each definition:
     - Compare with GDU version (if exists)
     - Compute field-level diff
     - Identify semantic changes
     - Detect breaking changes
   - Classify changes:
     - **New:** Definition doesn't exist in GDU
     - **Update:** Definition exists, content changed
     - **Supersede:** New version supersedes old
     - **Deprecate:** Mark old version obsolete

2. **Risk Classification:**
   - **LOW:** New definitions, patch version increments, documentation changes
   - **MEDIUM:** Minor version increments, new attributes, constraint additions
   - **HIGH:** Major version increments, entity changes, breaking changes
   - **CRITICAL:** Policy changes, identity changes, crypto suite changes

3. **Impact Analysis:**
   - Count affected compositions
   - Identify dependent packs
   - Estimate disruption scope
   - Calculate rollback complexity

4. **Diff Report Generation:**
   - Human-readable change summary
   - Side-by-side comparison
   - Highlighted semantic changes
   - Risk justification

**Outputs:**
- Detailed diff report
- Risk classification (LOW/MEDIUM/HIGH/CRITICAL)
- Impact analysis
- Affected definitions list
- Diff digest (for signing)

**Failure Modes:**
- Breaking change without version increment → Fail
- Incompatible constraint modification → Fail
- Unresolved semantic ambiguity → Fail

**Security Invariant:**  
Risk classification is deterministic and conservative (fail-high, not fail-low).

---

### Phase 5: Dual-Run / Conformance (Optional)

**Purpose:** Test new definitions against current GDU in parallel.

**Status:** Optional but defined for high-risk updates.

**Inputs:**
- Candidate pack from Phase 4
- Test workload specification
- Current GDU state

**Process:**

1. **Environment Preparation:**
   - Create isolated GDU snapshot
   - Inject candidate pack (shadow GDU)
   - Initialize dual runtime contexts

2. **Parallel Execution:**
   - Execute test workload against both GDUs
   - Record all definition resolutions
   - Capture performance metrics
   - Log behavioral differences

3. **Conformance Analysis:**
   - Compare outputs
   - Detect semantic divergence
   - Identify performance regressions
   - Validate compatibility claims

4. **Report Generation:**
   - Conformance percentage
   - Divergence cases
   - Performance comparison
   - Compatibility verification

**Outputs:**
- Conformance report
- Divergence log
- Performance metrics
- Recommendation (approve/reject/revise)

**Failure Modes:**
- Conformance < threshold → Recommend reject
- Critical divergence → Recommend reject
- Performance regression > limit → Recommend reject

**Security Invariant:**  
Shadow GDU is isolated. No production impact from testing.

**Note:** This phase is OPTIONAL for LOW-risk updates, RECOMMENDED for MEDIUM/HIGH, REQUIRED for CRITICAL.

---

### Phase 6: Watch-Based Approval Ceremony

**Purpose:** Obtain explicit human approval with physical presence verification.

**Inputs:**
- All artifacts from Phases 1-5
- Approval policy (from GDU policy/)
- Approver identity(ies)

**Process:**

1. **Presentation:**
   - Display diff report on secure terminal
   - Show risk classification
   - Present impact analysis
   - Display all intermediate cryptographic digests (approval workflow only):
     - `PACK_DIGEST`: SHA-256 of canonical pack content (all definitions)
     - `MANIFEST_DIGEST`: SHA-256 of pack.json metadata
     - `DIFF_DIGEST`: SHA-256 of change summary from Phase 4
     - `COMPAT_DIGEST`: SHA-256 of compatibility declaration
   - **Note:** These digests are for human review and approval signing. Runtime uses only `ACTIVE_GDU_DIGEST` (see Doc 25).

2. **Physical Presence Verification:**
   - Approver must be physically present at secure terminal
   - No remote approval allowed
   - Time-limited approval window (e.g., 60 seconds)
   - Environmental factors recorded:
     - Terminal ID
     - Physical location
     - Network status (must be isolated or verified secure)
     - Time of day
     - Witness identities (if policy requires)

3. **Digest Signing:**
   - Approver reviews exact digests (not abstract descriptions)
   - Approver signs:
     ```
     APPROVAL_SIGNATURE = sign(
       PACK_DIGEST,
       MANIFEST_DIGEST,
       DIFF_DIGEST,
       COMPAT_DIGEST,
       RISK_CLASSIFICATION,
       APPROVAL_TIMESTAMP,
       APPROVER_IDENTITY,
       TERMINAL_ID
     )
     ```
   - Signature includes anti-replay nonce
   - Signature binds to current GDU state

4. **Authorization Object Creation:**
   - Create short-lived authorization token:
     ```json
     {
       "authorization_id": "AUTH-{timestamp}-{hash}",
       "pack_digest": "sha256:...",
       "manifest_digest": "sha256:...",
       "diff_digest": "sha256:...",
       "compat_digest": "sha256:...",
       "risk_classification": "HIGH",
       "approver": "identity.user.admin_alice",
       "signature": "...",
       "timestamp": "2026-01-09T12:34:56Z",
       "expires": "2026-01-09T12:39:56Z",
       "nonce": "...",
       "current_gdu_digest": "sha256:...",
       "terminal_id": "SECURE-TERMINAL-01"
     }
     ```
   - `pack_digest`, `manifest_digest`, `diff_digest`, `compat_digest`: Intermediate approval artifacts (archived in activation record, not used by runtime)
   - `current_gdu_digest`: The ACTIVE_GDU_DIGEST at approval time (enables anti-rollback rule during activation)
   - Token valid for 5 minutes only
   - Single-use (consumed during activation)

5. **Witness Recording (if required by policy):**
   - Capture witness signatures
   - Record consensus mechanism
   - Store in immutable log

**Outputs:**
- Authorization object (short-lived)
- Approval signature
- Witness records
- Audit trail entry

**Failure Modes:**
- Physical presence not verified → Reject
- Digest mismatch → Reject
- Signature invalid → Reject
- Authorization expired → Reject (must restart ceremony)
- Insufficient approvers → Reject (per policy)

**Security Invariants:**
1. **No Remote Approval:** Physical presence mandatory
2. **No Abstract Approval:** Only exact digests signed
3. **Time-Bounded:** Authorization expires quickly
4. **Single-Use:** Authorization consumed atomically
5. **GDU-Bound:** Authorization tied to specific GDU state

**Anti-Replay Rules:**
- Nonce must be globally unique
- Timestamp must be monotonically increasing
- Authorization ID tracked to prevent reuse

**Anti-Rollback Rules:**
- Authorization includes `current_gdu_digest`
- Activation verifies GDU hasn't changed
- If GDU changed → Authorization invalid, must re-approve

---

### Phase 7: Atomic Activation

**Purpose:** Activate approved pack into GDU atomically.

**Inputs:**
- Authorization object from Phase 6
- Canonicalized pack from Phase 2
- Current GDU state

**Process:**

1. **Pre-Activation Verification:**
   - Verify authorization not expired
   - Verify authorization not consumed
   - Verify `current_gdu_digest` matches actual GDU
   - Re-verify all pack hashes match authorization
   - Check no GDU mutations since approval

2. **Atomic Registry Update (Filesystem)**

   **Phase 7b.1: Install Pack to Registry**
   ```
   1. Create temp directory: gdu/registry/packs.tmp/{PACK_DIGEST}/
   2. Copy pack files to temp directory
   3. Verify content hash matches PACK_DIGEST
   4. Atomic rename: gdu/registry/packs.tmp/{PACK_DIGEST}/ 
      → gdu/registry/packs/{PACK_DIGEST}/
   ```
   
   **Phase 7b.2: Update Active Pointer (Moment of Truth)**
   ```
   5. Create temp: gdu/registry/active.json.tmp
   6. Write new active.json to temp (add new pack, sort by pack_id)
   7. Atomic rename: gdu/registry/active.json.tmp 
      → gdu/registry/active.json
   ```
   
   **Atomicity Guarantee:** Filesystem atomic rename ensures all-or-nothing. No partial state visible.

   **Phase 7b.3: Update History (After Active Pointer)**
   ```
   8. Update epoch.json: increment epoch_number, record new ACTIVE_SET_DIGEST
   ```

3. **Post-Activation Notification**
   - Mark authorization as consumed (immutable activation record)
   - Create activation record (includes intermediate digests: MANIFEST_DIGEST, DIFF_DIGEST, COMPAT_DIGEST)
   - Update admission log
   - Emit `ActivationComplete` event
   
4. **Runtime Restart Required**
   - `ACTIVE_GDU_DIGEST` is locked at runtime initialization
   - New digest requires runtime restart to take effect
   - No in-flight cache update (fail-closed design)
   - Existing PackLoader instances continue using old digest until restart

**Outputs:**
- New GDU state
- New `ACTIVE_GDU_DIGEST`
- Activation record (immutable)
- Audit events

**Failure Modes:**
- Authorization invalid → Abort, log security event
- GDU digest mismatch → Abort, require re-approval
- Transaction failure → Rollback completely, preserve old state
- Filesystem error → Abort, preserve old state

**Security Invariants:**
1. **Atomicity:** Either complete activation or no change
2. **Consistency:** GDU always in valid state
3. **Isolation:** No partial state visible
4. **Durability:** Successful activation persists
5. **Fail-Closed:** Any error aborts activation

---

## Watch-Based Approval Specification

### Physical Presence Requirements

**Mandatory:**
- Approver physically at secure terminal
- Secure terminal identified by hardware token
- Terminal in physically secured location
- No remote desktop, SSH, or network forwarding
- Terminal display visible to approver only
- Optional witness co-located

**Verification:**
- Hardware token verification (e.g., USB security key)
- Terminal GPS/location check (if available)
- Network isolation verification
- Biometric confirmation (optional)

---

### Approval Interface

**Display Requirements:**
1. Full diff report (scrollable)
2. Risk classification (prominent)
3. Impact summary (counts, lists)
4. All cryptographic digests (full hashes, no truncation)
5. Warning: "You are signing these exact digests"
6. Countdown timer (60 seconds)
7. Clear APPROVE / REJECT buttons

**Interaction Flow:**
```
1. Display: "Pack update requires approval"
2. Show: Risk classification badge
3. Show: Diff report (full)
4. Show: All digests with labels
5. Prompt: "Review carefully. Sign exact digests?"
6. Require: Explicit scroll to bottom
7. Enable: APPROVE button (after full review)
8. Countdown: 60 seconds to decide
9. On APPROVE:
   - Prompt: "Enter passphrase" or "Insert hardware key"
   - Generate signature
   - Create authorization
   - Display: "Authorization valid for 5 minutes"
10. On REJECT:
    - Log rejection
    - Return to intake with notes
```

---

### Short-Lived Authorization Object

**Structure:**
```json
{
  "authorization_id": "AUTH-20260109-123456-a1b2c3",
  "pack_digest": "sha256:a1b2c3d4e5f6...",
  "manifest_digest": "sha256:f6e5d4c3b2a1...",
  "diff_digest": "sha256:123456789abc...",
  "compat_digest": "sha256:abcdef123456...",
  "risk_classification": "HIGH",
  "approver": "identity.user.admin_alice",
  "approver_signature": "ed25519:...",
  "timestamp": "2026-01-09T12:34:56.789Z",
  "expires": "2026-01-09T12:39:56.789Z",
  "nonce": "550e8400-e29b-41d4-a716-446655440000",
  "current_gdu_digest": "sha256:current_state_hash",
  "terminal_id": "SECURE-TERMINAL-01",
  "terminal_location": "Datacenter-A, Rack-7, Position-3",
  "witness_signatures": [],
  "consumed": false,
  "consumed_at": null,
  "activation_record_id": null
}
```

**Lifecycle:**
1. Created: After approval signature
2. Valid: 5 minutes from timestamp
3. Consumed: During atomic activation (Phase 7)
4. Expired: After 5 minutes OR after consumption
5. Archived: Immutable record in audit log

---

### Anti-Replay Enforcement

**Nonce Generation:**
- UUIDv4 (cryptographically random)
- Stored in nonce registry
- Checked before authorization creation
- Duplicate nonce → Reject

**Timestamp Validation:**
- Must be within ±30 seconds of system time
- Must be > last authorization timestamp
- Monotonic counter enforced

**Signature Verification:**
- Public key lookup from GDU identity/
- Signature algorithm from GDU crypto suite
- Full signature chain validation

---

### Anti-Rollback Enforcement

**GDU Digest Binding:**
```python
def validate_authorization(auth):
    if auth.current_gdu_digest != compute_gdu_digest():
        raise AntiRollbackError(
            "GDU state changed since approval. "
            "Re-approval required."
        )
```

**Version Counter:**
```python
# Active set version must increase
if new_active_set_version <= current_active_set_version:
    raise AntiRollbackError(
        f"Active set version must increase. "
        f"Current: {current}, Proposed: {new}"
    )
```

**Activation Timestamp Chain:**
```python
# Activation timestamps must be monotonic
if new_activation_timestamp <= last_activation_timestamp:
    raise AntiRollbackError(
        "Activation timestamp must be > last activation"
    )
```

---

## Security Guarantees

### Guarantee 1: No Unauthorized Updates

**Property:** Only packs with valid authorization can activate.

**Enforcement:**
- Cryptographic signature verification
- Authority validation (Phase 3)
- Watch-based approval (Phase 6)

**Violation Detection:**
- All activations logged with signature
- Missing signature → Fatal error
- Invalid signature → Security event + halt

---

### Guarantee 2: No Semantic Ambiguity

**Property:** All definitions have single, explicit meaning.

**Enforcement:**
- Schema validation (Phase 2)
- Conflict detection (Phase 3)
- Diff review (Phase 4)

**Violation Detection:**
- Namespace conflicts rejected
- Duplicate IDs rejected
- Ambiguous references rejected

---

### Guarantee 3: No Rollback

**Property:** GDU version strictly increases over time.

**Enforcement:**
- Monotonic version counters
- Activation timestamp chain
- GDU digest binding in authorization

**Violation Detection:**
- Version decrease → Reject
- Timestamp decrease → Reject
- Digest mismatch → Reject

---

### Guarantee 4: Audit Completeness

**Property:** All GDU modifications fully audited.

**Enforcement:**
- Immutable audit log
- Event emission at each phase
- Authorization record preservation

**Violation Detection:**
- Activation without audit entry → Impossible (atomic)
- Missing authorization → Fatal error
- Gap in audit log → Security alert

---

### Guarantee 5: Fail-Closed

**Property:** Any error halts activation without partial update.

**Enforcement:**
- Atomic transactions (Phase 7)
- Pre-activation verification
- Rollback on failure

**Violation Detection:**
- Partial state → Impossible (transaction)
- Error during activation → Full rollback
- Inconsistent state → Runtime halt

---

# PART B — ENKI Overlay Network

## Network Architecture Separation

### IP as Carrier Only

**Principle:**  
IP provides packet transport. ENKI provides identity, routing, and policy.

**IP Layer Responsibilities:**
- Physical/link layer connectivity
- Packet forwarding
- Congestion control
- Basic reachability

**IP Layer Does NOT:**
- Identify ENKI nodes
- Enforce ENKI policy
- Provide semantic routing
- Understand ENKI messages

---

### ENKI Address = Identity + Routing + Policy

**ENKI Address Structure:**
```
enki://{node_identity}@{network_id}/{resource_path}
```

**Example:**
```
enki://node.abc123@mainnet/gdu/entities/car
```

**Components:**
- `node_identity`: Cryptographic node ID (from GDU identity/)
- `network_id`: Network namespace (e.g., mainnet, testnet)
- `resource_path`: Semantic resource locator

**Contrast with IP:**
| Layer | IP Address | ENKI Address |
|-------|------------|--------------|
| **Identity** | Host location | Node identity (cryptographic) |
| **Routing** | Network topology | Policy + trust graph |
| **Stability** | Changes with location | Stable across networks |
| **Meaning** | "Where is it?" | "Who is it and what does it have?" |

---

## GDU Network Definitions

The following network-related definitions MUST exist in GDU for overlay network operation:

### Node Identities (gdu/libraries/network/)

**Purpose:** Define node types and their capabilities.

**Definitions:**
```
network.node.peer
network.node.relay
network.node.gateway
network.node.edge
network.node.validator
```

**Example Definition:**
```json
{
  "id": "network.node.peer",
  "type": "network_node",
  "version": "1.0.0",
  "content": {
    "name": "peer",
    "capabilities": ["message_routing", "gdu_replication", "query_handling"],
    "required_policies": ["authentication", "encryption"],
    "trust_requirements": ["identity_verification", "signature_validation"]
  }
}
```

---

### Message Types (gdu/libraries/network/)

**Purpose:** Define all valid ENKI message types.

**Definitions:**
```
network.message.handshake_request
network.message.handshake_response
network.message.encrypted_envelope
network.message.gdu_query
network.message.gdu_response
network.message.attestation
network.message.receipt
```

**Example Definition:**
```json
{
  "id": "network.message.handshake_request",
  "type": "network_message",
  "version": "1.0.0",
  "content": {
    "name": "handshake_request",
    "required_fields": [
      "sender_identity",
      "sender_public_key",
      "nonce",
      "supported_crypto_suites",
      "gdu_digest",
      "timestamp"
    ],
    "optional_fields": ["capabilities", "policies"],
    "max_size_bytes": 4096
  }
}
```

---

### Peer Policies (gdu/libraries/policy/)

**Purpose:** Define rules governing peer interactions.

**Definitions:**
```
policy.peer.allow_all
policy.peer.authenticated_only
policy.peer.verified_only
policy.peer.whitelist_only
policy.peer.rate_limited
```

**Example Definition:**
```json
{
  "id": "policy.peer.authenticated_only",
  "type": "peer_policy",
  "version": "1.0.0",
  "content": {
    "name": "authenticated_only",
    "rule": "reject_unauthenticated",
    "requirements": [
      "valid_identity_signature",
      "current_gdu_digest_match",
      "nonce_uniqueness"
    ],
    "enforcement": "connection_time",
    "violation_action": "disconnect_immediately"
  }
}
```

---

### Crypto Suites (gdu/libraries/network/)

**Purpose:** Define supported cryptographic primitives.

**Definitions:**
```
network.crypto.suite_v1
network.crypto.suite_v2_quantum_resistant
```

**Example Definition:**
```json
{
  "id": "network.crypto.suite_v1",
  "type": "crypto_suite",
  "version": "1.0.0",
  "content": {
    "name": "suite_v1",
    "key_exchange": "x25519",
    "signature": "ed25519",
    "encryption": "chacha20_poly1305",
    "hash": "blake3",
    "kdf": "hkdf_sha256",
    "min_key_bits": 256
  }
}
```

---

## Secure Messaging Protocol

### High-Level Flow

```
Peer A                                  Peer B
   |                                       |
   |--- Handshake Request --------------->|
   |       (identity, nonce, crypto)      |
   |                                      |
   |<-- Handshake Response ---------------|
   |       (identity, nonce, crypto)      |
   |                                      |
   |--- Encrypted Envelope -------------->|
   |       (policy-bound message)         |
   |                                      |
   |<-- Receipt --------------------------|
   |       (GDU-bound acknowledgment)     |
```

---

### Phase 1: Handshake

**Purpose:** Establish identity and negotiate encryption.

**Handshake Request:**
```json
{
  "message_type": "network.message.handshake_request",
  "version": "1.0.0",
  "sender_identity": "network.node.peer_abc123",
  "sender_public_key": "ed25519:...",
  "nonce": "550e8400-e29b-41d4-a716-446655440000",
  "supported_crypto_suites": [
    "network.crypto.suite_v1",
    "network.crypto.suite_v2_quantum_resistant"
  ],
  "gdu_digest": "sha256:...",
  "timestamp": "2026-01-09T12:34:56Z",
  "signature": "ed25519:..."
}
```

**Handshake Response:**
```json
{
  "message_type": "network.message.handshake_response",
  "version": "1.0.0",
  "responder_identity": "network.node.peer_xyz789",
  "responder_public_key": "ed25519:...",
  "request_nonce": "550e8400-e29b-41d4-a716-446655440000",
  "response_nonce": "660f9511-f39c-52e5-b827-557766551111",
  "selected_crypto_suite": "network.crypto.suite_v1",
  "gdu_digest": "sha256:...",
  "timestamp": "2026-01-09T12:34:57Z",
  "shared_secret_kdf": "hkdf(ephemeral_dh, request_nonce, response_nonce)",
  "signature": "ed25519:..."
}
```

**Verification Steps:**
1. Validate sender/responder identity exists in GDU
2. Verify signature using public key from GDU
3. Check GDU digest matches local state
4. Verify timestamp within acceptable window
5. Check nonce uniqueness
6. Validate crypto suite supported
7. Derive shared secret using selected suite

**Failure Modes:**
- Identity not in GDU → Reject
- Signature invalid → Reject
- GDU digest mismatch → Reject (cannot communicate)
- Timestamp out of window → Reject
- Nonce reused → Reject (replay attack)
- No compatible crypto suite → Reject

---

### Phase 2: Encrypted Envelope

**Purpose:** Send authenticated, encrypted message with policy binding.

**Envelope Structure:**
```json
{
  "message_type": "network.message.encrypted_envelope",
  "version": "1.0.0",
  "envelope_id": "envelope-20260109-123456-abc",
  "sender_identity": "network.node.peer_abc123",
  "recipient_identity": "network.node.peer_xyz789",
  "sequence_number": 42,
  "timestamp": "2026-01-09T12:35:00Z",
  "policy_digest": "sha256:...",
  "crypto_suite_digest": "sha256:...",
  "gdu_digest": "sha256:...",
  "encrypted_payload": "base64:...",
  "authentication_tag": "base64:..."
}
```

**Encrypted Payload (before encryption):**
```json
{
  "inner_message_type": "network.message.gdu_query",
  "query": {
    "definition_id": "entity.car",
    "version": "1.0.0"
  },
  "nonce": "770g0622-g40d-63f6-c938-668877662222"
}
```

**Encryption Process:**
1. Serialize inner message (canonical JSON)
2. Compute inner_hash = hash(inner_message)
3. Encrypt: ciphertext = encrypt(inner_message, shared_secret)
4. Compute auth_tag = mac(ciphertext + envelope_header, shared_secret)
5. Assemble envelope with ciphertext and auth_tag

**Decryption Process:**
1. Verify sequence_number > last_seen
2. Verify timestamp within window
3. Verify gdu_digest matches local
4. Verify policy_digest matches known policy
5. Recompute auth_tag and compare
6. Decrypt ciphertext
7. Validate inner message structure

**Failure Modes:**
- Sequence number out of order → Reject (replay)
- Timestamp expired → Reject
- GDU digest mismatch → Reject
- Policy digest unknown → Reject
- Authentication tag mismatch → Reject (tampering)
- Decryption failure → Reject

---

### Phase 3: Integrity + Replay Protection

**Integrity Mechanisms:**

1. **Authentication Tag:**
   - HMAC or AEAD tag
   - Covers entire envelope (header + ciphertext)
   - Prevents tampering

2. **Sequence Number:**
   - Monotonically increasing per connection
   - Prevents replay attacks
   - Window-based acceptance (allow small reordering)

3. **Timestamp:**
   - Bounded window (±30 seconds)
   - Prevents stale message replay

4. **Nonce:**
   - Per-message unique value
   - Tracked in bloom filter
   - Prevents duplicate processing

**Replay Protection:**
```python
def validate_envelope(envelope, connection_state):
    # Check sequence number
    if envelope.sequence_number <= connection_state.last_sequence:
        raise ReplayError("Sequence number too old")
    
    # Check timestamp
    if abs(envelope.timestamp - now()) > 30:
        raise ReplayError("Timestamp out of window")
    
    # Check nonce
    if nonce_registry.contains(envelope.nonce):
        raise ReplayError("Nonce reused")
    
    # Update state
    connection_state.last_sequence = envelope.sequence_number
    nonce_registry.add(envelope.nonce)
```

---

### Phase 4: Policy Enforcement Using GDU

**Policy Binding:**

Every message is bound to a peer policy from GDU:

```json
{
  "policy_digest": "sha256:hash_of_policy_definition"
}
```

**Policy Enforcement Flow:**

1. **Message Receipt:**
   - Extract policy_digest from envelope
   - Resolve policy from GDU using digest
   - If policy not found → Reject

2. **Policy Evaluation:**
   - Load policy definition from GDU
   - Check sender_identity against policy.allowed_peers
   - Verify message_type allowed by policy
   - Check rate limits
   - Verify compliance with policy.requirements

3. **Policy Violation:**
   - Emit security event
   - Increment violation counter
   - Apply policy.violation_action:
     - `warn`: Log but continue
     - `rate_limit`: Throttle sender
     - `disconnect`: Close connection
     - `ban`: Blacklist sender identity

**Example Policy Enforcement:**
```python
def enforce_policy(envelope, sender_connection):
    # Resolve policy
    policy = gdu.resolve(envelope.policy_digest)
    if not policy:
        raise PolicyError("Unknown policy")
    
    # Check allowlist
    if sender_connection.identity not in policy.allowed_peers:
        if policy.default_action == "reject":
            raise PolicyError("Sender not allowed")
    
    # Check rate limit
    if sender_connection.message_count > policy.rate_limit:
        if policy.violation_action == "disconnect":
            sender_connection.close()
            raise PolicyError("Rate limit exceeded")
    
    # Check message type
    if envelope.inner_message_type not in policy.allowed_message_types:
        raise PolicyError("Message type not allowed")
```

---

## Receipt Binding to GDU

### Receipt Purpose

A **receipt** is a cryptographic proof that:
1. Message was received
2. Message was processed
3. Processing occurred under specific GDU state
4. Processing complied with specific policy

### Receipt Structure

```json
{
  "receipt_id": "receipt-20260109-123456-xyz",
  "message_type": "network.message.receipt",
  "version": "1.0.0",
  "original_envelope_id": "envelope-20260109-123456-abc",
  "original_sender": "network.node.peer_abc123",
  "recipient": "network.node.peer_xyz789",
  "timestamp": "2026-01-09T12:35:01Z",
  "processing_result": "success",
  "bindings": {
    "peer_identity_digest": "sha256:hash_of_sender_identity_def",
    "policy_digest": "sha256:hash_of_policy_def",
    "crypto_suite_digest": "sha256:hash_of_crypto_suite_def",
    "active_gdu_digest": "sha256:current_gdu_state"
  },
  "signature": "ed25519:..."
}
```

### Binding Components

#### 1. Peer Identity Digest

**What it binds:**
- Sender node identity definition from GDU
- Ensures sender identity hasn't changed since message

**Computation:**
```python
peer_identity_digest = hash(
    gdu.resolve(sender_identity).canonical_json()
)
```

**Verification:**
```python
sender_def = gdu.resolve(receipt.original_sender)
if hash(sender_def) != receipt.bindings.peer_identity_digest:
    raise IntegrityError("Sender identity changed")
```

---

#### 2. Policy Digest

**What it binds:**
- Peer policy definition from GDU
- Ensures policy was applied correctly

**Computation:**
```python
policy_digest = hash(
    gdu.resolve(policy_id).canonical_json()
)
```

**Verification:**
```python
policy_def = gdu.resolve_by_digest(receipt.bindings.policy_digest)
if not policy_def:
    raise IntegrityError("Policy definition not found")
# Verify policy was applied correctly
assert envelope.policy_digest == receipt.bindings.policy_digest
```

---

#### 3. Crypto Suite Digest

**What it binds:**
- Crypto suite definition from GDU
- Ensures correct algorithms used

**Computation:**
```python
crypto_suite_digest = hash(
    gdu.resolve(crypto_suite_id).canonical_json()
)
```

**Verification:**
```python
crypto_def = gdu.resolve_by_digest(receipt.bindings.crypto_suite_digest)
if not crypto_def:
    raise IntegrityError("Crypto suite definition not found")
# Verify algorithms match
assert envelope.crypto_suite_digest == receipt.bindings.crypto_suite_digest
```

---

#### 4. Active GDU Digest

**What it binds:**
- Complete GDU state at processing time
- Ensures reproducible interpretation

**Computation:**
```python
active_gdu_digest = compute_gdu_digest()  # From Phase 7
```

**Verification:**
```python
# Receipt proves message was processed under specific GDU
if receipt.bindings.active_gdu_digest != expected_gdu_digest:
    # GDU states differ - meanings may differ
    raise GDUMismatchWarning(
        "Receipt from different GDU state. "
        "Semantic interpretation may differ."
    )
```

---

### Receipt Lifecycle

1. **Message Received:** Envelope arrives and is validated
2. **Message Processed:** Inner message executed (e.g., GDU query answered)
3. **Receipt Generated:**
   - Compute all digests
   - Record processing result
   - Sign receipt
4. **Receipt Transmitted:** Send back to sender
5. **Receipt Verified:** Sender validates receipt signature and bindings
6. **Receipt Archived:** Both parties store receipt for audit

---

### Receipt as Proof

Receipts provide:

**Non-Repudiation:**
- Recipient cannot deny receiving message
- Recipient signature proves acknowledgment

**Audit Trail:**
- Immutable record of communication
- Binds to exact GDU state
- Enables compliance verification

**Dispute Resolution:**
- Both parties have cryptographic proof
- Third party can verify without trust
- GDU state reproducible from digest

**Example Dispute:**
```
Sender: "You processed my message under wrong policy"
Recipient: "Here's receipt with policy_digest. That was the active policy."
Auditor: Resolves policy_digest → Verifies correct policy was used
```

---

## Network Security Guarantees

### Guarantee 1: Identity Verification

**Property:** All network participants have cryptographically verified identities.

**Enforcement:**
- Identity definitions in GDU
- Signature verification at handshake
- Public key resolution from GDU

**Violation Detection:**
- Missing identity → Connection rejected
- Invalid signature → Connection rejected
- Identity not in GDU → Connection rejected

---

### Guarantee 2: End-to-End Encryption

**Property:** All messages encrypted between endpoints.

**Enforcement:**
- Handshake establishes shared secret
- Encrypted envelope for all messages
- Crypto suite from GDU

**Violation Detection:**
- Plaintext message → Rejected
- Wrong crypto suite → Rejected
- Decryption failure → Connection closed

---

### Guarantee 3: Replay Protection

**Property:** Each message processed at most once.

**Enforcement:**
- Sequence numbers
- Nonce tracking
- Timestamp validation

**Violation Detection:**
- Duplicate sequence → Rejected
- Reused nonce → Rejected
- Stale timestamp → Rejected

---

### Guarantee 4: Policy Compliance

**Property:** All communication complies with GDU policies.

**Enforcement:**
- Policy resolution from GDU
- Policy evaluation before processing
- Policy digest in receipts

**Violation Detection:**
- Unknown policy → Rejected
- Policy violation → Action per policy
- Policy bypass attempt → Security event

---

### Guarantee 5: GDU State Binding

**Property:** All network activity bound to specific GDU state.

**Enforcement:**
- GDU digest in handshake
- GDU digest in every envelope
- GDU digest in receipts

**Violation Detection:**
- Digest mismatch → Connection refused
- Stale GDU → Warning + potential rejection
- Missing digest → Rejected

---

## Implementation Phases

### Phase 1: GDU Update Security Foundation

**Status:** Planning  
**Priority:** Critical  
**Blocking:** All GDU modifications

**Deliverables:**
1. Implement Phases 1-4 of Spine-gated update flow
2. Build watch-based approval terminal interface
3. Implement authorization object system
4. Add anti-replay and anti-rollback enforcement
5. Create audit logging for all updates

**Success Criteria:**
- No unauthorized GDU update possible
- All updates have human approval
- Full audit trail exists
- Anti-rollback verified

---

### Phase 2: Overlay Network Foundation

**Status:** Planning  
**Priority:** High  
**Dependencies:** GDU network definitions created

**Deliverables:**
1. Implement ENKI addressing scheme
2. Build handshake protocol
3. Implement encrypted envelope system
4. Add replay protection
5. Create receipt generation and verification

**Success Criteria:**
- Nodes can establish authenticated connections
- All messages encrypted
- Replay attacks prevented
- Receipts verifiable

---

### Phase 3: Policy Enforcement Integration

**Status:** Planning  
**Priority:** High  
**Dependencies:** Phase 1, 2 complete

**Deliverables:**
1. Implement policy resolution from GDU
2. Build policy evaluation engine
3. Add policy violation handling
4. Integrate with network layer
5. Add policy-based routing

**Success Criteria:**
- All messages policy-checked
- Policy violations handled correctly
- Policy changes propagate to network
- Audit trail includes policy compliance

---

### Phase 4: Advanced Features

**Status:** Planning  
**Priority:** Medium  
**Dependencies:** Phase 1, 2, 3 complete

**Deliverables:**
1. Implement dual-run conformance testing (Phase 5)
2. Add GDU replication over overlay network
3. Build distributed admission ceremony
4. Add multi-witness approval
5. Implement policy-based routing optimization

**Success Criteria:**
- Conformance testing operational
- GDU replicates reliably
- Distributed approval works
- Network performance acceptable

---

## Explicitly Out of Scope

This specification does NOT cover:

- **Routing algorithms:** How messages traverse the network (future doc)
- **GDU replication protocol:** How GDU synchronizes across nodes (future doc)
- **Consensus mechanisms:** How distributed approval works (future doc)
- **Network discovery:** How nodes find each other (future doc)
- **Performance optimization:** Caching, batching, compression (future doc)
- **Network monitoring:** Metrics, telemetry, health checks (future doc)

---

## Integration Summary

This specification extends:

**GDU Core (doc 25):**
- Adds update security layer
- Defines spine-gated admission
- Enforces fail-closed updates

**Library Structure (doc 26):**
- Adds network/ library definitions
- Defines policy/ governance
- Enables network operations

**Result:**
- Secure, auditable GDU updates
- Identity-based overlay network
- Cryptographic binding to GDU state
- End-to-end encryption and authentication

---

## Appendix A: Update Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         LDU (Drafts)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
            ┌────────────────────────┐
            │  Phase 1: Intake       │
            │  - Assign tracking ID   │
            │  - Compute hash         │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 2: Canonical+   │
            │  Validation            │
            │  - Schema check         │
            │  - Canonicalize         │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 3: Dependency+  │
            │  Authority             │
            │  - Resolve deps         │
            │  - Check authority      │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 4: Diff+Risk    │
            │  - Compute diff         │
            │  - Classify risk        │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 5: Dual-Run     │
            │  (Optional)            │
            │  - Test in shadow       │
            │  - Verify conformance   │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 6: Watch-Based  │
            │  Approval              │
            │  - Physical presence    │
            │  - Sign digests         │
            │  - Create authorization │
            └────────────┬───────────┘
                         ↓
            ┌────────────────────────┐
            │  Phase 7: Atomic       │
            │  Activation            │
            │  - Verify auth          │
            │  - Atomic commit        │
            │  - Update GDU digest    │
            └────────────┬───────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    GDU (Production)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Network Message Flow

```
Node A                                            Node B
  |                                                 |
  |--- Handshake Request ------------------------->|
  |    (identity, nonce, crypto_suite, gdu_digest) |
  |                                                 |
  |<-- Handshake Response -------------------------|
  |    (identity, nonce, crypto_suite, gdu_digest) |
  |                                                 |
  | [Shared secret derived]                         |
  |                                                 |
  |--- Encrypted Envelope ------------------------->|
  |    (policy_digest, crypto_digest, gdu_digest)  |
  |    [encrypted: GDU Query for entity.car]       |
  |                                                 |
  |                              [Process query]    |
  |                              [Generate receipt] |
  |                                                 |
  |<-- Receipt -------------------------------------|
  |    (bindings: identity, policy, crypto, GDU)   |
  |    (signature, timestamp)                       |
  |                                                 |
  | [Verify receipt]                                |
  | [Archive for audit]                             |
```

---

## Appendix C: Security Event Types

| Event | Severity | Trigger | Response |
|-------|----------|---------|----------|
| `UnauthorizedUpdateAttempt` | CRITICAL | Update without valid authorization | Reject + Alert |
| `SignatureVerificationFailed` | CRITICAL | Invalid signature | Reject + Alert |
| `AntiRollbackViolation` | CRITICAL | Attempt to decrease version | Reject + Alert |
| `GDUDigestMismatch` | HIGH | GDU state differs between peers | Refuse connection |
| `PolicyViolation` | MEDIUM | Message violates peer policy | Per policy action |
| `ReplayDetected` | MEDIUM | Duplicate nonce or sequence | Reject message |
| `AuthorizationExpired` | LOW | Authorization past TTL | Reject + Log |
| `UnknownIdentity` | LOW | Identity not in GDU | Reject connection |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-09 | 1.0.0 | Initial specification |

---

**End of GDU Update Security & ENKI Overlay Network Specification**

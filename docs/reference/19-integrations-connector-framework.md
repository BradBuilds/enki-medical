# Integrations & Connector Framework (Phase 4+)

**ENKI Specification #21**

**Status:** Phase 4+ (Post-Spine, Post-Storage)  
**Dependencies:** Phase 3 Storage Validation (LOCKED)

---

## Overview

ENKI Node can be extended to ingest externally generated JSON assertions from on-site systems (LAN / OT network) through a strictly governed connector framework.

This capability is **post-spine** and **post-storage**: it is enabled only after the deterministic spine and the locked storage contract are proven stable.

**Connectors do not change ENKI's truth model** — they provide a controlled way to receive, validate, and persist external inputs without introducing schema drift or interpretation.

---

## What "Integration" Means in ENKI

ENKI integrations operate under strict constraints:

### Local-only ingestion
Integrations operate within the customer environment.

### No public exposure
ENKI does not provide internet-facing endpoints.

### No SaaS dependency
Integrations do not require cloud services or telemetry.

### Definition-governed meaning
Any accepted structure must be definition-backed and versioned.

**ENKI may accept externally generated JSON only through fail-closed ingestion gates.**

Raw payloads can be retained immutably as audit truth, while structured projections are optional, derived, and enabled only after verified stability and approved definitions.

---

## Raw Truth vs Projected Truth

ENKI distinguishes two persistence layers for integrations:

### 1) Raw Truth (Immutable Ingest Ledger)

Represents exactly what was received, with full provenance and verification metadata.

**Properties:**
- Stored as received (JSON)
- Append-only, immutable
- Fully stamped and auditable
- Safe under vendor payload changes
- Always available for replay and rebuild

**Purpose:** Authoritative record of what external systems provided.

### 2) Projected Truth (Derived Structured Tables — Optional)

Structured, queryable tables derived from raw truth.

**Properties:**
- Created only when explicitly enabled
- Versioned mappings, rebuildable from raw
- Additive evolution by default
- Never authoritative over raw truth

**Purpose:** Convenience layer for structured queries and reporting.

**Invariant:** Raw truth is the foundation. Projections are convenience layers.

---

## Gated Ingestion Pipeline (Fail-Closed)

All connector ingestion follows a strict gating model:

### Gate A — Transport & Authentication

**Validation:**
- Signature / token verification (provider-specific)
- Optional allowlists and local-network constraints

**Outcome:**
- **If Gate A fails:** Payload is rejected (or quarantined) and the operator is notified.

---

### Gate B — Envelope & JSON Validity

**Validation:**
- Payload must be valid JSON
- Size and safety limits enforced
- Required envelope stamp fields present
- Dedupe key resolvable (or hash fallback)

**Outcome:**
- **If Gate B passes:** Payload is written to the immutable raw ingest ledger.
- **If Gate B fails:** Payload is quarantined and the operator is notified.

---

### Gate C — Mapping & Projection Validity (Optional)

Projection writes occur only when:

- Connector is verified and active
- Mapping is approved and versioned
- Projection is explicitly enabled
- Field transforms succeed (types/constraints)

**Outcome:**
- **If Gate C fails:** No projection writes occur. Raw truth remains preserved. The operator is notified.

---

## Invariants

**Invariant 1:** No verified JSON → no raw truth.

**Invariant 2:** No verified mapping → no structured projection.

**Invariant 3:** No approved definition → no execution.

These invariants ensure ENKI's fail-closed security model remains intact during integration.

---

## Connector States

Each connector exists in a visible, audited state:

### TESTING
- Capturing sample payloads
- Not writing projections
- Used for connector development and verification

### VERIFIED_RAW
- Auth + JSON validation proven
- Raw ledger enabled
- No structured projections yet

### ACTIVE_PROJECTION
- Versioned mapping enabled
- Structured projections allowed
- Full operational mode

**State transitions are explicit, audited, and reversible** (rollback activates a prior definition version).

---

## Intelligent Connector Agent (Optional, Post-Spine)

ENKI may include an optional **Connector Agent** that assists operators through a VS Code-style chat interface to:

- Test webhook/poller connectivity
- Capture real sample payloads
- Propose dedupe keys and promoted fields
- Draft versioned connector/mapping definitions
- Recommend whether projections are warranted

### Safety Rule

**The agent is not an authority and cannot bypass the spine.**

- It proposes definitions
- The spine enforces execution
- If the agent detects JSON/mapping failure, it must notify the operator
- Projections remain blocked until resolution

**The agent accelerates definition creation—it does not replace validation.**

---

## Operator Visibility (Required)

The UI must expose:

### Connector Status
- Current state (TESTING / VERIFIED_RAW / ACTIVE_PROJECTION)
- State transition history
- Approval timestamps

### Ingestion Metrics
- Ingest rate (payloads/minute)
- Error rate (failed validations)
- Quarantined payload counts

### Projection Health
- Projection lag (raw vs projected)
- Blocked-write reasons
- Recent validation failures with stamped provenance

**This ensures integrations remain observable, auditable, and deterministic.**

---

## Integration Security Model

### No Network Exposure

Connectors operate within the customer's LAN/OT network.  
ENKI does not provide public ingestion endpoints.

### Definition-First Authorization

Every connector must:
- Have an approved definition pack
- Specify what data it provides
- Declare versioned schemas
- Pass validation before persistence

### Fail-Closed Gates

**If any gate fails:**
- No data persists
- Operator is notified immediately
- System does not silently degrade

### Raw Truth as Audit Foundation

**Even if projections fail:**
- Raw truth remains immutable
- Full replay is always possible
- No data loss from mapping errors

---

## Use Cases

### Medical Device Integration (OT Network)

**Scenario:** Hospital has on-site medical devices generating JSON telemetry.

**ENKI Integration:**
1. Device sends JSON to ENKI connector (LAN only)
2. Gate A validates device signature
3. Gate B writes raw truth to immutable ledger
4. Gate C (optional) projects structured data for queries
5. All steps are audited and provable

**Result:** Medical data remains on-site, validated, and auditable without cloud exposure.

---

### Industrial IoT Sensors (OT Network)

**Scenario:** Manufacturing facility has sensors generating operational data.

**ENKI Integration:**
1. Sensors send JSON to ENKI connector (local network)
2. Raw truth preserves exact sensor outputs
3. Projections enable structured queries
4. No cloud dependency or remote admin access

**Result:** Operational data sovereignty with full audit trail.

---

### Third-Party SaaS Webhooks (Opt-In)

**Scenario:** Customer uses external SaaS that provides webhooks.

**ENKI Integration:**
1. ENKI provides webhook endpoint (customer's infrastructure)
2. SaaS sends JSON payloads to ENKI
3. Raw truth captures exactly what SaaS provided
4. Projections remain optional
5. Customer retains authoritative copy

**Result:** Customer controls canonical record, even when using external services.

---

## Relationship to ENKI Spine

The connector framework is **post-spine**, meaning:

### The Spine Remains Unchanged

- No mutable schemas
- No credential-only authority
- No silent ingestion
- No bulk export

### Connectors Are Governed by the Spine

- Definitions are immutable
- Validation is mandatory
- Fail-closed behavior is enforced
- Audit chain is preserved

**The connector framework does not weaken ENKI's structural security—it extends it to external data sources under the same strict rules.**

---

## Phase 4+ Roadmap

### Phase 4A: Raw Truth Ingestion (TESTING State)

- Implement Gate A (transport/auth)
- Implement Gate B (JSON validation)
- Implement raw truth ledger
- Operator visibility for quarantined payloads

### Phase 4B: Connector Agent (Assisted Definition Creation)

- VS Code-style chat interface
- Sample payload capture
- Dedupe key proposals
- Draft definition generation

### Phase 4C: Projected Truth (ACTIVE_PROJECTION State)

- Implement Gate C (mapping validation)
- Versioned mapping engine
- Structured projections
- Replay and rebuild capabilities

### Phase 4D: Production Hardening

- Connector state management
- Rollback and versioning
- Full operator visibility
- Performance optimization

---

## Documentation Cross-References

**For security model:**  
→ Security Architecture  
→ Attack Surface Reduction

**For storage layer:**  
→ [Storage Contract Specification](10-storage-contract-spec.md)  
→ Phase 3 Storage Validation LOCK

**For definition resolution:**  
→ [Validation Contract](02-validation-contract.md)  
→ [Identity Pack Specification](04-identity-pack-spec.md)

**For executive summary:**  
→ Executive Summary

---

## One-Sentence Summary

**ENKI's connector framework enables fail-closed, definition-governed ingestion of external JSON data—preserving raw truth immutably while allowing optional structured projections under strict validation.**

# ENKI Node Security Architecture

**Status:** AUTHORITATIVE  
**Version:** 1.0.0  
**Date:** 2026-01-03  
**Purpose:** Security model, threat analysis, and trust boundaries for ENKI Node

---

## Document Purpose

This document defines the complete security architecture for ENKI Node.

It is the authoritative reference for:
- Security reviewers
- Auditors
- Procurement teams
- Compliance officers
- Integration partners

---

## Executive Summary

ENKI Node's security model is **architectural, not aspirational**.

Security is achieved through:
1. **Physical constraints** — Hardware enforces rules code cannot bypass
2. **Deterministic validation** — Truth cannot exist without proof
3. **Human verification loops** — Automation cannot escalate authority
4. **Fail-closed behavior** — Invalid input stops communication, not execution
5. **Limited capability** — The system cannot do what it was never designed to do

**Key Principle:**  
If a human cannot physically access the node, they cannot compromise truth.

---

## Hardware as Security Component

### The Hardware Is Not "Infrastructure"

In traditional systems:
- Hardware runs software
- Software enforces security
- Compromise happens in software

In ENKI Node:
- Hardware **is part of the security model**
- Physical access **is a security requirement**
- Remote attacks have **no viable surface**

### Reference Hardware Specification

ENKI Node is delivered as a **pre-built appliance** or **certified build specification**.

**Minimum Certified Specification:**

| Component | Requirement | Security Purpose |
|-----------|-------------|------------------|
| CPU | x86_64 or ARM64, ≥ 4 cores | Deterministic validation (CPU-bound) |
| RAM | 16 GB minimum | Isolated runtime |
| Storage | NVMe SSD (dedicated, encrypted) | Encrypted at rest, isolated |
| OS | Hardened Linux (immutable root) | Read-only system prevents tampering |
| Network | Ethernet + optional Wi-Fi | Physical network control |
| GPU | Optional (non-authoritative) | Never used for truth validation |
| TPM | Preferred | Hardware attestation |
| Form Factor | Small-form-factor / industrial PC | Physical presence enforcement |

⚠️ **Critical:** GPU acceleration is **never authoritative**.  
All truth validation occurs on **CPU-bound deterministic logic**.

### Immutable System Layout

ENKI Node enforces separation of concerns at the **filesystem level**:

```
/boot        → Signed boot artifacts (verified at startup)
/system      → Read-only OS (cannot be modified at runtime)
/definitions → Immutable definition packs (version-locked)
/runtime     → Ephemeral execution (disposable state)
/data        → Canonical truth storage (isolated, encrypted)
/logs        → Append-only audit logs (tamper-evident)
```

**Key Properties:**
- System partitions are **read-only**
- Definition packs are **version-locked** (no silent updates)
- Runtime state is **disposable** (no persistent execution artifacts)
- Truth data is **isolated** (cannot leak into runtime)
- Logs are **append-only** (modification is detectable)

---

## Human-Proof Security Model

### Core Assumption

> **If a human cannot physically access the node, they cannot compromise truth.**

This is not accidental. It is architectural.

### Why This Works

1. **No Remote Mutation Authority**
   - No API keys can bypass validation
   - No tokens can override definitions
   - No credentials can alter canonical truth

2. **No Bulk Export Path**
   - No database dumps
   - No full-state snapshots
   - No streaming truth extraction

3. **Physical Presence Required for:**
   - Definition pack installation
   - System image replacement
   - Full truth store access
   - Hardware migration

4. **Human Verification Loops**
   - Critical operations require operator confirmation
   - No silent automated escalation
   - Explicit intent required for writes

---

## Why Bots Cannot Attack ENKI Node

### No Public Attack Surface

**What ENKI Does NOT Expose:**
- ❌ No cloud endpoints
- ❌ No public database ports
- ❌ No admin UI over the network
- ❌ No credential-based remote write access
- ❌ No API marketplace integrations
- ❌ No webhook receivers
- ❌ No server-side scripting

**There is nothing for bots to enumerate, brute-force, or scrape.**

### No Credential-Only Authority

**What ENKI Does NOT Allow:**
- ❌ API keys to mutate truth
- ❌ Tokens to bypass validation
- ❌ Remote admin roles to override rules
- ❌ OAuth flows to escalate privileges
- ❌ Session persistence without physical re-auth

**Even authenticated requests cannot violate canonical definitions.**

### No Bulk Export Path

**What ENKI Does NOT Support:**
- ❌ Dumping entire databases
- ❌ Snapshotting truth stores remotely
- ❌ Streaming full state externally
- ❌ Backup APIs that return raw data
- ❌ CSV/Excel export of canonical truth

**Truth is queryable, not exfiltratable.**

### Attack Resistance By Design

| Attack Vector | Traditional Systems | ENKI Node |
|---------------|---------------------|-----------|
| Botnet probing | Exposed APIs, credential stuffing | No public surface |
| Supply-chain exploits | Runtime dependency injection | Immutable definitions |
| Credential compromise | Remote access, privilege escalation | Physical presence required |
| Database exfiltration | Bulk export, backup leaks | No meaningful raw data |
| API abuse | Rate limits, monitoring | Definition-locked validation |
| Zero-day exploits | Patch cycles, downtime | Limited capability, fail-closed |

---

## Deterministic Communication Control

### JSON Soft Validation Layer (Pre-Commit Gate)

All communication into ENKI Node passes through a **JSON soft-validation process** before it is allowed to:
- Touch canonical truth
- Write to disk
- Trigger downstream processes

#### How It Works

1. **Inbound JSON is intercepted**
2. **Payload is checked against:**
   - Known schemas
   - Definition libraries
   - Structural validity
   - Semantic constraints
3. **If validation fails:**
   - ❌ No data is written
   - ❌ No partial state is created
   - ❌ No retries escalate automatically
   - ❌ Communication is halted
4. **The system explicitly reports:**
   - What failed
   - Why it failed
   - That persistence was denied

**This ensures fail-closed behavior by default.**

### Explicit Commit Requirement

ENKI Node **does not infer intent**.

Data is only committed when **all three conditions are met**:

1. **Schema Validity**  
   The structure exactly matches an approved definition.

2. **Definition Authorization**  
   The data corresponds to a known, versioned definition pack.

3. **Explicit Commit Intent**  
   The operation is explicitly declared as write-authorized.

**If any condition is missing, ENKI:**
- Rejects the operation
- Preserves system integrity
- Leaves the database unchanged

### Why This Prevents Database Corruption

**Traditional systems fail because:**
- Invalid data partially commits
- Schemas evolve silently
- APIs accept "close enough" payloads
- Errors occur **after** persistence

**ENKI inverts this flow:**
- No valid definition → no commit → no corruption

**There is no concept of:**
- "Fix it later"
- "Recover from bad writes"
- "Clean up inconsistent state"

**Invalid data never enters the system.**

---

## Communication Halt as a Security Feature

When validation fails, ENKI **does not degrade gracefully**.  
**It stops communication.**

This is intentional.

### Effects

- Prevents cascading failures
- Stops automated retry storms
- Blocks bot probing
- Forces human review
- Preserves forensic clarity

### What Systems Receive

```
ERROR: Schema validation failed.
Reason: Field 'timestamp' does not match ISO 8601 format.
State: No persistence occurred.
Action Required: Human review of payload.
```

**Systems interacting with ENKI receive a clear signal:**  
The communication channel is invalid. No state change occurred.

---

## Interactive API Connection System (Human-Guided)

ENKI Node includes a **terminal-based, conversational API integration system** designed to eliminate blind automation.

Rather than preloading credentials or auto-connecting to external services, operators **explicitly instruct ENKI** on what to connect to.

### Operator Workflow

1. **Operator opens the ENKI terminal**

2. **Operator states intent in plain language:**
   - "Connect to the Salesforce API"
   - "Connect to internal telemetry endpoint"

3. **ENKI:**
   - Inspects API structure
   - Builds the JSON contract
   - Defines schemas
   - Proposes validation rules

4. **Operator reviews and approves:**
   - Read-only access
   - Write access
   - No persistence
   - Canonical storage enabled

**Nothing proceeds without human confirmation.**

### Controlled Database Access Decision

After an API is defined, ENKI requires an **explicit decision**:

**Options:**

1. **No Storage**  
   Data is validated, processed, and discarded.

2. **On-System Proof Only**  
   Data is used for verification but not retained.

3. **Canonical Storage**  
   Data is written to the truth store under strict schema enforcement.

**This prevents:**
- Accidental large-scale ingestion
- Silent data hoarding
- Regulatory violations
- Storage of unverifiable external data

### Large Data Handling Without Trust Assumptions

When large data volumes are required:

- Storage is **opt-in**
- Schema is **locked before ingestion**
- Validation occurs **per payload**
- Bulk writes are **segmented and verified**
- Partial failures **do not corrupt state**

This allows ENKI to act as:
- A verification gateway
- A selective truth repository
- A numeric proof system

**—not a passive data sink.**

---

## Database Design: Why It Cannot Be "Leaked"

### ENKI Does Not Store Meaningfully Exploitable Raw Data

**Key Properties:**
- Canonical **numeric truth only**
- No free-form text blobs
- No user-generated arbitrary content
- No derived representations stored
- No hidden metadata

### Even If a Disk Were Stolen

1. **Data is encrypted** (at rest, via OS-level encryption)
2. **Truth is meaningless without definitions** (numeric values have no context)
3. **Glyphs are not stored** (rendered deterministically at runtime)
4. **Interpretability requires ENKI itself** (no offline tooling exists)

### Why Full Database Leaks Are Structurally Prevented

**Traditional systems fail because:**
- Databases store **interpreted data**
- Representations are **authoritative**
- Bulk export is **normal**

**ENKI inverts this:**
- Truth is **atomic and numeric**
- Meaning is **derived at runtime**
- No single table is **"useful"**
- No snapshot represents **full context**

**Without:**
- The definitions
- The validation engine
- The rendering rules
- The versioned contracts

**…the data is not actionable.**

---

## Air-Gapped Operation

ENKI Node can operate **fully air-gapped**.

**No Dependencies On:**
- ❌ Internet connectivity
- ❌ Time drift synchronization
- ❌ Remote verification services
- ❌ Licensing call-home
- ❌ Cloud-based secret storage

**Ideal For:**
- Critical infrastructure
- Sovereign environments
- Regulated industries (HIPAA, FedRAMP, ITAR)
- Long-term archival systems
- Classified or defense applications

---

## Why ENKI Does Not Rely on "Security by Software"

### Most Systems Rely On:
- Patches (reactive, never-ending)
- Credentials (stolen, phished, brute-forced)
- Firewalls (bypassed, misconfigured)
- Monitoring (alert fatigue, post-breach detection)

### ENKI Relies On:
- **Determinism** (same input = same output, always)
- **Physical presence** (remote attacks have no surface)
- **Immutable definitions** (no silent behavior changes)
- **Limited capability** (system cannot do what it wasn't designed to do)

### This Reduces:
- Attack surface (nothing to exploit)
- Complexity (fewer moving parts)
- Operational risk (no patches breaking production)
- Unknown failure modes (behavior is provable)

---

## Threat Model

### In Scope (What ENKI Protects Against)

✅ **Bot-driven attacks**  
✅ **Credential stuffing**  
✅ **Database exfiltration**  
✅ **Schema drift**  
✅ **Malformed input ingestion**  
✅ **Silent data corruption**  
✅ **Remote privilege escalation**  
✅ **Supply-chain exploits (runtime)**  
✅ **Automated retry storms**  

### Out of Scope (What ENKI Does NOT Protect Against)

❌ **Physical hardware theft** (disk encryption mitigates)  
❌ **Physical operator coercion** (human trust boundaries)  
❌ **Side-channel attacks** (not a cryptographic vault)  
❌ **Denial of service** (availability is separate from integrity)  
❌ **Social engineering** (human verification is required)  

---

## Failure Modes (Fail-Closed Behavior)

### What Happens When Things Go Wrong

| Failure | Traditional System | ENKI Node |
|---------|-------------------|-----------|
| Invalid JSON | Partial write, retry | Reject, halt communication |
| Schema mismatch | Silent coercion | Reject, no persistence |
| Network timeout | Retry loop, eventual success | No commit, explicit human review |
| Definition missing | Infer, guess, proceed | Reject, require definition |
| Credential expired | Lock out, wait for patch | No remote credential dependency |

**ENKI always fails closed.**  
If validation cannot be proven, the operation does not occur.

---

## ENKI's Security Promise

ENKI Node will **never**:

- Allow bots to mutate truth
- Permit silent remote database access
- Export full state invisibly
- Depend on cloud trust
- Change behavior without definition updates
- Accept credentials as sole authority
- Store unvalidated external data

**If truth matters, it must be physically protected.**  
**ENKI enforces that.**

---

## Why This Matters for Government & Enterprise

This architecture ensures:

✅ **No blind API trust**  
✅ **No automatic data persistence**  
✅ **No schema drift**  
✅ **No bot-driven ingestion**  
✅ **No silent corruption**  
✅ **No ambiguous failure states**  

**Every external connection is:**
- Human-authorized
- Definition-backed
- Auditable
- Reversible (before commit)
- Physically accountable

---

## Summary

ENKI Node treats **communication itself as untrusted** until proven otherwise.

- JSON is validated **before** it is believed
- Definitions are required **before** commitment
- Databases **cannot be corrupted** by malformed input
- Bots **cannot escalate** access
- Humans remain **in control** of integration decisions

**This makes ENKI suitable for environments where external data must be proven before it is allowed to exist.**

---

**END OF SECURITY ARCHITECTURE SPECIFICATION**

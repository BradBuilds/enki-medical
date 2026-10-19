# ENKI Ingestion Contract Specification

**Version:** 1.0.0  
**Status:** ✅ LOCKED (Phase 3 Complete)  
**Date:** 2026-01-01  
**Authority:** Phase 3 implementation lock artifact

---

## Purpose

This document defines the **ingestion boundary** for ENKI's Phase 3 storage implementation. It specifies:

1. What JSONL input is accepted
2. How validation stages process input
3. What guarantees the ingestion pipeline provides
4. What outputs are produced (receipts, chain hash updates)

This contract locks the ingestion interface before Phase 4 APIs are built.

---

## Ingestion Pipeline Overview

```
JSONL Input (stdin)
    ↓
[1] Parse JSONL
    ↓
[2] Map ObservabilityEvent → AuditEvent
    ↓
[3] Validate Against Phase 0-1 Contracts
    ↓
[4] Store Accepted Records (PostgreSQL)
    ↓
[5] Generate Receipt
    ↓
[6] Update Chain Hash
    ↓
Receipt Output (with outcome)
```

---

## Input Format

### JSONL (JSON Lines)

**Format:** One JSON object per line, newline-separated

**Example:**
```jsonl
{"event_type": "assertion.proposed", "severity": "info", "timestamp": "2026-01-01T12:00:00Z", "tenant_id": "test-tenant", "actor_id": "user:alice", "payload": {...}}
{"event_type": "pack.loaded", "severity": "info", "timestamp": "2026-01-01T12:00:01Z", "tenant_id": "test-tenant", "actor_id": "system:loader", "payload": {...}}
```

**Encoding:** UTF-8  
**Line Endings:** LF (`\n`) or CRLF (`\r\n`)  
**Empty Lines:** Ignored (skipped)  
**Comments:** Not supported (JSON does not support comments)

### ObservabilityEvent Schema (Phase 2)

**MUST Fields:**
- `event_type` (string, dot notation, e.g., `assertion.proposed`)
- `severity` (string, one of: `info`, `warning`, `error`, `critical`)
- `timestamp` (ISO 8601 string with timezone, e.g., `2026-01-01T12:00:00Z`)
- `tenant_id` (string, identifies tenant boundary)
- `actor_id` (string, identifies who/what triggered event)

**SHOULD Fields:**
- `payload` (object, event-specific data)
- `context` (object, optional contextual metadata)
- `sequence` (integer, for deterministic ordering within batch)

**MAY Fields:**
- `event_id` (string, UUID or similar)
- Additional fields for observability tooling

**Forbidden:**
- `rid` (assigned during storage, not provided by caller)
- `commit_time` (assigned during storage, not provided by caller)

---

## Validation Stages

### Stage 1: JSONL Parsing

**Input:** Raw bytes from stdin  
**Process:**
1. Read line-by-line
2. Attempt JSON parse for each line
3. Skip empty lines
4. Collect parse errors

**Outcomes:**
- **Success:** Parsed JSON objects collected
- **Failure:** Malformed JSON → rejection with error reason

**Error Reasons:**
- `parse_error.invalid_json` — Not valid JSON syntax
- `parse_error.empty_line` — Empty line (skipped, not error)

### Stage 2: ObservabilityEvent → AuditEvent Mapping

**Input:** Parsed JSON objects  
**Process:**
1. Extract MUST fields (`event_type`, `severity`, `timestamp`, `tenant_id`, `actor_id`)
2. Map `payload` to AuditEvent structure
3. Store original `sequence` in `metadata._enki_observability_sequence` (if present)
4. Exclude `rid` and `commit_time` from input (assigned during storage)

**Outcomes:**
- **Success:** AuditEvent candidate ready for validation
- **Failure:** Missing MUST fields → rejection with error reason

**Error Reasons:**
- `mapping_error.missing_must_field` — Required field absent
- `mapping_error.invalid_type` — Field type mismatch (e.g., severity not string)

**Mapping Rules (Appendix A from Phase 2):**
- ObservabilityEvent.sequence → AuditEvent.metadata._enki_observability_sequence
- ObservabilityEvent.event_id → AuditEvent.metadata._enki_event_id (optional)
- ObservabilityEvent.context → AuditEvent.metadata._enki_context (optional)

### Stage 3: Phase 0-1 Validation

**Input:** AuditEvent candidates  
**Process:**
1. **Schema Validation:** Validate against `audit_event_instance.schema.json`
2. **Vocabulary Validation:** Verify `event_type` exists in `libraries/audit_vocab/`
3. **Severity Validation:** Verify `severity` is one of: `info`, `warning`, `error`, `critical`
4. **Timestamp Validation:** Parse ISO 8601, verify timezone present
5. **Tenant ID Validation:** Non-empty string (format validation deferred to Phase 4)

**Outcomes:**
- **Success:** AuditEvent passes all validation stages
- **Failure:** Validation error → rejection with error reason

**Error Reasons:**
- `validation_error.schema_violation` — Does not conform to audit_event_instance.schema.json
- `validation_error.unknown_event_type` — Event type not defined in audit_vocab pack
- `validation_error.invalid_severity` — Severity not in allowed set
- `validation_error.invalid_timestamp` — Timestamp parse failure or missing timezone
- `validation_error.empty_tenant_id` — Tenant ID is empty string

**Validation Order:** Schema → Vocabulary → Field constraints (deterministic)

### Stage 4: Storage

**Input:** Validated AuditEvent records  
**Process:**
1. Begin PostgreSQL transaction
2. Assign `rid` (from `audit_events` IDENTITY sequence)
3. Assign `commit_time` (current UTC timestamp)
4. Insert into `audit_events` table
5. Commit transaction

**Outcomes:**
- **Success:** AuditEvent stored with assigned RID and commit_time
- **Failure:** Database error → transaction rollback, rejection with error reason

**Error Reasons:**
- `storage_error.db_connection_failed` — Cannot connect to PostgreSQL
- `storage_error.insert_failed` — INSERT statement failed (constraint violation, disk full, etc.)
- `storage_error.transaction_failed` — Transaction commit failed

**Atomicity Guarantee:**
- All accepted records in a single ingestion batch are stored in one transaction
- If any storage error occurs, entire batch is rolled back (no partial storage)

### Stage 5: Receipt Generation

**Input:** Storage transaction outcome  
**Process:**
1. Collect accepted AuditEvent RIDs
2. Collect rejected events with error reasons
3. Determine receipt outcome:
   - `FULL_ACCEPT` — All events accepted
   - `PARTIAL_ACCEPT` — Some accepted, some rejected
   - `FULL_REJECT` — All events rejected
4. Compute receipt digest (RFC 8785 canonical JSON)
5. Assign receipt RID (from `receipts` IDENTITY sequence)
6. Store receipt in `receipts` table

**Outcomes:**
- **Success:** Receipt generated with unique RID
- **Failure:** (Should not occur; receipt generation is final stage)

**Receipt Structure:**
```json
{
  "rid": 1,
  "tenant_id": "test-tenant",
  "outcome": "FULL_ACCEPT",
  "accepted_items": [
    {"rid": 101, "event_type": "assertion.proposed"}
  ],
  "rejected_items": [],
  "receipt_digest": "sha256:abcdef...",
  "chain_hash": "sha256:123456...",
  "previous_chain_hash": "sha256:000000...",
  "commit_time": "2026-01-01T12:00:00.123456Z"
}
```

### Stage 6: Chain Hash Update

**Input:** Receipt digest + previous chain hash  
**Process:**
1. Retrieve current chain state for tenant (from `chain_state` table)
2. Compute new chain hash: `SHA256(previous_chain_hash || receipt_digest)`
3. Update `chain_state` with new chain hash and receipt RID
4. Store `previous_chain_hash` in receipt for verification

**Outcomes:**
- **Success:** Chain hash updated, receipt includes chain linkage
- **Failure:** (Should not occur; chain update is atomic with receipt storage)

**Genesis Hash (First Receipt):**
- If no prior chain state exists: `previous_chain_hash = SHA256("ENKI_GENESIS_" || tenant_id)`
- First receipt establishes chain foundation

**Chain Hash Formula:**
```python
chain_hash_n = SHA256(chain_hash_{n-1} || receipt_digest_n)
```

**Determinism Guarantee:**
- RFC 8785 (JCS) canonical JSON ensures identical receipt digests across systems
- Same tenant + same receipt sequence → same chain hash

---

## Guarantees

### 1. Ordering Preservation

**Guarantee:** Receipts are assigned RIDs in submission order

**Implication:**
- `ORDER BY receipts.rid ASC` produces submission-order sequence
- No timestamp-based ambiguity
- Cursor pagination uses integer RID ordering (displayed as compact alphanumeric strings)

**Caveat:**
- Single ingestion pipeline assumed (no concurrent ingestion from multiple sources)
- Multi-node ingestion requires coordination (Phase 5 concern)

### 2. Validation Determinism

**Guarantee:** Same input → same validation outcome

**Implication:**
- Replaying JSONL input produces identical accepted/rejected items
- Validation errors are reproducible
- No random or time-dependent validation logic

**Caveat:**
- Assumes vocabulary packs are unchanged (pack versioning required for evolution)

### 3. Transaction Atomicity

**Guarantee:** All accepted records in a batch are stored together or not at all

**Implication:**
- No partial storage of batch (PostgreSQL transaction boundary)
- Receipt always reflects actual storage outcome

**Caveat:**
- Does not guarantee cross-batch atomicity (each ingestion is independent transaction)

### 4. Tamper-Evident Chain

**Guarantee:** Any modification to receipt data invalidates chain hash

**Implication:**
- `verify_chain(tenant_id)` detects tampering
- Chain verification requires only receipts table (no external dependencies)

**Caveat:**
- Database administrator with direct SQL access can corrupt chain (append-only enforced at application layer, not database constraints)

### 5. Tenant Isolation

**Guarantee:** Events for `tenant_id=A` do not affect `tenant_id=B` chain state

**Implication:**
- Each tenant has independent chain hash sequence
- Cross-tenant queries return empty results (application-layer enforcement)

**Caveat:**
- No database-level row security (relies on application code correctness)

---

## Error Handling

### Malformed JSONL

**Error Reason:** `parse_error.invalid_json`

**Example:**
```jsonl
{invalid json}
```

**Receipt Outcome:** `FULL_REJECT` (or `PARTIAL_ACCEPT` if other lines valid)

**Rejected Item:**
```json
{
  "line_number": 1,
  "error": "parse_error.invalid_json",
  "reason": "Expecting property name enclosed in double quotes"
}
```

### Missing Required Fields

**Error Reason:** `mapping_error.missing_must_field`

**Example:**
```jsonl
{"event_type": "assertion.proposed", "severity": "info"}
```
(Missing `timestamp`, `tenant_id`, `actor_id`)

**Receipt Outcome:** `PARTIAL_ACCEPT` (if other events valid)

**Rejected Item:**
```json
{
  "event_type": "assertion.proposed",
  "error": "mapping_error.missing_must_field",
  "reason": "Missing required field: timestamp"
}
```

### Vocabulary Violation

**Error Reason:** `validation_error.unknown_event_type`

**Example:**
```jsonl
{"event_type": "unknown.type", "severity": "info", "timestamp": "2026-01-01T12:00:00Z", "tenant_id": "test", "actor_id": "user:alice"}
```

**Receipt Outcome:** `PARTIAL_ACCEPT` (if other events valid)

**Rejected Item:**
```json
{
  "event_type": "unknown.type",
  "error": "validation_error.unknown_event_type",
  "reason": "Event type 'unknown.type' not defined in audit_vocab pack"
}
```

### Database Connection Failure

**Error Reason:** `storage_error.db_connection_failed`

**Example:** PostgreSQL container not running

**Receipt Outcome:** Ingestion fails completely (no receipt generated)

**User-Visible Error:** Exception raised, ingestion pipeline exits with error

---

## Performance Characteristics

### Single-Node Deployment

**Expected Throughput:** ~1000-10000 events/second (depends on validation complexity, PostgreSQL configuration)

**Bottlenecks:**
1. JSON parsing (CPU-bound)
2. Vocabulary validation (pack loading, disk I/O)
3. PostgreSQL INSERT (disk I/O, transaction commit latency)

**Optimization (Future):**
- Batch INSERT for multiple events (reduce transaction overhead)
- GIN indexes on `audit_events.payload` (faster JSON queries)
- Connection pooling (reduce connection overhead)

### Chain Verification

**Complexity:** O(n) for chain length n

**Expected Time:** ~1-10ms per receipt (depends on receipt size, PostgreSQL query latency)

**Optimization (Phase 5):**
- Checkpoints (verify from latest checkpoint, not genesis)
- Parallel verification (multiple tenants in parallel)

---

## Integration Points

### Phase 0-1 Dependencies

**Vocabulary Packs:**
- `libraries/audit_vocab/` — Event types, severity, field definitions
- Loaded via `core/packs/loader.py`

**Validators:**
- `core/validation/validate_audit_events.py` — Schema + vocabulary validation

**Schemas:**
- `schemas/audit_event_instance.schema.json` — JSON Schema for AuditEvent structure

### Phase 2 Dependencies

**Event Emission:**
- ObservabilityEvent objects from `core/events/` module
- Mapping rules defined in `docs/11-event-emission-spec.md` Appendix A

### Phase 3 Dependencies

**Storage Modules:**
- `storage/ingest/ingestion.py` — Main ingestion pipeline
- `storage/ingest/mapping.py` — ObservabilityEvent → AuditEvent mapper
- `storage/postgres/queries.py` — Database operations (insert, query, verify_chain)
- `storage/crypto/cid.py` — RFC 8785 canonical JSON + SHA-256 hashing
- `storage/crypto/chain.py` — Chain hash computation
- `storage/ids/rid.py` — RID compact alphanumeric encoding (base-55)

**Database Schema:**
- `storage/postgres/schema.sql` — PostgreSQL table definitions

---

## Future Evolution

### Phase 4 API Layer

**Expected Changes:**
- REST endpoint: `POST /ingest` → accepts JSONL body
- Authentication: Tenant ID derived from API key or JWT
- Rate limiting: Requests per minute/hour per tenant
- Async ingestion: Queue-based ingestion with webhook callbacks

**No Breaking Changes Expected:**
- Ingestion contract remains: JSONL → validation → receipt → chain
- API layer is thin wrapper around existing ingestion pipeline

### Phase 5 Federation

**Expected Changes:**
- Multi-node ingestion coordination (distributed transaction IDs)
- Cross-node chain verification (federated checkpoints)
- Tenant ID format standardization (UUID, public key hash, etc.)

**Potential Breaking Changes:**
- Receipt RID → stable transaction ID (txid) migration
- Chain hash algorithm upgrade (SHA-256 → SHA-3, if quantum-resistant requirement)

---

## Testing

### Test Coverage

**Test Suite:** `services/api/tests/test_phase3_milestone*.py`

**Covered Scenarios:**
- ✅ Happy path ingestion (valid events → receipt → chain hash)
- ✅ Partial accept (some valid, some invalid events)
- ✅ Chain continuity (multiple receipts correctly chain)
- ✅ Malformed JSON handling (parse errors)
- ✅ Contract violation (missing required fields)
- ✅ Sequence storage (ObservabilityEvent.sequence preserved)
- ✅ Receipt roundtrip (store + retrieve by RID)
- ✅ Audit event pagination (integer RID ordering)
- ✅ Chain verification success (valid chain)
- ✅ Chain verification detects tampering (corrupted chain hash)
- ✅ Tenant isolation (cross-tenant queries return empty)

**Total:** 16/16 tests passing (Phase 3 Milestone 2 validation)

### Manual Testing

**Command:**
```powershell
echo '{"event_type":"assertion.proposed","severity":"info","timestamp":"2026-01-01T12:00:00Z","tenant_id":"test","actor_id":"user:alice","payload":{}}'  | python -m storage.ingest.ingestion
```

**Expected Output:**
```json
{
  "rid": 1,
  "tenant_id": "test",
  "outcome": "FULL_ACCEPT",
  "accepted_items": [{"rid": 1, "event_type": "assertion.proposed"}],
  "rejected_items": [],
  "receipt_digest": "sha256:...",
  "chain_hash": "sha256:...",
  "commit_time": "2026-01-01T12:00:00.123456Z"
}
```

---

## References

- **Storage Contract:** docs/10-storage-contract-spec.md
- **Event Emission Spec:** docs/11-event-emission-spec.md (Appendix A: ObservabilityEvent → AuditEvent mapping)
- **Validation Contract:** docs/02-validation-contract.md
- **Audit Event Instance Spec:** docs/08-audit-event-instance-spec.md
- **Audit Vocabulary Pack Spec:** docs/07-audit-vocabulary-pack-spec.md
- **Phase 3 Milestone 2 Report:** docs/implementation-reports/2026-01-01-phase3-milestone2-db-validation.md

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-01-01 | Initial ingestion contract locked (Phase 3 complete) |

---

**Status:** ✅ LOCKED — This contract defines Phase 3 ingestion boundary and MUST NOT be modified without governance approval and version increment.

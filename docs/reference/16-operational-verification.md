# 18 — Operational Verification

**Document Status:** Canonical Reference  
**Last Updated:** 2026-01-03  
**Phase Scope:** Phase 3+ (Storage Layer Active)

---

## Purpose

This document explains **how ENKI Node is verified in operational environments**, without redefining architectural behavior.

**This is NOT a test plan.**  
This is documentation for operators, DevOps teams, and auditors who need to understand:

- Why certain tests are skipped
- What database activation means
- How verification differs across phases
- When stress testing is appropriate

---

## Test Categories

ENKI distinguishes between three types of verification:

### 1. Unit Tests (Always Run)

**Scope:** Pure logic with no external dependencies

**Examples:**
- RID encoder/decoder roundtrip
- Base-60 conversion accuracy
- Definition schema validation
- Glyph rendering (deterministic)

**Execution:**
- No environment variables required
- No database connection needed
- No network access required

**Expected Outcome:** 100% pass rate on every commit

---

### 2. Database-Gated Tests (Conditional)

**Scope:** Storage contract verification against live PostgreSQL

**Examples:**
- Ingestion pipeline (JSONL → PostgreSQL)
- Receipt generation and verification
- Audit event chain validation
- RID assignment and retrieval

**Execution Requirement:**

```bash
ENKI_DB_DSN=postgresql://user:pass@localhost:5432/enki_test
```

**If `ENKI_DB_DSN` is NOT set:**
- Tests are **SKIPPED** (not failed)
- Exit code remains 0
- CI/CD pipeline continues normally

**If `ENKI_DB_DSN` IS set:**
- Tests execute against live database
- Database state is modified
- Failures indicate storage contract violations

**Why This Gating Exists:**

- **Developer workflow:** Not everyone needs a running PostgreSQL instance for every commit
- **CI/CD flexibility:** Lightweight validation doesn't require database spin-up
- **Security hygiene:** Database credentials are not assumed to exist
- **Phase isolation:** Phase 1-2 work did not require storage layer

---

### 3. Stress Harness (Explicit Invocation)

**Scope:** Load, concurrency, and boundary condition testing

**Examples:**
- 10,000-record ingestion bursts
- Concurrent writes from multiple processes
- Malformed JSONL edge cases
- Database transaction rollback verification

**Execution:**

```bash
pytest services/api/tests/test_stress_ingestion.py
```

**Purpose:**
- Validate storage layer under realistic load
- Surface race conditions and locking issues
- Verify transaction isolation guarantees
- Test failure modes and recovery paths

**Expected Outcome:**
- Not run in standard CI/CD
- Invoked manually before production deployment
- Used to validate hardware capacity planning

---

## What "SKIPPED" Means

ENKI tests use pytest's skip mechanism to differentiate between:

**❌ FAILED** — Code violated a contract  
**⏭️ SKIPPED** — Precondition not met (database not available)

### Example Output

```
services/api/tests/test_phase3_milestone1.py::test_ingest_single_assertion SKIPPED
services/api/tests/test_phase3_milestone1.py::test_ingest_single_audit_event SKIPPED
services/api/tests/test_phase3_milestone1.py::test_verify_receipt SKIPPED
```

**This is correct behavior.**

### Why Skips Are Not Failures

ENKI's test suite is designed for:
- Developers without local databases
- CI environments that only validate logic
- Quick feedback loops during iteration

**Database-gated tests are opt-in verification, not mandatory gates.**

---

## Phase 3 vs Phase 4 Verification

### Phase 3: Storage Layer Verification

**Focus:** Database contract enforcement

**Key Tests:**
- Ingestion pipeline correctness
- Receipt generation and verification
- Audit chain integrity
- RID encoder accuracy

**Success Criteria:**
- All unit tests pass
- DB-gated tests pass when database is available
- Stress harness validates load handling

**Verification Command:**

```bash
# With database active
ENKI_DB_DSN=postgresql://localhost/enki_test pytest services/api/tests/
```

---

### Phase 4: API Surface Verification

**Focus:** External request handling and contract enforcement

**Key Tests:**
- HTTP API correctness
- Request validation
- Response formatting
- Error handling and status codes

**Success Criteria:**
- Phase 3 tests still pass
- API tests validate HTTP layer
- Integration tests verify end-to-end flows

**Verification Command:**

```bash
# Requires both database AND API server running
ENKI_DB_DSN=postgresql://localhost/enki_test \
ENKI_API_URL=http://localhost:8000 \
pytest services/api/tests/
```

---

## Database Activation (Controlled and Intentional)

ENKI does not assume database availability because:

### 1. Development Workflow

Not every contributor needs a running PostgreSQL instance to:
- Fix RID encoder bugs
- Update definition schemas
- Refactor validation logic
- Write documentation

### 2. CI/CD Flexibility

Lightweight CI pipelines can validate:
- Python syntax
- Import correctness
- Unit test coverage
- Documentation integrity

**Without needing:**
- Docker Compose orchestration
- Database initialization scripts
- Credential management
- Network port allocation

### 3. Security Hygiene

Database credentials should not be:
- Hardcoded in test files
- Committed to version control
- Assumed to exist in CI environments
- Passed as command-line arguments

**ENKI requires explicit opt-in via environment variable.**

### 4. Phase Isolation

Phase 1-2 work focused on:
- Base-60 library implementation
- Definition pack structure
- Validation contract design
- Glyph rendering logic

**None of this requires PostgreSQL.**

Database activation is a Phase 3+ concern.

---

## How to Enable Full Verification

### Local Development

```bash
# Start PostgreSQL (Docker Compose recommended)
docker compose up -d postgres

# Set environment variable
export ENKI_DB_DSN=postgresql://enki:enki@localhost:5432/enki_test

# Run all tests (including DB-gated)
pytest services/api/tests/
```

### CI/CD Pipeline

```yaml
# GitHub Actions example
- name: Start PostgreSQL
  run: docker compose up -d postgres

- name: Run Full Test Suite
  env:
    ENKI_DB_DSN: postgresql://enki:enki@localhost:5432/enki_test
  run: pytest services/api/tests/
```

### Pre-Deployment Verification

```bash
# Full stress harness + DB-gated tests
ENKI_DB_DSN=postgresql://localhost/enki_prod_staging \
pytest services/api/tests/ --durations=10
```

---

## Interpreting Test Results

### ✅ All Tests Pass (No Skips)

**Meaning:**
- Database is available
- Storage contract is validated
- Ingestion pipeline is functional
- Chain integrity is verified

**Action:** Ready for production deployment

---

### ✅ All Tests Pass (Some Skips)

**Meaning:**
- Logic tests passed
- Database tests were skipped (no `ENKI_DB_DSN`)
- Code is correct but storage layer not verified

**Action:** Safe to merge, but require DB validation before deployment

---

### ❌ Any Test Fails

**Meaning:**
- Contract violation detected
- Logic error in implementation
- Database state corruption
- Race condition surfaced

**Action:** Block merge, investigate failure, fix contract violation

---

## Stress Testing Rationale

ENKI's stress harness is **not run in standard CI/CD** because:

### 1. Time Cost

Stress tests may take:
- 30+ seconds per ingestion burst
- Minutes for concurrency tests
- Extended time for boundary condition exploration

**This is incompatible with fast feedback loops.**

### 2. Resource Cost

Stress tests require:
- Active database connections
- Large temporary table allocation
- Disk I/O for transaction logging
- Memory for concurrent process simulation

**Not appropriate for every commit.**

### 3. Signal-to-Noise Ratio

Most commits do not affect:
- Ingestion throughput
- Concurrent write handling
- Transaction isolation behavior

**Stress tests are for storage layer changes only.**

### When to Run Stress Tests

✅ **Before production deployment**  
✅ **After storage contract changes**  
✅ **When investigating performance regressions**  
✅ **During hardware capacity planning**

❌ **Not on every commit**  
❌ **Not in lightweight CI pipelines**  
❌ **Not for documentation changes**

---

## Operational Guarantees

ENKI's verification approach guarantees:

### 1. Fast Feedback

Unit tests execute in milliseconds:
- No external dependencies
- Deterministic behavior
- Immediate failure detection

### 2. Opt-In Complexity

Database tests only run when needed:
- Developer chooses when to validate storage
- CI/CD can vary depth per pipeline
- Stress testing is explicit invocation

### 3. Clear Failure Attribution

Test categorization prevents confusion:
- SKIPPED → Missing precondition
- FAILED → Contract violation
- PASSED → Validation successful

### 4. Production Confidence

Full verification validates:
- Storage layer correctness
- Ingestion pipeline integrity
- Chain verification accuracy
- Load handling capacity

---

## Common Misunderstandings

### ❌ "Tests are skipped, something is broken"

**Reality:** Skips indicate database is not available.  
**Action:** If storage validation is needed, set `ENKI_DB_DSN`.

---

### ❌ "Why don't all tests run automatically?"

**Reality:** Database gating is intentional design.  
**Action:** Review "Database Activation" section above.

---

### ❌ "Stress tests failed in CI"

**Reality:** Stress tests should not run in standard CI.  
**Action:** Remove stress harness from CI pipeline, run manually.

---

### ❌ "How do I know storage layer works?"

**Reality:** Set `ENKI_DB_DSN` and verify all DB-gated tests pass.  
**Action:** See "How to Enable Full Verification" section.

---

## Verification Checklist

### Before Merging Code

- [ ] All unit tests pass (no database required)
- [ ] Python imports resolve correctly
- [ ] No syntax errors or linting violations
- [ ] Documentation updated if contracts changed

---

### Before Deploying to Staging

- [ ] All unit tests pass
- [ ] All DB-gated tests pass (`ENKI_DB_DSN` set)
- [ ] No skipped tests in results
- [ ] Stress harness executed successfully

---

### Before Deploying to Production

- [ ] All verification from staging complete
- [ ] Stress harness run against production-equivalent load
- [ ] Database migration plan validated
- [ ] Rollback procedure tested

---

## References

**Related Specifications:**
- [10-storage-contract-spec.md](10-storage-contract-spec.md) — Storage layer contracts
- 15-ingestion-contract.md — Ingestion validation semantics
- 17-security-architecture.md — Security model and constraints

**Test Locations:**
- Unit tests: `services/api/tests/test_rid_encoder.py`
- DB-gated tests: `services/api/tests/test_phase3_milestone1.py`
- Stress harness: `services/api/tests/test_stress_ingestion.py` (if exists)

**Test Runner:**
- `services/api/run_local_tests.ps1` — Repeatable test execution with PYTHONPATH setup

---

## Document Maintenance

**This document should be updated when:**
- New test categories are introduced
- Database gating logic changes
- Stress testing criteria evolve
- CI/CD pipeline structure changes

**This document should NOT:**
- Redefine architectural contracts
- Specify test implementation details
- Document every individual test case
- Replace inline test documentation

**Treat this as operational guidance, not architectural specification.**

---

**END OF SPECIFICATION**

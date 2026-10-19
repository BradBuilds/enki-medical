# ENKI Workspace Organization & Governance

**Date:** 2025-12-31  
**Status:** 🔒 AUTHORITATIVE  
**Purpose:** Prevent confusion, establish clear rules for folder structure, documentation, and archiving

---

## Current Structure Analysis

```
Enki Node/
├── 📁 core/                    # Python implementation (source of truth for code)
├── 📁 libraries/               # Definition packs (source of truth for data)
├── 📁 schemas/                 # JSON schemas (source of truth for contracts)
├── 📁 services/                # API and services
├── 📁 docs/                    # Canonical documentation (numbered specs)
├── 📁 examples/                # Integration examples and demos
├── 📄 Root-level *.md files    # ⚠️ STATUS: PROLIFERATING (needs governance)
├── 📜 Scripts (*.bat, *.sh)    # Convenience runners
└── 📦 Config (.gitignore)      # Version control
```

---

## The Problem: Documentation Sprawl

**Current state (12 markdown files at root):**
```
BUILD_COMPLETE.md
PACK_LOADER_COMPLETE.md
PACK_LOADER_IMPLEMENTATION.md
PACK_LOADER_QUICK_REF.md
QUICK_REFERENCE.md
README.md
SETUP.md
SPEC_DIVERGENCE_CORRECTION.md
TERMINOLOGY_AUTHORITY.md
```

**Issues:**
- ❌ No clear hierarchy between "active" and "historical" docs
- ❌ Multiple docs per feature (PACK_LOADER_* × 3)
- ❌ Completion reports mixed with user guides
- ❌ Will become unmanageable as features grow

---

## Governance Rules (Authoritative)

### Rule 1: Source of Truth Hierarchy

```
Authority Level 1: SCHEMAS (highest)
  └── schemas/*.schema.json
      ↓ Defines contracts

Authority Level 2: DEFINITIONS
  └── libraries/*/definitions/*.json
      ↓ Implements contracts

Authority Level 3: CODE
  └── core/*, services/*
      ↓ Consumes definitions

Authority Level 4: DOCS
  └── docs/*.md
      ↓ Explains everything
```

**Principle:** Lower levels must defer to higher levels. Code follows definitions, definitions follow schemas.

---

### Rule 2: Documentation Types & Locations

#### Type A: **Living Documentation** (always current)
**Location:** `docs/` (numbered)
**Pattern:** `NN-topic-name.md` (00, 01, 02...)
**Purpose:** Canonical specs and guides
**Examples:**
- `00-start-here.md` - Entry point
- `01-base60-library-spec.md` - Feature spec
- `02-validation-contract.md` - Contract spec
- `03-pack-loader-spec.md` ← Next one to create

**Rules:**
- ✅ Numbered sequentially
- ✅ Always kept up-to-date
- ✅ User-facing or developer-facing specs
- ❌ Never deleted, only updated

#### Type B: **Implementation Reports** (recent history)
**Location:** `docs/implementation-reports/`
**Pattern:** `YYYY-MM-DD-feature-name.md`
**Purpose:** Point-in-time completion reports (recent, last 3 months)
**Examples:**
- `2025-12-31-pack-loader-complete.md`
- `2025-12-31-spec-divergence-correction.md`

**Rules:**
- ✅ Dated filenames
- ✅ Immutable after creation (historical record)
- ✅ Prove what was built and when
- ✅ Stay here for 3 months, then move to archive
- ❌ Not updated (snapshot in time)

#### Type C: **Quick References** (cheat sheets)
**Location:** `docs/quick-ref/`
**Pattern:** `feature-name-quick-ref.md`
**Purpose:** Fast lookups for developers
**Examples:**
- `pack-loader-quick-ref.md`
- `base60-quick-ref.md`

**Rules:**
- ✅ Kept current
- ✅ Minimal, focused content
- ✅ Code examples first, explanations second

#### Type D: **Root-Level Docs** (entry points only)
**Location:** `/` (root)
**Allowed files (exhaustive list):**
- `README.md` - Project overview, first thing visitors see
- `SETUP.md` - Installation and setup
- `CHANGELOG.md` - Version history
- `LICENSE` - License file (if present)

**Rules:**
- ✅ Maximum 4 files (listed above)
- ✅ High-level only
- ✅ Link to `docs/` for details
- ❌ No feature-specific docs at root
- ❌ No completion reports at root
- ❌ No quick references at root

---

### Rule 3: Archive Strategy

#### What to Archive
- ✅ Implementation reports older than 3 months
- ✅ Deprecated specs (when features change)
- ✅ Historical decisions (ADRs - Architecture Decision Records)
- ❌ Current specs (keep in `docs/`)
- ❌ Quick references (keep current)
- ❌ Recent implementation reports (keep in `docs/implementation-reports/`)

#### Archive Location
```
docs/
  archive/              ← IMMUTABLE ONLY (frozen artifacts)
    YYYY-MM/
      implementation-reports/
      deprecated-specs/
      decisions/
```

**Critical rule:** Everything in `docs/archive/` is **immutable**. No edits after archiving.

**Naming convention:**
- Implementation reports: `YYYY-MM-DD-feature-name.md`
- Decisions: `YYYY-MM-DD-ADR-NNN-title.md`
- Deprecated specs: `YYYY-MM-DD-deprecated-spec-name.md`

---

### Rule 4: Folder Purposes (Immutable)

| Folder | Purpose | Authority | Who Writes | Can Modify? |
|--------|---------|-----------|------------|-------------|
| `schemas/` | JSON schemas | 🔒 Highest | Schema authors | Versioned only |
| `libraries/` | Definition packs | 🔒 High | Pack authors | Via pack loader |
| `core/` | Python implementation | Medium | Developers | Yes (code) |
| `services/` | API & services | Medium | Developers | Yes (code) |
| `docs/` | Canonical docs | Medium | Tech writers | Yes (updates) |
| `examples/` | Integration demos | Low | Developers | Yes (demos) |
| `tests/` | Test suites | Medium | Developers | Yes (tests) |

---

### Rule 5: New Feature Documentation Workflow

When implementing a new feature:

#### Step 1: Planning Phase
1. Create spec in `docs/NN-feature-spec.md`
2. Get approval/review
3. Lock down requirements

#### Step 2: Implementation Phase
1. Write code in `core/` or `services/`
2. Create tests in appropriate test folder
3. Update relevant definitions in `libraries/` if needed

#### Step 3: Completion Phase
1. Create implementation report: `docs/implementation-reports/YYYY-MM-DD-feature-complete.md`
2. Update spec in `docs/` if implementation differs
3. Create quick reference: `docs/quick-ref/feature-quick-ref.md`
4. Update root `README.md` with one-line summary
5. Update `docs/README.md` index with new spec number

#### Step 4: Archive Phase (3 months later OR at next major release)
1. Move old implementation reports: `docs/implementation-reports/` → `docs/archive/YYYY-MM/implementation-reports/`
2. Keep specs and quick-refs active (never archive unless deprecated)
3. Mark archived files as immutable (no further edits)

---

## Proposed Reorganization (Immediate Action)

### Target Structure (Clean End State)

```
Root/
├── README.md
├── SETUP.md
├── CHANGELOG.md                              (to be created)
└── LICENSE                                   (if applicable)

docs/
├── README.md                                 (index of all specs)
├── 00-start-here.md
├── 01-base60-library-spec.md
├── 02-validation-contract.md
├── 03-terminology-authority.md               ← Moved from root
│
├── implementation-reports/                   ← Recent history (last 3 months)
│   ├── 2025-12-31-build-complete.md
│   ├── 2025-12-31-pack-loader-complete.md
│   ├── 2025-12-31-pack-loader-impl.md
│   └── 2025-12-31-spec-divergence.md
│
├── quick-ref/                                ← Always current
│   ├── base60-quick-ref.md
│   └── pack-loader-quick-ref.md
│
└── archive/                                  ← Immutable only (3+ months old)
    └── YYYY-MM/
        ├── implementation-reports/
        ├── deprecated-specs/
        └── decisions/
```

### File Moves

```bash
# Move implementation reports to recent history (NOT archive yet)
docs/implementation-reports/
  ├── 2025-12-31-build-complete.md          (was: BUILD_COMPLETE.md)
  ├── 2025-12-31-pack-loader-complete.md    (was: PACK_LOADER_COMPLETE.md)
  ├── 2025-12-31-pack-loader-impl.md        (was: PACK_LOADER_IMPLEMENTATION.md)
  └── 2025-12-31-spec-divergence.md         (was: SPEC_DIVERGENCE_CORRECTION.md)

# Move quick references
docs/quick-ref/
  ├── base60-quick-ref.md                   (was: QUICK_REFERENCE.md)
  └── pack-loader-quick-ref.md              (was: PACK_LOADER_QUICK_REF.md)

# Move authority docs to numbered specs
docs/
  └── 03-terminology-authority.md           (was: TERMINOLOGY_AUTHORITY.md)

# Keep at root (only these 4 allowed)
README.md
SETUP.md
CHANGELOG.md (to be created)
LICENSE (if applicable)
```

---

## Access Patterns (How to Find Things)

### "I want to understand a feature"
→ Go to `docs/NN-feature-spec.md`

### "I need a quick code example"
→ Go to `docs/quick-ref/feature-quick-ref.md`

### "I want to see what was built"
→ Go to `docs/archive/YYYY-MM/implementation-reports/`

### "I need to validate data"
→ Go to `schemas/*.schema.json`

### "I want to use a library"
→ Go to `libraries/*/pack.json` and definitions

### "I need to run something"
→ Use root-level scripts (`*.bat`, `*.sh`)

---

## File Naming Conventions

### Specs (docs/)
- Pattern: `NN-topic-name.md`
- Example: `03-pack-loader-spec.md`
- Rule: Two-digit prefix, lowercase-with-hyphens
- **Never reuse a number** (even if old spec is deleted)
- Maintain index in `docs/README.md` listing all specs

### Implementation Reports (docs/archive/)
- Pattern: `YYYY-MM-DD-feature-complete.md`
- Example: `2025-12-31-pack-loader-complete.md`
- Rule: ISO date prefix, descriptive suffix

### Quick References (docs/quick-ref/)
- Pattern: `feature-name-quick-ref.md`
- Example: `pack-loader-quick-ref.md`
- Rule: Feature name + "-quick-ref"

### Code Files
- Pattern: `snake_case.py` for Python
- Example: `loader.py`, `validate_pack.py`
- Rule: Descriptive, no prefixes

### Definition Files
- Pattern: `pack-id.type.json`
- Example: `base60.system.json`
- Rule: Matches definition `id` field

---

## Anti-Patterns (Don't Do This)

❌ **Multiple docs for one feature at root**
```
FEATURE_COMPLETE.md
FEATURE_IMPLEMENTATION.md
FEATURE_QUICK_REF.md
```
→ Use folder structure instead

❌ **Mixing historical and current docs**
```
docs/
  old-spec-v1.md
  old-spec-v2.md
  current-spec.md
```
→ Archive old versions with dates

❌ **Vague file names**
```
notes.md
todo.md
temp.md
```
→ Use descriptive, dated names

❌ **Duplicating information**
→ Link to single source of truth

---

## Maintenance Schedule

### Weekly
- Review root folder for new *.md files
- Move completion reports to archive
- Update quick references if code changed

### Monthly
- Archive old implementation reports (>3 months)
- Review docs/ for outdated specs
- Update README.md with recent changes

### Per Feature
- Create numbered spec in `docs/` before coding
- Create implementation report in `docs/implementation-reports/` after completion
- Create quick-ref in `docs/quick-ref/` for user reference
- Update `docs/README.md` index
- Archive implementation report after 3 months (move to `docs/archive/YYYY-MM/`)

---

## Decision Authority

**Who decides folder structure?**
→ This document (governance)

**Who decides file placement?**
→ Feature implementer following these rules

**Who approves exceptions?**
→ Project maintainer with documentation of why

**How to propose changes?**
→ Create ADR in `docs/archive/YYYY-MM/decisions/`

---

## Summary: The Rules

1. **Authority flows from schemas → definitions → code → docs**
2. **Living docs in `docs/NN-*.md`** (always current)
3. **Historical docs in `docs/archive/YYYY-MM/`** (immutable)
4. **Quick refs in `docs/quick-ref/`** (cheat sheets)
5. **Root has max 3-4 entry point docs** (README, SETUP, CHANGELOG)
6. **No orphan docs** - everything has a home
7. **Date historical files** (YYYY-MM-DD prefix)
8. **Number canonical specs** (00, 01, 02...)
9. **Archive after 3 months** (implementation reports)
10. **Link, don't duplicate** (single source of truth)

---

## Implementation Checklist

To apply this structure NOW:

```bash
# 1. Create directory structure
mkdir -p docs/implementation-reports
mkdir -p docs/quick-ref
mkdir -p docs/archive/2025-12/implementation-reports
mkdir -p docs/archive/2025-12/deprecated-specs
mkdir -p docs/archive/2025-12/decisions

# 2. Move implementation reports (to recent history, NOT archive)
mv BUILD_COMPLETE.md docs/implementation-reports/2025-12-31-build-complete.md
mv PACK_LOADER_COMPLETE.md docs/implementation-reports/2025-12-31-pack-loader-complete.md
mv PACK_LOADER_IMPLEMENTATION.md docs/implementation-reports/2025-12-31-pack-loader-impl.md
mv SPEC_DIVERGENCE_CORRECTION.md docs/implementation-reports/2025-12-31-spec-divergence.md

# 3. Move quick references
mv QUICK_REFERENCE.md docs/quick-ref/base60-quick-ref.md
mv PACK_LOADER_QUICK_REF.md docs/quick-ref/pack-loader-quick-ref.md

# 4. Move authority docs to numbered spec
mv TERMINOLOGY_AUTHORITY.md docs/03-terminology-authority.md

# 5. Create docs index
echo "# ENKI Documentation Index" > docs/README.md
echo "" >> docs/README.md
echo "## Specifications (Always Current)" >> docs/README.md
echo "- 00 - Start Here" >> docs/README.md
echo "- [01 - Base-60 Library Spec](01-base60-library-spec.md)" >> docs/README.md
echo "- [02 - Validation Contract](02-validation-contract.md)" >> docs/README.md
echo "- [03 - Terminology Authority](03-terminology-authority.md)" >> docs/README.md

# 6. Verify clean root
ls *.md  # Should only show: README.md, SETUP.md
```

---

**Status:** Ready to implement  
**Impact:** Prevents future confusion  
**Authority:** Governance document  
**Next Step:** Execute reorganization checklist

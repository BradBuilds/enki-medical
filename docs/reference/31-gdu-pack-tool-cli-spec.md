# GDU Pack Tool — CLI Specification

**Date:** 2026-01-12  
**Status:** Implementation Specification  
**Purpose:** Define exact command-line interface for Pack Tool (Phase B)  
**Authority:** Derived from GDU Patch v2 verification

---

## Overview

The Pack Tool (`gdu pack`) is the **first component to build** in the GDU implementation. It:
- Imports raw definition files
- Validates "no volatile fields" rule
- Enforces pack constraints
- Computes PACK_DIGEST deterministically
- Installs packs to registry

**Build Order:** Pack Tool → PackLoader → Activation → Dev Workflow

---

## Command Suite

### 1. `gdu pack init`

**Purpose:** Initialize a new pack manifest (pack.json)

**Usage:**
```bash
gdu pack init --pack-id <id> --version <semver> [--namespace <ns>] [--author <name>] [--output <dir>] [--force] [--text]
```

**Arguments:**
| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--pack-id` | string | YES | Semantic pack identifier (e.g., "base60") |
| `--version` | semver | YES | Semantic version (e.g., "0.2.0") |
| `--namespace` | string | NO | Root namespace (default: pack-id) |
| `--author` | string | NO | Pack author/maintainer |
| `--output` | path | NO | Output directory (default: `./<pack-id>`) |
| `--force` | flag | NO | Allow initialization in an existing directory only if it is empty OR contains only pack.json and definitions/ (and definitions/ is not a symlink). Otherwise fail. |
| `--text` | flag | NO | Output human-readable text instead of JSON |

**Output File:** `<output>/pack.json`

**Output JSON Schema:**
```json
{
  "pack_id": "base60",
  "version": "0.2.0",
  "namespace": "base60",
  "author": "ENKI Core Team",
  "definitions": [],
  "dependencies": [],
  "metadata": {
    "description": "Base-60 positional numeral system with hieroglyphic representation",
    "tags": ["numeral", "base60", "cuneiform"],
    "license": "MIT"
  }
}
```

**Critical Governance Rule:**
`pack.json` is part of the pack; therefore it **MUST NOT** contain volatile fields either. Creation metadata must live in activation records or dev-only tool output, never in pack.json itself.

**Behavior:**
1. Resolve `<output>` directory (default `./<pack-id>`)
2. If `<output>` exists:
   - If `--force` is NOT set → fail with exit code 2
   - If `--force` is set → allow only if `<output>` is empty OR contains only:
     - `pack.json` (file)
     - `definitions/` (directory) and `definitions/` is not a symlink
   - Otherwise fail with exit code 2
3. Create (or ensure) `<output>/definitions/` directory exists and is not a symlink
4. Write `<output>/pack.json` with the schema above (no volatile fields)

**Exit Codes:**
- `0`: Success
- `1`: Invalid arguments
- `2`: Output directory exists and is not eligible for `--force`

**Example (--text):**
```bash
$ gdu pack init --pack-id base60 --version 0.2.0 --author "ENKI Core" --text
✓ Created pack.json in ./base60/
  Pack ID: base60
  Version: 0.2.0
  Namespace: base60
```

---

### 2. `gdu pack add`

**Purpose:** Add definition files to pack

**Usage:**
```bash
gdu pack add <file-pattern> [--pack-dir <dir>] [--base <dir>] [--strict-volatile] [--dry-run] [--text]
```

**Arguments:**
| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `<file-pattern>` | glob | YES | Files to add (e.g., `definitions/*.json`) |
| `--pack-dir` | path | NO | Pack directory (default: `.`) |
| `--base` | path | NO | Base directory for relative path mapping (see Behavior) |
| `--strict-volatile` | flag | NO | Enable heuristic volatile-field regex rejection (advisory strict mode) |
| `--dry-run` | flag | NO | Show what would be added without modifying |
| `--text` | flag | NO | Output human-readable text instead of JSON |

**Behavior (Deterministic Copy Rules):**
1. Resolve glob pattern to file list (deterministic ordering: sort source paths by UTF-8 byte lexicographic order after NFC normalization)
2. For each file:
   - Reject symlinks (fail-closed)
   - Read file as UTF-8 bytes and parse JSON
   - JSON must parse successfully AND root must be a JSON object (not array/string/number/null)
   - Check for volatile fields (fail if found)
   - If `--strict-volatile` is enabled, apply heuristic key regex rejection (advisory strict mode)
   - **Determine destination path (MUST be under definitions/ and MUST NOT escape):**
     - If source is already under `<pack-root>/definitions/`, register in-place (no copy)
     - If source is external:
       - With `--base <dir>`: compute `rel_path = relative(source, base)` and set destination to `definitions/{rel_path}`
       - Without `--base`: flatten to `definitions/{basename}` (fail on collision)
   - Normalize destination path to NFC, require forward slashes in stored manifest paths
   - **Fail if destination is absolute, contains `..`, contains a Windows drive prefix, or would escape `definitions/`**
   - If not in-place: copy source → destination, creating subdirectories under `definitions/` as needed
   - Update `pack.json.definitions` array with the destination path (stored as `definitions/...` with forward slashes)
3. After processing all files, normalize all `pack.json.definitions` entries to NFC and sort by UTF-8 byte lexicographic order
4. Write updated `pack.json` (pack tool MUST NOT write any other files into pack root)

**Example (preserve structure):**
```bash
gdu pack add /src/defs/**/*.json --pack-dir ./base60 --base /src/defs
# /src/defs/system/base60.json → ./base60/definitions/system/base60.json
# /src/defs/rules.json → ./base60/definitions/rules.json
```

**Example (flatten):**
```bash
gdu pack add /src/**/*.json --pack-dir ./base60
# /src/any/path/file.json → ./base60/definitions/file.json (flat)
```

**Volatile Field Check (Blacklist — Minimum Required Set):**
Reject files containing any of:
- `created`, `created_at`, `created_timestamp`
- `modified`, `modified_at`, `modified_timestamp`
- `activated_at`, `activation_timestamp`, `timestamp`
- `usage_count`, `usage_metric`, `access_counter`, `hit_count`
- `last_accessed`, `last_modified`, `last_used`

**Structural Check (Optional with `--strict-volatile`):**
When `--strict-volatile` flag is enabled, also reject any key matching regex:
```
.*(time|timestamp|modified|created|access|usage|count|counter|metric).*
```
Unless key is in semantic allowlist:
- Permitted: `digit_count`, `place_value_positions`, `carry_threshold` (semantic constants, not runtime metrics)

**Governance Note:** The exact blacklist is normative; governance may expand this list. Structural check is advisory for stricter enforcement.

**Output (stdout):**
```json
{
  "status": "success",
  "added": [
    {
      "source": "/path/to/base60.system.json",
      "destination": "definitions/base60.system.json",
      "size_bytes": 342
    },
    {
      "source": "/path/to/base60.digits.json",
      "destination": "definitions/base60.digits.json",
      "size_bytes": 8192
    }
  ],
  "skipped": [],
  "failed": []
}
```

**Error Output (volatile field found):**
```json
{
  "status": "failed",
  "error": "volatile_field_detected",
  "file": "definitions/bad_definition.json",
  "violations": [
    {
      "field": "created_at",
      "value": "2026-01-12T00:00:00Z",
      "reason": "Timestamp fields are prohibited in definitions"
    }
  ]
}
```

**Exit Codes:**
- `0`: All files added successfully
- `1`: Invalid arguments
- `3`: Volatile field detected (fail-closed)
- `4`: Invalid JSON structure

**Example:**
```bash
$ gdu pack add definitions/*.json --pack-dir ./base60/
✓ Added 4 files to pack
  definitions/base60.system.json (342 bytes)
  definitions/base60.digits.json (8192 bytes)
  definitions/base60.glyphs.json (1024 bytes)
  definitions/base60.rules.json (512 bytes)

$ gdu pack add definitions/invalid.json
✗ Failed: Volatile field detected
  File: definitions/invalid.json
  Field: "created_at"
  Value: "2026-01-12T00:00:00Z"
  Reason: Timestamp fields are prohibited in definitions
```

---

### 3. `gdu pack validate`

**Purpose:** Validate pack structure and constraints

**Usage:**
```bash
gdu pack validate [--pack-dir <dir>] [--strict] [--strict-volatile] [--text]
```

**Arguments:**
| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--pack-dir` | path | NO | Pack directory (default: `.`) |
| `--strict` | flag | NO | Enable strict validation (fail on warnings) |
| `--strict-volatile` | flag | NO | Enable heuristic volatile-field regex rejection (advisory strict mode) |
| `--text` | flag | NO | Output human-readable text instead of JSON |

**Validation Checks:**
1. **Pack Structure:**
   - `pack.json` exists at pack root
   - `definitions/` directory exists at pack root
   - **No other files or directories at pack root** (including hidden dotfiles; fail on .DS_Store, notes.txt, tmp/, .gitkeep, etc.)
   - Under `definitions/`: only `.json` files and subdirectories allowed (recursive)
   - No symlinks anywhere in pack

2. **pack.json Schema:**
   - Required fields: pack_id, version, namespace, definitions
   - Semantic version format
   - Valid namespace identifier
   - **`pack.json` MUST NOT contain volatile fields** (same blacklist as definitions; and apply `--strict-volatile` heuristic if enabled)
   - **Consistency check:** `pack.json.definitions` array **MUST** equal the scanned set of `definitions/**/*.json` (recursive, `.json` only), after normalization and sorting
   - **Sort order:** `pack.json.definitions` **MUST** be sorted in UTF-8 lexicographic byte order (same as PACK_DIGEST manifest)
   - Mismatch between declared definitions and filesystem → fail

3. **Definition Files:**
   - All listed in pack.json exist
   - Valid JSON structure
   - No volatile fields
   - No symlinks
   - UTF-8 encoding
   - **NFC normalized paths:** For each `definitions/*` file path, ensure `path == NFC(path)`. **MUST fail** if non-NFC detected (fail-closed; ensures consistent digest computation across implementations)

4. **Path Constraints:**
   - All definitions under `definitions/` subdirectory
   - Forward slash separators
   - No `..` or absolute paths
   - No duplicate filenames

**Output (success):**
```json
{
  "status": "valid",
  "pack_id": "base60",
  "version": "0.2.0",
  "definition_count": 4,
  "total_size_bytes": 10070,
  "checks_passed": 12,
  "warnings": []
}
```

**Output (failure):**
```json
{
  "status": "invalid",
  "pack_id": "base60",
  "version": "0.2.0",
  "errors": [
    {
      "check": "symlink_prohibited",
      "file": "definitions/symlink.json",
      "message": "Symlinks are not allowed in packs (fail-closed)"
    },
    {
      "check": "prohibited_directory",
      "path": "receipts/",
      "message": "Pack may only contain pack.json and definitions/"
    }
  ]
}
```

**Exit Codes:**
- `0`: Pack is valid
- `1`: Invalid arguments
- `5`: Validation failed

**Example:**
```bash
$ gdu pack validate --pack-dir ./base60/
✓ Pack is valid
  Pack: base60 v0.2.0
  Definitions: 4 files (10,070 bytes)
  Checks passed: 12/12

$ gdu pack validate --pack-dir ./broken-pack/
✗ Validation failed
  ✗ Symlink detected: definitions/link.json (prohibited)
  ✗ Prohibited directory: receipts/ (only pack.json + definitions/ allowed)
```

---

### 4. `gdu pack digest`

**Purpose:** Compute PACK_DIGEST for pack

**Usage:**
```bash
gdu pack digest [--pack-dir <dir>] [--show-manifest] [--digest-format hex|short] [--text]
```

**Arguments:**
| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--pack-dir` | path | NO | Pack directory (default: `.`) |
| `--show-manifest` | flag | NO | Include manifest in output |
| `--digest-format` | enum | NO | Digest string format in output JSON: `hex` (default) or `short` |
| `--text` | flag | NO | Output human-readable text instead of JSON |

**PACK_DIGEST Scope:**
`pack.json` is **intentionally excluded** from PACK_DIGEST computation. Changing pack metadata (author, description, tags) MUST NOT change PACK_DIGEST. The runtime binds to packs by `content_hash` (PACK_DIGEST) and semantic identifiers (pack_id, version, namespace) are separately validated by pack validation rules, not by PACK_DIGEST.

**PACK_DIGEST Representation:**
- **PACK_DIGEST_HEX:** 64 hexadecimal characters (lowercase), no prefix
  - Example: `e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374`
  - Used in: Registry directory names (Windows-safe, no colons)
- **PACK_DIGEST (display/JSON):** `sha256:` prefix + PACK_DIGEST_HEX
  - Example: `"sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374"`
  - Used in: JSON output, active.json `content_hash` field, human display
- **Registry directory naming:** `{registry}/packs/{PACK_DIGEST_HEX}/`

**Manifest Derivation:**
PACK_DIGEST manifest is **derived from filesystem scan** of `definitions/**/*.json`, not from `pack.json.definitions` list. Validation enforces that pack.json list matches scan results.

**Computation Steps:**
1. Scan `definitions/` directory recursively
2. For each `.json` file:
   - Compute SHA-256 of file content
   - Normalize path to NFC
   - Store as `{path, sha256}` entry
3. Build manifest object: `{"version":"1","files":[...]}`
4. Sort files array by `path` (lexicographic UTF-8 byte comparison)
5. Canonicalize JSON via RFC 8785 (JCS)
6. Compute PACK_DIGEST = SHA256(canonical_manifest)

**Note:** `pack.json` is copied into the digest-named installation directory as non-hash-addressed metadata.

**Output (hex format):**
```json
{
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "manifest_version": "1",
  "file_count": 4,
  "computation_time_ms": 12
}
```

**Output (with manifest):**
```json
{
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "manifest_version": "1",
  "file_count": 4,
  "manifest": {
    "version": "1",
    "files": [
      {
        "path": "definitions/base60.digits.json",
        "sha256": "abc123def456..."
      },
      {
        "path": "definitions/base60.glyphs.json",
        "sha256": "ghi789jkl012..."
      },
      {
        "path": "definitions/base60.rules.json",
        "sha256": "mno345pqr678..."
      },
      {
        "path": "definitions/base60.system.json",
        "sha256": "stu901vwx234..."
      }
    ]
  },
  "canonical_manifest": "{\"files\":[{\"path\":\"definitions/base60.digits.json\",\"sha256\":\"abc123...\"},{\"path\":\"definitions/base60.glyphs.json\",\"sha256\":\"ghi789...\"},{\"path\":\"definitions/base60.rules.json\",\"sha256\":\"mno345...\"},{\"path\":\"definitions/base60.system.json\",\"sha256\":\"stu901...\"}],\"version\":\"1\"}"
}
```

**Exit Codes:**
- `0`: Digest computed successfully
- `1`: Invalid arguments
- `6`: Computation failed (e.g., file read error)

**Output Format Rules:**
All commands output **JSON to stdout** by default.
- `--digest-format hex` (default): `"sha256:<64-char-hex>"`
- `--digest-format short`: `"sha256:<12-char-hex>"`

For human-readable text output, use `--text` flag (outputs plain text instead of JSON).

**Example (JSON output):**
```bash
$ gdu pack digest --pack-dir ./base60/
{
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "manifest_version": "1",
  "file_count": 4,
  "computation_time_ms": 12
}

$ gdu pack digest --pack-dir ./base60/ --digest-format short
{
  "pack_digest": "sha256:e742a368cf1f",
  "manifest_version": "1",
  "file_count": 4,
  "computation_time_ms": 12
}

$ gdu pack digest --pack-dir ./base60/ --text
PACK_DIGEST: sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374
Manifest version: 1
Files: 4
```

---

### 5. `gdu pack install`

**Purpose:** Install validated pack to GDU registry

**Usage:**
```bash
gdu pack install [--pack-dir <dir>] --registry <registry-path> [--verify] [--dry-run] [--text]
```

**Arguments:**
| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--pack-dir` | path | NO | Pack directory (default: `.`) |
| `--registry` | path | YES | GDU registry root (e.g., `./gdu/registry`) |
| `--verify` | flag | NO | Verify digest after installation |
| `--dry-run` | flag | NO | Show installation plan without executing |
| `--text` | flag | NO | Output human-readable text instead of JSON |

**Installation Steps:**
1. Validate pack (same as `gdu pack validate`)
2. Compute PACK_DIGEST (get PACK_DIGEST_HEX by stripping `sha256:` prefix)
3. Check if pack already exists at `{registry}/packs/{PACK_DIGEST_HEX}/`
4. If not exists:
   - Create `{registry}/packs/{PACK_DIGEST_HEX}.tmp/` (temp directory uses hex only, no prefix)
   - Copy `pack.json`
   - Copy `definitions/` directory (recursive)
   - Atomic rename: `{PACK_DIGEST_HEX}.tmp/` → `{PACK_DIGEST_HEX}/`
5. If `--verify`, recompute digest and verify match

**Output (success):**
```json
{
  "status": "installed",
  "pack_id": "base60",
  "version": "0.2.0",
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "install_path": "/path/to/gdu/registry/packs/e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "install_path_note": "Path uses PACK_DIGEST_HEX (no sha256: prefix)",
  "verified": true
}
```

**Output (already exists):**
```json
{
  "status": "already_installed",
  "pack_id": "base60",
  "version": "0.2.0",
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "install_path": "/path/to/gdu/registry/packs/e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374"
}
```

**Exit Codes:**
- `0`: Installed successfully or already exists
- `1`: Invalid arguments
- `7`: Installation failed (filesystem error)
- `8`: Verification failed (digest mismatch)

**Example:**
```bash
$ gdu pack install --pack-dir ./base60/ --registry ./gdu/registry --verify
✓ Pack installed successfully
  Pack: base60 v0.2.0
  Digest: sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374
  Location: gdu/registry/packs/e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374/
  Verified: ✓

$ gdu pack install --pack-dir ./base60/ --registry ./gdu/registry
✓ Pack already installed (digest match)
```

---

## Minimal Pack Template

### Directory Structure

```
base60/                                 # Pack root
├── pack.json                          # Pack manifest (NO volatile fields)
└── definitions/                       # Definition files only
    ├── base60.system.json             # System constants
    ├── base60.digits.json             # Digit definitions (0-59)
    ├── base60.glyphs.json             # Glyph styles
    └── base60.rules.json              # Computation rules
```

**Prohibited:**
- `receipts/` ❌
- `audit_logs/` ❌
- `signatures/` ❌
- `test/` ❌
- Symlinks ❌
- Any files created by pack tool (`.cache`, `.manifest`, `.tmp`) ❌

**Pack Tool Constraint:**
The pack tool **MUST NOT** write any files into the pack root directory except `pack.json` and `definitions/**`. Temporary files must be created outside the pack root or cleaned up atomically before command completion.

---

### pack.json (Minimal Example)

```json
{
  "pack_id": "base60",
  "version": "0.2.0",
  "namespace": "base60",
  "author": "ENKI Core Team",
  "definitions": [
    "definitions/base60.system.json",
    "definitions/base60.digits.json",
    "definitions/base60.glyphs.json",
    "definitions/base60.rules.json"
  ],
  "dependencies": [],
  "metadata": {
    "description": "Base-60 positional numeral system with hieroglyphic representation",
    "tags": ["numeral", "base60", "cuneiform"],
    "license": "MIT"
  }
}
```

**Field Rules (Volatile Field Constraint):**
- ✅ **Permitted:** pack_id, version, namespace, author, license, description, tags, dependencies, metadata
- ❌ **Prohibited (Volatile):** created, created_at, modified_at, activated_at, usage_count, timestamp, last_modified
- **Rationale:** `pack.json` is part of the pack and subject to the same "no volatile fields" rule as definitions

---

### definitions/base60.system.json (Minimal Example)

```json
{
  "definition_type": "numeral_system",
  "id": "base60.system",
  "namespace": "base60",
  "name": "Base-60 Numeral System",
  "description": "Sexagesimal positional numeral system",
  "base": 60,
  "digit_count": 60,
  "place_value_positions": ["ones", "sixties", "thirty-six-hundreds"],
  "zero_representation": "∅",
  "computation_rules": "base60.rules",
  "digit_set": "base60.digits",
  "glyph_styles": ["wedge_ascii", "wedge_unicode_modern"]
}
```

**Field Rules:**
- ✅ **Permitted:** Semantic constants (name, description, base, rules, constraints)
- ❌ **Prohibited:** created, modified_at, usage_count, last_accessed, timestamp

---

### definitions/base60.digits.json (Minimal Example)

```json
{
  "definition_type": "digit_collection",
  "id": "base60.digits",
  "namespace": "base60",
  "name": "Base-60 Digit Set",
  "description": "Complete set of 60 digits (0-59) with hieroglyphic representations",
  "digits": [
    {
      "value": 0,
      "name": "zero",
      "hieroglyph": "∅",
      "tens": 0,
      "units": 0
    },
    {
      "value": 1,
      "name": "one",
      "hieroglyph": "|",
      "tens": 0,
      "units": 1
    },
    {
      "value": 10,
      "name": "ten",
      "hieroglyph": "<",
      "tens": 1,
      "units": 0
    },
    {
      "value": 23,
      "name": "twenty-three",
      "hieroglyph": "<<|||",
      "tens": 2,
      "units": 3
    }
  ]
}
```

**Notes:**
- Each digit has **immutable properties** only (value, name, hieroglyph)
- No `created_at`, `usage_count`, or other volatile fields
- Structure is deterministic (same digits → same JSON → same hash)

---

### definitions/base60.glyphs.json (Minimal Example)

```json
{
  "definition_type": "glyph_style_collection",
  "id": "base60.glyphs",
  "namespace": "base60",
  "name": "Base-60 Glyph Styles",
  "description": "Visual representations for base-60 digits",
  "styles": [
    {
      "style_id": "wedge_ascii",
      "name": "Wedge ASCII",
      "description": "ASCII approximation of cuneiform wedges",
      "unit_glyph": "|",
      "ten_glyph": "<",
      "encoding": "ASCII"
    },
    {
      "style_id": "wedge_unicode_modern",
      "name": "Wedge Unicode (Modern)",
      "description": "Unicode cuneiform characters",
      "unit_glyph": "𒁹",
      "ten_glyph": "𒌋",
      "encoding": "UTF-8"
    }
  ]
}
```

---

### definitions/base60.rules.json (Minimal Example)

```json
{
  "definition_type": "computation_rules",
  "id": "base60.rules",
  "namespace": "base60",
  "name": "Base-60 Computation Rules",
  "description": "Rules for arithmetic operations in base-60",
  "rules": [
    {
      "rule_id": "addition",
      "operation": "add",
      "description": "Add two base-60 numbers with carry",
      "carry_threshold": 60,
      "example": "23 + 37 = 60 → 1 (sixty) + 0 (units)"
    },
    {
      "rule_id": "place_value",
      "operation": "positional_value",
      "description": "Compute absolute value from positional notation",
      "formula": "value = digit[0] * 60^0 + digit[1] * 60^1 + digit[2] * 60^2 + ...",
      "example": "[23, 1] = 23 + (1 * 60) = 83 (decimal)"
    }
  ]
}
```

---

## Timestamp Format Rules (Windows-Safe)

**Directory Naming Convention:**
When creating activation records or any timestamped directories:
- `{TIMESTAMP}` in directory names **MUST** use basic ISO 8601 UTC without separators: `YYYYMMDDTHHMMSSZ`
  - Example: `20260112T143045Z`
  - Rationale: Colons in Windows filenames cause issues with some tools
- The `timestamp` field inside JSON **MUST** use extended ISO 8601: `YYYY-MM-DDTHH:MM:SSZ`
  - Example: `"2026-01-12T14:30:45Z"`

**Consistency Rule:**
Both representations refer to the same instant; the directory name is filesystem-safe, the JSON field is standard ISO 8601.

---

## Error Handling

All commands follow consistent error patterns:

### Exit Code Standards
| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Continue |
| 1 | Invalid arguments | Check command usage |
| 2 | File/directory conflict | Resolve manually |
| 3 | Volatile field detected | Remove volatile fields (fail-closed) |
| 4 | Invalid JSON | Fix JSON syntax |
| 5 | Validation failed | Fix pack structure |
| 6 | Digest computation failed | Check file permissions |
| 7 | Installation failed | Check registry permissions |
| 8 | Verification failed | Recompute digest |

### JSON Error Output Format

All commands output errors as structured JSON to stderr:

```json
{
  "status": "error",
  "error_code": 3,
  "error_type": "volatile_field_detected",
  "message": "Definition contains prohibited volatile field",
  "details": {
    "file": "definitions/bad.json",
    "field": "created_at",
    "value": "2026-01-12T00:00:00Z",
    "rule": "Timestamps are prohibited in definitions (Doc 25 Patch 4)"
  },
  "help": "Remove all timestamp, counter, and mutable metadata fields from definitions. See: docs/25-gdu-core-master-plan.md#volatile-fields"
}
```

---

## Implementation Notes

### Dependencies
- **JSON handling:** Use RFC 8785 (JCS) library for canonical JSON
- **Unicode:** Normalize paths to NFC before hashing
- **Hashing:** SHA-256 (standard library)
- **Filesystem:** Atomic operations (temp → rename pattern)

### Performance Targets
- `gdu pack digest`: < 100ms for packs with < 1000 definitions
- `gdu pack validate`: < 50ms for typical packs
- `gdu pack install`: < 200ms (includes atomic copy + verify)

### Logging
All commands support `--log-level` flag:
- `debug`: All operations + timings
- `info`: Major steps only (default)
- `warn`: Warnings + errors
- `error`: Errors only

### Output Format
All commands support `--text` flag for human-readable output. Default is JSON to stdout (machine-readable, parseable).

---

## Example Workflow: Building First Pack

**Note:** All commands output JSON by default. Examples below use `--text` flag for human-readable output.

```bash
# 1. Initialize pack
$ gdu pack init --pack-id base60 --version 0.2.0 --author "ENKI Core" --text
✓ Created pack.json in ./base60/
  Pack ID: base60
  Version: 0.2.0
  Namespace: base60

# 2. Add definition files
$ gdu pack add definitions/*.json --pack-dir ./base60/ --text
✓ Added 4 files to pack
  definitions/base60.system.json (342 bytes)
  definitions/base60.digits.json (8192 bytes)
  definitions/base60.glyphs.json (1024 bytes)
  definitions/base60.rules.json (512 bytes)

# 3. Validate pack structure
$ gdu pack validate --pack-dir ./base60/ --text
✓ Pack is valid
  Pack: base60 v0.2.0
  Definitions: 4 files (10,070 bytes)
  Checks passed: 12/12

# 4. Compute digest
$ gdu pack digest --pack-dir ./base60/ --text
PACK_DIGEST: sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374
Manifest version: 1
Files: 4

# Alternative: JSON output (default)
$ gdu pack digest --pack-dir ./base60/
{
  "pack_digest": "sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374",
  "manifest_version": "1",
  "file_count": 4,
  "computation_time_ms": 12
}

# 5. Install to registry
$ gdu pack install --pack-dir ./base60/ --registry ./gdu/registry --verify --text
✓ Pack installed successfully
  Pack: base60 v0.2.0
  Digest: sha256:e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374
  Location: gdu/registry/packs/e742a368cf1fab5eac675fc674f1097ab58609acc715c47c3b05d0f3ea841374/
  Verified: ✓
```

---

**Next Steps:**
- Build Phase C: PackLoader (loads packs from registry)
- Build Phase D: Activation (writes active.json, signatures, audit records)
- Build Phase E: Dev workflow commands (status, diff, verify)

---

**Status:** Ready for Implementation  
**Implementation Order:** CLI commands → Pack validation → PACK_DIGEST computation → Registry installation

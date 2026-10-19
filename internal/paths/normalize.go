package paths

import (
    "path/filepath"
    "runtime"
    "strings"

    "golang.org/x/text/unicode/norm"
)

type NormalizedPath struct {
    Raw   string
    Clean string // NFC, forward slashes, relative (no abs/..)
}

func ToNFC(s string) string { return norm.NFC.String(s) }

// Reject Windows drive prefixes like C:\\ or \\?\ (fail-closed)
func HasWindowsDrivePrefix(p string) bool {
    if len(p) >= 2 && ((p[1] == ':' && ((p[0] >= 'A' && p[0] <= 'Z') || (p[0] >= 'a' && p[0] <= 'z')))) {
        return true
    }
    if strings.HasPrefix(p, `\\?\`) || strings.HasPrefix(p, `\\.\`) {
        return true
    }
    return false
}

func IsAbsAnyOS(p string) bool {
    if filepath.IsAbs(p) {
        return true
    }
    // Also check for Unix-style absolute paths (leading /)
    if strings.HasPrefix(p, "/") {
        return true
    }
    return HasWindowsDrivePrefix(p)
}

func CleanRel(p string) string {
    // Only convert slashes and trim; don't use filepath.Clean
    // because it collapses ".." which we want to detect separately.
    p = filepath.ToSlash(p)
    p = strings.TrimSpace(p)
    p = strings.TrimPrefix(p, "./")
    // Don't call filepath.Clean here—it collapses ..
    // Instead just normalize slashes
    p = filepath.ToSlash(p)
    return p
}

func ContainsDotDot(p string) bool {
    parts := strings.Split(filepath.ToSlash(p), "/")
    for _, part := range parts {
        if part == ".." {
            return true
        }
    }
    return false
}

// NormalizePath enforces: relative, no abs, no drive prefixes, no '..', NFC, forward slashes.
// CRITICAL: Raw input MUST be NFC (fail-closed). NFC mismatch = trust boundary violation.
func NormalizePath(base string, p string) (NormalizedPath, error) {
    raw := p

    // FAIL-CLOSED: Verify raw input is already NFC-normalized.
    // Non-NFC inputs are rejected immediately (trust boundary).
    nfcRaw := ToNFC(p)
    if nfcRaw != p {
        return NormalizedPath{Raw: raw}, ErrNFCMismatch
    }

    // Now safe to work with normalized input.
    if IsAbsAnyOS(p) {
        return NormalizedPath{Raw: raw}, ErrAbsPath
    }
    if runtime.GOOS != "windows" && HasWindowsDrivePrefix(p) {
        return NormalizedPath{Raw: raw}, ErrDrivePrefix
    }

    p = CleanRel(p)
    if p == "." {
        p = ""
    }
    if ContainsDotDot(p) {
        return NormalizedPath{Raw: raw}, ErrDotDot
    }

    // Final check: clean path must still be NFC.
    p2 := ToNFC(p)
    if p2 != p {
        // Should not happen if input was NFC, but double-check.
        return NormalizedPath{Raw: raw}, ErrNFCMismatch
    }

    return NormalizedPath{Raw: raw, Clean: p}, nil
}

var (
    ErrAbsPath       = simpleErr("absolute_paths_prohibited")
    ErrDotDot        = simpleErr("dotdot_prohibited")
    ErrDrivePrefix   = simpleErr("windows_drive_prefix_prohibited")
    ErrNFCMismatch   = simpleErr("path_not_nfc_normalized")
)

type simpleErr string

func (e simpleErr) Error() string { return string(e) }

// ManifestPath ensures forward slashes and prefix "definitions/" (no escape)
func ManifestPath(rel string) string {
    rel = filepath.ToSlash(rel)
    rel = strings.TrimPrefix(rel, "/")
    return "definitions/" + rel
}

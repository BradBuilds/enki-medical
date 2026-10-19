package pack

import (
    "encoding/json"
    stderrs "errors"
    "flag"
    "fmt"
    "io"
    "os"
    "path/filepath"
    "regexp"
    "sort"
    "strings"

    "gdu/internal/errors"
    fsutil "gdu/internal/fs"
    "gdu/internal/paths"
    "gdu/internal/volatile"
)

type validationError struct {
    Check   string `json:"check"`
    Path    string `json:"path,omitempty"`
    File    string `json:"file,omitempty"`
    Message string `json:"message"`
}

type validateSuccess struct {
    Status           string   `json:"status"`
    PackID           string   `json:"pack_id"`
    Version          string   `json:"version"`
    DefinitionCount  int      `json:"definition_count"`
    TotalSizeBytes   int64    `json:"total_size_bytes"`
    ChecksPassed     int      `json:"checks_passed"`
    Warnings         []string `json:"warnings"`
}

type validateFailure struct {
    Status  string             `json:"status"`
    PackID  string             `json:"pack_id,omitempty"`
    Version string             `json:"version,omitempty"`
    Errors  []validationError  `json:"errors"`
}

// Semver pattern: major.minor.patch with no leading zeros (except single 0)
var semverRe = regexp.MustCompile(`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`)

func CmdValidate(argv []string) int {
    fs := flag.NewFlagSet("validate", flag.ContinueOnError)
    packDir := fs.String("pack-dir", ".", "")
    strict := fs.Bool("strict", false, "")
    strictVol := fs.Bool("strict-volatile", false, "")
    text := fs.Bool("text", false, "")

    if err := fs.Parse(argv); err != nil {
        errors.ExitJSON(errors.CliError{
            Code:    errors.InvalidArgs,
            Type:    "invalid_arguments",
            Message: "Failed to parse flags",
            Details: map[string]any{"error": err.Error()},
        })
    }

    okRes, errList, _, fatalErr := validatePack(*packDir, *strictVol, *strict)
    if fatalErr != nil {
        code := errors.ValidationFailed
        if stderrs.Is(fatalErr, errInvalidJSON) {
            code = errors.InvalidJSON
        }
        errors.ExitJSON(errors.CliError{
            Code:    code,
            Type:    "validation_failed",
            Message: fatalErr.Error(),
        })
    }

    if len(errList) > 0 {
        failure := validateFailure{
            Status:  "invalid",
            PackID:  okRes.PackID,
            Version: okRes.Version,
            Errors:  errList,
        }
        // Per spec: errors always JSON to stderr. Use ExitJSON to send invalid pack to stderr.
        failureJSON, _ := json.Marshal(failure)
        errors.ExitJSON(errors.CliError{
            Code:    errors.ValidationFailed,
            Type:    "validation_failed",
            Message: fmt.Sprintf("Pack validation failed with %d errors", len(errList)),
            Details: json.RawMessage(failureJSON),
        })
    }

    if *text {
        fmt.Printf("Pack is valid\nPack: %s v%s\nDefinitions: %d files (%d bytes)\nChecks passed: %d\n", okRes.PackID, okRes.Version, okRes.DefinitionCount, okRes.TotalSizeBytes, okRes.ChecksPassed)
        return int(errors.OK)
    }

    errors.PrintJSON(okRes)
    return int(errors.OK)
}

var errInvalidJSON = stderrs.New("invalid_json")
var errRootNotObject = stderrs.New("root_not_object")

func ValidatePack(packDir string, strictVol bool, strict bool) (validateSuccess, []validationError, error) {
    meta, errs, _, fatal := validatePack(packDir, strictVol, strict)
    return meta, errs, fatal
}

// ValidatePackForDigest validates the pack and returns the canonical, NFC-normalized,
// UTF-8 lex sorted list of definition file paths ("definitions/...") discovered on disk.
// It returns meta information, the canonical defs list, any validation errors, and a fatal error.
func ValidatePackForDigest(packDir string, strictVol bool) (validateSuccess, []string, []validationError, error) {
    meta, errs, fsDefs, fatal := validatePack(packDir, strictVol, false)
    return meta, fsDefs, errs, fatal
}

func validatePack(packDir string, strictVol bool, strict bool) (validateSuccess, []validationError, []string, error) {
    var errs []validationError
    var meta validateSuccess
    var checks int // Count actual checks performed

    root := filepath.Clean(packDir)

    packPath := filepath.Join(root, "pack.json")
    defDir := filepath.Join(root, "definitions")

    // Basic existence checks
    checks++
    if info, err := os.Lstat(packPath); err != nil {
        if os.IsNotExist(err) {
            errs = append(errs, validationError{Check: "pack_json_missing", Path: "pack.json", Message: "pack.json is required"})
        } else {
            return meta, nil, nil, err
        }
    } else {
        if info.Mode()&os.ModeSymlink != 0 {
            errs = append(errs, validationError{Check: "symlink_prohibited", Path: "pack.json", Message: "pack.json must not be a symlink"})
        }
        if info.IsDir() {
            errs = append(errs, validationError{Check: "pack_json_not_file", Path: "pack.json", Message: "pack.json must be a file"})
        }
    }

    checks++
    if info, err := os.Lstat(defDir); err != nil {
        if os.IsNotExist(err) {
            errs = append(errs, validationError{Check: "definitions_missing", Path: "definitions/", Message: "definitions/ directory is required"})
        } else {
            return meta, nil, nil, err
        }
    } else {
        if info.Mode()&os.ModeSymlink != 0 {
            errs = append(errs, validationError{Check: "symlink_prohibited", Path: "definitions/", Message: "definitions/ must not be a symlink"})
        }
        if !info.IsDir() {
            errs = append(errs, validationError{Check: "definitions_not_directory", Path: "definitions/", Message: "definitions/ must be a directory"})
        }
    }

    // Walk filesystem enforcing allowed layout and NFC paths
    allow := func(rel string, info os.FileInfo) bool {
        if rel == "pack.json" {
            return !info.IsDir()
        }
        if rel == "definitions" {
            return info.IsDir()
        }
        if strings.HasPrefix(rel, "definitions/") {
            if info.IsDir() {
                return true
            }
            return fsutil.IsJSON(rel)
        }
        return false
    }

    checks++
    walkEntries, walkErr := fsutil.WalkNoSymlink(fsutil.WalkOptions{BaseDir: root, AllowFiles: allow})
    if walkErr != nil {
        // Fail-closed on trust boundary violations
        switch e := walkErr.(type) {
        case fsutil.ErrDisallowedPath:
            errs = append(errs, validationError{Check: "prohibited_path", Path: e.Path, Message: "Only pack.json and definitions/ are allowed"})
            return meta, errs, nil, nil
        case fsutil.ErrSymlinkDetected:
            errs = append(errs, validationError{Check: "symlink_prohibited", Path: e.Path, Message: "Symlinks are not allowed in packs"})
            return meta, errs, nil, nil
        case fsutil.ErrNFCMismatch:
            errs = append(errs, validationError{Check: "nfc_mismatch", Path: e.Path, Message: "Paths must be NFC normalized"})
            return meta, errs, nil, nil
        default:
            return meta, nil, nil, walkErr
        }
    }

    // If pack.json missing, cannot continue to deep checks
    if !fileExists(packPath) {
        return meta, errs, nil, nil
    }

    checks++
    packObj, perr := loadJSONObject(packPath)
    if perr != nil {
        if stderrs.Is(perr, errInvalidJSON) {
            return meta, nil, nil, perr
        }
        if stderrs.Is(perr, errRootNotObject) {
            errs = append(errs, validationError{Check: "pack_json_not_object", Path: "pack.json", Message: "pack.json must have an object root"})
            return meta, errs, nil, nil
        }
        return meta, nil, nil, perr
    }

    // Required fields
    checks++
    packID, ok := packObj["pack_id"].(string)
    if !ok || strings.TrimSpace(packID) == "" {
        errs = append(errs, validationError{Check: "pack_id_missing", Path: "pack.json", Message: "pack_id is required"})
    }
    version, ok := packObj["version"].(string)
    if !ok || strings.TrimSpace(version) == "" {
        errs = append(errs, validationError{Check: "version_missing", Path: "pack.json", Message: "version is required"})
    } else if !semverRe.MatchString(version) {
        errs = append(errs, validationError{Check: "version_invalid", Path: "pack.json", Message: "version must be semantic version (x.y.z)"})
    }
    namespace, ok := packObj["namespace"].(string)
    if !ok || strings.TrimSpace(namespace) == "" {
        errs = append(errs, validationError{Check: "namespace_missing", Path: "pack.json", Message: "namespace is required"})
    }
    meta.PackID = packID
    meta.Version = version

    // Volatile scan on pack.json
    checks++
    packVol := volatile.ScanVolatile(packObj, volatile.ScanOptions{StrictHeuristic: strictVol})
    for _, v := range packVol {
        errs = append(errs, validationError{Check: "volatile_field_detected", Path: "pack.json", Message: fmt.Sprintf("Volatile field: %s", v.Field)})
    }

    checks++
    declDefsRaw, ok := packObj["definitions"]
    if !ok {
        errs = append(errs, validationError{Check: "definitions_missing", Path: "pack.json", Message: "definitions array is required"})
        return meta, errs, nil, nil
    }

    declPaths, arrErrs := normalizeDefinitionList(declDefsRaw)
    errs = append(errs, arrErrs...)

    // Validate sort order of declared definitions
    checks++
    if len(declPaths) > 0 {
        sorted := append([]string(nil), declPaths...)
        // Go string comparison is UTF-8 bytewise; required for deterministic PACK_DIGEST
        sort.Strings(sorted)
        if !equalStringSlices(declPaths, sorted) {
            errs = append(errs, validationError{Check: "definitions_not_sorted", Path: "pack.json", Message: "definitions array must be sorted UTF-8 lexicographic"})
        }
    }

    // Build actual filesystem list
    var fsDefs []string
    var totalSize int64
    for _, w := range walkEntries {
        if w.Info.IsDir() {
            continue
        }
        if strings.HasPrefix(w.RelPath, "definitions/") && fsutil.IsJSON(w.RelPath) {
            fsDefs = append(fsDefs, w.RelPath)
            totalSize += w.Info.Size()
        }
    }

    // Compare sets
    checks++
    declSet := make(map[string]struct{}, len(declPaths))
    for _, d := range declPaths {
        declSet[d] = struct{}{}
    }
    fsSet := make(map[string]struct{}, len(fsDefs))
    for _, d := range fsDefs {
        fsSet[d] = struct{}{}
    }

    for path := range fsSet {
        if _, ok := declSet[path]; !ok {
            errs = append(errs, validationError{Check: "filesystem_not_declared", Path: path, Message: "Definition exists on disk but not listed in pack.json"})
        }
    }
    for path := range declSet {
        if _, ok := fsSet[path]; !ok {
            errs = append(errs, validationError{Check: "missing_definition_file", Path: path, Message: "Definition listed in pack.json is missing on disk"})
        }
    }

    // Validate each definition file content
    checks++
    validatedSize := int64(0)
    for _, def := range fsDefs {
        full := filepath.Join(root, filepath.FromSlash(def))
        obj, derr := loadJSONObject(full)
        if derr != nil {
            if stderrs.Is(derr, errInvalidJSON) {
                return meta, nil, nil, derr
            }
            if stderrs.Is(derr, errRootNotObject) {
                errs = append(errs, validationError{Check: "definition_not_object", File: def, Message: "Definition JSON root must be object"})
                continue
            }
            return meta, nil, nil, derr
        }
        vols := volatile.ScanVolatile(obj, volatile.ScanOptions{StrictHeuristic: strictVol})
        for _, v := range vols {
            errs = append(errs, validationError{Check: "volatile_field_detected", File: def, Message: fmt.Sprintf("Volatile field: %s", v.Field)})
        }
        // Only count size if definition passed all checks
        if len(vols) == 0 {
            // Find size from walk entries
            for _, w := range walkEntries {
                if w.RelPath == def {
                    validatedSize += w.Info.Size()
                    break
                }
            }
        }
    }

    meta.DefinitionCount = len(fsDefs)
    meta.TotalSizeBytes = validatedSize
    meta.ChecksPassed = checks
    warnings := []string{}
    if strict && len(warnings) > 0 {
        // Future: promote warnings to errors in strict mode
    }
    meta.Warnings = warnings
    meta.Status = "valid"

    // Ensure deterministic ordering of defs for consumers
    sort.Strings(fsDefs)
    return meta, errs, fsDefs, nil
}

func loadJSONObject(path string) (map[string]any, error) {
    f, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer f.Close()

    dec := json.NewDecoder(f)
    dec.UseNumber()
    var v any
    if err := dec.Decode(&v); err != nil {
        return nil, errInvalidJSON
    }
    var extra any
    if err := dec.Decode(&extra); err != io.EOF {
        return nil, errInvalidJSON
    }

    obj, ok := v.(map[string]any)
    if !ok {
        return nil, errRootNotObject
    }
    return obj, nil
}

func normalizeDefinitionList(v any) ([]string, []validationError) {
    var errs []validationError
    arr, ok := v.([]any)
    if !ok {
        errs = append(errs, validationError{Check: "definitions_not_array", Path: "pack.json", Message: "definitions must be an array"})
        return nil, errs
    }
    out := make([]string, 0, len(arr))
    seen := make(map[string]struct{})
    for i, item := range arr {
        s, ok := item.(string)
        if !ok {
            errs = append(errs, validationError{Check: "definitions_invalid_entry", Path: fmt.Sprintf("pack.json:def[%d]", i), Message: "definition entries must be strings"})
            continue
        }
        s = strings.TrimSpace(s)
        if s == "" {
            errs = append(errs, validationError{Check: "definitions_invalid_entry", Path: fmt.Sprintf("pack.json:def[%d]", i), Message: "definition entry cannot be empty"})
            continue
        }
        if paths.ToNFC(s) != s {
            errs = append(errs, validationError{Check: "nfc_mismatch", Path: s, Message: "definition path must be NFC normalized"})
        }
        np, nErr := paths.NormalizePath("", s)
        if nErr != nil {
            errs = append(errs, validationError{Check: "path_invalid", Path: s, Message: "definition path is invalid"})
            continue
        }
        clean := np.Clean
        if !strings.HasPrefix(clean, "definitions/") {
            errs = append(errs, validationError{Check: "path_escape", Path: s, Message: "definition paths must start with definitions/"})
            continue
        }
        if !fsutil.IsJSON(clean) {
            errs = append(errs, validationError{Check: "path_extension", Path: s, Message: "definition files must be .json"})
            continue
        }
        if _, dup := seen[clean]; dup {
            errs = append(errs, validationError{Check: "duplicate_definition", Path: clean, Message: "duplicate definition entry"})
            continue
        }
        seen[clean] = struct{}{}
        out = append(out, clean)
    }
    return out, errs
}

func fileExists(path string) bool {
    _, err := os.Stat(path)
    return err == nil
}

func equalStringSlices(a, b []string) bool {
    if len(a) != len(b) {
        return false
    }
    for i := range a {
        if a[i] != b[i] {
            return false
        }
    }
    return true
}

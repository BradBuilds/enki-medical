package pack

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"unicode/utf8"

	"gdu/internal/errors"
	"gdu/internal/paths"
)

// volatileFieldBlacklist is the normative list of volatile fields
var volatileFieldBlacklist = map[string]bool{
	"created":              true,
	"created_at":           true,
	"created_timestamp":    true,
	"modified":             true,
	"modified_at":          true,
	"modified_timestamp":   true,
	"activated_at":         true,
	"activation_timestamp": true,
	"timestamp":            true,
	"usage_count":          true,
	"usage_metric":         true,
	"access_counter":       true,
	"hit_count":            true,
	"last_accessed":        true,
	"last_modified":        true,
	"last_used":            true,
}

var volatileFieldRegex = regexp.MustCompile(`(?i).*(time|timestamp|modified|created|access|usage|count|counter|metric).*`)

var semanticAllowlist = map[string]bool{
	"digit_count":           true,
	"place_value_positions": true,
	"carry_threshold":       true,
}

func CmdAdd(argv []string) int {
	fs := flag.NewFlagSet("add", flag.ContinueOnError)
	packDir := fs.String("pack-dir", ".", "")
	base := fs.String("base", "", "")
	strictVol := fs.Bool("strict-volatile", false, "")
	dryRun := fs.Bool("dry-run", false, "")
	text := fs.Bool("text", false, "")

	if err := fs.Parse(argv); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Failed to parse flags",
			Details: map[string]any{"error": err.Error()},
		})
	}

	rest := fs.Args()
	if len(rest) != 1 {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Missing <file-pattern>",
		})
	}
	filePattern := rest[0]

	// Resolve pack directory
	packRootDir, err := filepath.Abs(*packDir)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_pack_dir",
			Message: "Failed to resolve pack directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Check that pack.json and definitions/ exist
	packJSONPath := filepath.Join(packRootDir, "pack.json")
	defsPath := filepath.Join(packRootDir, "definitions")

	if _, err := os.Stat(packJSONPath); os.IsNotExist(err) {
		errors.ExitJSON(errors.CliError{
			Code:    errors.ValidationFailed,
			Type:    "pack_not_found",
			Message: "pack.json not found in pack directory",
			Details: map[string]any{"pack_dir": packRootDir},
		})
	}

	if _, err := os.Stat(defsPath); os.IsNotExist(err) {
		errors.ExitJSON(errors.CliError{
			Code:    errors.ValidationFailed,
			Type:    "definitions_dir_not_found",
			Message: "definitions/ directory not found in pack directory",
			Details: map[string]any{"pack_dir": packRootDir},
		})
	}

	// Resolve glob pattern to files
	matches, err := filepath.Glob(filePattern)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "glob_error",
			Message: "Failed to resolve file pattern",
			Details: map[string]any{"error": err.Error()},
		})
	}

	if len(matches) == 0 {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "no_files_matched",
			Message: "No files matched the given pattern",
			Details: map[string]any{"pattern": filePattern},
		})
	}

	// Normalize to NFC and sort by UTF-8 bytewise order
	for i := range matches {
		matches[i] = paths.ToNFC(matches[i])
	}
	sort.Slice(matches, func(i, j int) bool {
		return matches[i] < matches[j]
	})

	// Determine base directory for relative path computation
	baseDir := *base
	if baseDir == "" {
		baseDir = "."
	}
	baseDir, err = filepath.Abs(baseDir)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_base_dir",
			Message: "Failed to resolve base directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Process each file
	type addedFile struct {
		Source      string `json:"source"`
		Destination string `json:"destination"`
		SizeBytes   int64  `json:"size_bytes"`
	}

	type failedFile struct {
		Source string `json:"source"`
		Error  string `json:"error"`
	}

	var addedList []addedFile
	var failedList []failedFile
	var updatedDefinitions []string

	for _, srcPath := range matches {
		// Resolve to absolute path
		srcAbs, err := filepath.Abs(srcPath)
		if err != nil {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "failed to resolve path",
			})
			continue
		}

		// Read file
		fileBytes, err := os.ReadFile(srcAbs)
		if err != nil {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  fmt.Sprintf("read error: %v", err),
			})
			continue
		}

		// Check UTF-8
		if !utf8.Valid(fileBytes) {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "file is not valid UTF-8",
			})
			continue
		}

		// Parse JSON
		var obj map[string]any
		if err := json.Unmarshal(fileBytes, &obj); err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InvalidJSON,
				Type:    "json_parse_error",
				Message: "Invalid JSON in source file",
				Details: map[string]any{
					"file":  srcAbs,
					"error": err.Error(),
				},
			})
		}

		// Check that root is an object
		if len(obj) == 0 && string(fileBytes) != "{}" {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InvalidJSON,
				Type:    "not_object",
				Message: "JSON root must be an object",
				Details: map[string]any{"file": srcAbs},
			})
		}

		// Check for volatile fields
		volatileViolations := checkVolatileFields(obj, *strictVol)
		if len(volatileViolations) > 0 {
			errors.ExitJSON(errors.CliError{
				Code:    errors.VolatileDetected,
				Type:    "volatile_field_detected",
				Message: "File contains volatile fields",
				Details: map[string]any{
					"file":        srcAbs,
					"violations": volatileViolations,
				},
			})
		}

		// Determine destination path
		var destRel string
		if isInside(srcAbs, packRootDir) && isInside(srcAbs, filepath.Join(packRootDir, "definitions")) {
			// Already inside definitions/: register in-place
			rel, _ := filepath.Rel(packRootDir, srcAbs)
			destRel = filepath.ToSlash(rel)
		} else {
			// External file: compute relative path from base
			rel, err := filepath.Rel(baseDir, srcAbs)
			if err != nil {
				// Can't compute relative path: use basename
				destRel = filepath.ToSlash(filepath.Join("definitions", filepath.Base(srcAbs)))
			} else {
				destRel = filepath.ToSlash(filepath.Join("definitions", rel))
			}
		}

		// Normalize to NFC
		destRel = paths.ToNFC(destRel)

		// Validate destination path safety
		if !strings.HasPrefix(filepath.ToSlash(destRel), "definitions/") {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "destination would be outside definitions/",
			})
			continue
		}

		destAbs := filepath.Join(packRootDir, filepath.FromSlash(destRel))
		if !isInside(destAbs, filepath.Join(packRootDir, "definitions")) {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "destination path escapes definitions/",
			})
			continue
		}

		// Check for path safety: no .., no absolute, no drive prefix
		if strings.Contains(destRel, "..") || filepath.IsAbs(destRel) {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "destination path contains .. or is absolute",
			})
			continue
		}

		// On Windows, reject drive prefix
		if len(destRel) > 1 && destRel[1] == ':' {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  "destination path contains Windows drive prefix",
			})
			continue
		}

		// Check for collision
		if _, err := os.Stat(destAbs); err == nil {
			// File exists: check if bytes are identical
			existing, err := os.ReadFile(destAbs)
			if err != nil || string(existing) != string(fileBytes) {
				failedList = append(failedList, failedFile{
					Source: srcPath,
					Error:  "destination file exists with different content",
				})
				continue
			}
			// Bytes are identical: skip (idempotent)
		} else if !os.IsNotExist(err) {
			failedList = append(failedList, failedFile{
				Source: srcPath,
				Error:  fmt.Sprintf("stat error: %v", err),
			})
			continue
		}

		if !*dryRun {
			// Create subdirectories if needed
			destDirPath := filepath.Dir(destAbs)
			if err := os.MkdirAll(destDirPath, 0755); err != nil {
				failedList = append(failedList, failedFile{
					Source: srcPath,
					Error:  fmt.Sprintf("mkdir error: %v", err),
				})
				continue
			}

			// Copy/write file
			if err := os.WriteFile(destAbs, fileBytes, 0644); err != nil {
				failedList = append(failedList, failedFile{
					Source: srcPath,
					Error:  fmt.Sprintf("write error: %v", err),
				})
				continue
			}
		}

		addedList = append(addedList, addedFile{
			Source:      srcAbs,
			Destination: destRel,
			SizeBytes:   int64(len(fileBytes)),
		})
		updatedDefinitions = append(updatedDefinitions, destRel)
	}

	if len(failedList) > 0 && len(addedList) == 0 {
		errors.ExitJSON(errors.CliError{
			Code:    errors.ValidationFailed,
			Type:    "all_files_failed",
			Message: "No files were added successfully",
			Details: map[string]any{"failed": failedList},
		})
	}

	if !*dryRun && len(addedList) > 0 {
		// Read current pack.json
		packBytes, err := os.ReadFile(packJSONPath)
		if err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.ValidationFailed,
				Type:    "pack_read_failed",
				Message: "Failed to read pack.json",
				Details: map[string]any{"error": err.Error()},
			})
		}

		var packObj map[string]any
		if err := json.Unmarshal(packBytes, &packObj); err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InvalidJSON,
				Type:    "pack_parse_failed",
				Message: "Failed to parse pack.json",
				Details: map[string]any{"error": err.Error()},
			})
		}

		// Merge new definitions with existing
		var existingDefs []string
		if defs, ok := packObj["definitions"].([]any); ok {
			for _, d := range defs {
				if s, ok := d.(string); ok {
					existingDefs = append(existingDefs, paths.ToNFC(s))
				}
			}
		}

		// Combine and sort
		allDefs := append(existingDefs, updatedDefinitions...)
		sort.Strings(allDefs)

		// Deduplicate while preserving order
		seen := make(map[string]bool)
		var uniqueDefs []string
		for _, d := range allDefs {
			if !seen[d] {
				uniqueDefs = append(uniqueDefs, d)
				seen[d] = true
			}
		}

		packObj["definitions"] = uniqueDefs

		// Write pack.json with deterministic formatting
		updatedPackBytes, err := json.MarshalIndent(packObj, "", "  ")
		if err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InvalidJSON,
				Type:    "pack_marshal_failed",
				Message: "Failed to marshal updated pack.json",
				Details: map[string]any{"error": err.Error()},
			})
		}

		if err := os.WriteFile(packJSONPath, append(updatedPackBytes, '\n'), 0644); err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InstallFailed,
				Type:    "pack_write_failed",
				Message: "Failed to write updated pack.json",
				Details: map[string]any{"error": err.Error()},
			})
		}
	}

	// Output
	if *text {
		if len(addedList) > 0 {
			fmt.Printf("✓ Added %d file(s) to pack\n", len(addedList))
			for _, f := range addedList {
				fmt.Printf("  %s (%d bytes)\n", f.Destination, f.SizeBytes)
			}
		}
		if len(failedList) > 0 {
			fmt.Printf("⚠ %d file(s) failed:\n", len(failedList))
			for _, f := range failedList {
				fmt.Printf("  %s: %s\n", f.Source, f.Error)
			}
		}
		return 0
	}

	// JSON output
	output := map[string]any{
		"status": "success",
		"added":  addedList,
	}
	if len(failedList) > 0 {
		output["failed"] = failedList
	}

	errors.PrintJSON(output)
	return 0
}

func checkVolatileFields(obj map[string]any, strict bool) []map[string]any {
	var violations []map[string]any

	for key := range obj {
		// Check blacklist
		if volatileFieldBlacklist[key] {
			violations = append(violations, map[string]any{
				"field":  key,
				"reason": "Timestamp or metric fields are prohibited",
			})
			continue
		}

		// Check strict regex
		if strict && volatileFieldRegex.MatchString(key) && !semanticAllowlist[key] {
			violations = append(violations, map[string]any{
				"field":  key,
				"reason": "Matches volatile field pattern (use allowlist for semantic constants)",
			})
		}
	}

	return violations
}

// isInside returns true if target is inside the root directory tree.
func isInside(target, root string) bool {
	target = filepath.Clean(target)
	root = filepath.Clean(root)

	if target == root {
		return true
	}

	rel, err := filepath.Rel(root, target)
	if err != nil {
		return false
	}

	return !strings.HasPrefix(rel, "..")
}

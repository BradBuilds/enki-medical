package pack

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"gdu/internal/errors"
	"gdu/internal/paths"
)

// InitPackJSON represents the initial pack.json structure with no volatile fields.
type InitPackJSON struct {
	PackID       string   `json:"pack_id"`
	Version      string   `json:"version"`
	Namespace    string   `json:"namespace"`
	Author       string   `json:"author,omitempty"`
	Definitions  []string `json:"definitions"`
	Dependencies []string `json:"dependencies,omitempty"`
	Metadata     map[string]any `json:"metadata,omitempty"`
}

func CmdInit(argv []string) int {
	fs := flag.NewFlagSet("init", flag.ContinueOnError)
	packID := fs.String("pack-id", "", "")
	version := fs.String("version", "", "")
	namespace := fs.String("namespace", "", "")
	author := fs.String("author", "", "")
	output := fs.String("output", "", "")
	force := fs.Bool("force", false, "")
	text := fs.Bool("text", false, "")

	if err := fs.Parse(argv); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Failed to parse flags",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Validate required arguments
	if *packID == "" || *version == "" {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Missing required flags: --pack-id and --version",
		})
	}

	// Set defaults
	ns := *namespace
	if ns == "" {
		ns = *packID
	}

	outDir := *output
	if outDir == "" {
		outDir = *packID
	}

	// Resolve output directory (absolute path)
	outDir, err := filepath.Abs(outDir)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Failed to resolve output directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Check if directory exists
	stat, err := os.Stat(outDir)
	if err == nil {
		// Directory exists
		if !*force {
			// --force not set: fail closed
			errors.ExitJSON(errors.CliError{
				Code:    errors.DirConflict,
				Type:    "directory_exists",
				Message: "Output directory already exists (use --force to allow)",
				Details: map[string]any{"path": outDir},
			})
		}

		// --force set: validate existing content
		if !stat.IsDir() {
			errors.ExitJSON(errors.CliError{
				Code:    errors.DirConflict,
				Type:    "not_a_directory",
				Message: "Output path exists but is not a directory",
				Details: map[string]any{"path": outDir},
			})
		}

		// Check that directory contains only pack.json and definitions/
		entries, err := os.ReadDir(outDir)
		if err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InstallFailed,
				Type:    "cannot_read_directory",
				Message: "Failed to read directory contents",
				Details: map[string]any{"error": err.Error()},
			})
		}

		for _, entry := range entries {
			name := entry.Name()
			if name != "pack.json" && name != "definitions" {
				// Extra files found: fail closed
				errors.ExitJSON(errors.CliError{
					Code:    errors.DirConflict,
					Type:    "directory_has_extra_files",
					Message: "Directory contains files other than pack.json and definitions/",
					Details: map[string]any{"unexpected_name": name},
				})
			}

			// If it's definitions/, verify it's a directory and not a symlink
			if name == "definitions" {
				if entry.Type()&os.ModeSymlink != 0 {
					errors.ExitJSON(errors.CliError{
						Code:    errors.DirConflict,
						Type:    "symlink_not_allowed",
						Message: "definitions/ must be a real directory, not a symlink",
						Details: map[string]any{"path": filepath.Join(outDir, "definitions")},
					})
				}
				if !entry.IsDir() {
					errors.ExitJSON(errors.CliError{
						Code:    errors.DirConflict,
						Type:    "not_a_directory",
						Message: "definitions exists but is not a directory",
						Details: map[string]any{"path": filepath.Join(outDir, "definitions")},
					})
				}
			}
		}
	} else if !os.IsNotExist(err) {
		// Some other error (permission denied, etc.)
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "stat_failed",
			Message: "Failed to check directory status",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Create directory if it doesn't exist
	if err := os.MkdirAll(outDir, 0755); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "mkdir_failed",
			Message: "Failed to create output directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Ensure definitions/ directory exists and is not a symlink
	defsDir := filepath.Join(outDir, "definitions")
	defsStat, err := os.Lstat(defsDir)
	if err == nil {
		// definitions/ exists
		if defsStat.Mode()&os.ModeSymlink != 0 {
			errors.ExitJSON(errors.CliError{
				Code:    errors.DirConflict,
				Type:    "symlink_not_allowed",
				Message: "definitions/ must be a real directory, not a symlink",
				Details: map[string]any{"path": defsDir},
			})
		}
		if !defsStat.IsDir() {
			errors.ExitJSON(errors.CliError{
				Code:    errors.DirConflict,
				Type:    "not_a_directory",
				Message: "definitions exists but is not a directory",
				Details: map[string]any{"path": defsDir},
			})
		}
	} else if os.IsNotExist(err) {
		// Create it
		if err := os.MkdirAll(defsDir, 0755); err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.InstallFailed,
				Type:    "mkdir_failed",
				Message: "Failed to create definitions/ directory",
				Details: map[string]any{"error": err.Error()},
			})
		}
	} else {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "stat_failed",
			Message: "Failed to check definitions/ directory status",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Build pack.json (normalized to NFC for pack_id and namespace if they come from user input)
	packJSON := InitPackJSON{
		PackID:       paths.ToNFC(*packID),
		Version:      *version,
		Namespace:    paths.ToNFC(ns),
		Definitions:  []string{},
		Dependencies: []string{},
	}

	if *author != "" {
		packJSON.Author = paths.ToNFC(*author)
	}

	// Write pack.json deterministically (struct field order is stable)
	packPath := filepath.Join(outDir, "pack.json")
	packBytes, err := json.MarshalIndent(packJSON, "", "  ")
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidJSON,
			Type:    "json_marshal_failed",
			Message: "Failed to marshal pack.json",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Ensure UTF-8 and write atomically
	if err := os.WriteFile(packPath, append(packBytes, '\n'), 0644); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "write_failed",
			Message: "Failed to write pack.json",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Output result
	if *text {
		fmt.Printf("✓ Created pack.json in %s/\n", outDir)
		fmt.Printf("  Pack ID: %s\n", *packID)
		fmt.Printf("  Version: %s\n", *version)
		fmt.Printf("  Namespace: %s\n", ns)
		return 0
	}

	// JSON output
	output_json := map[string]any{
		"status":             "created",
		"pack_id":            *packID,
		"version":            *version,
		"namespace":          ns,
		"output_path":        outDir,
		"definitions_count":  0,
	}
	if *author != "" {
		output_json["author"] = *author
	}

	errors.PrintJSON(output_json)
	return 0
}

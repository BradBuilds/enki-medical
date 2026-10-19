package pack

import (
	stderrs "errors"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"unicode/utf8"

	"gdu/internal/digest"
	"gdu/internal/errors"
)

func CmdDigest(argv []string) int {
	flagSet := flag.NewFlagSet("digest", flag.ContinueOnError)
	packDir := flagSet.String("pack-dir", ".", "")
	showManifest := flagSet.Bool("show-manifest", false, "")
	digestFormat := flagSet.String("digest-format", "hex", "")
	text := flagSet.Bool("text", false, "")

	if err := flagSet.Parse(argv); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Failed to parse flags",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Validate digest-format
	if *digestFormat != "hex" && *digestFormat != "short" {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "Invalid --digest-format (must be 'hex' or 'short')",
			Details: map[string]any{"digest_format": *digestFormat},
		})
	}

	// Step 1: Validate pack (fail-closed) and reuse canonical defs
	_, defs, validationErrs, err := ValidatePackForDigest(*packDir, false)
	if err != nil {
		code := errors.ValidationFailed
		if stderrs.Is(err, errInvalidJSON) {
			code = errors.InvalidJSON
		}
		errors.ExitJSON(errors.CliError{
			Code:    code,
			Type:    "validation_failed",
			Message: err.Error(),
		})
	}

	if len(validationErrs) > 0 {
		errors.ExitJSON(errors.CliError{
			Code:    errors.ValidationFailed,
			Type:    "validation_failed",
			Message: "Pack validation failed during digest",
			Details: map[string]any{"errors": validationErrs},
		})
	}

	// Step 2: Hash the exact validated definition paths
	root := filepath.Clean(*packDir)

	// Step 3: Compute SHA-256 for each file and build manifest
	var files []digest.ManifestFile
	for _, rel := range defs {
		fullPath := filepath.Join(root, filepath.FromSlash(rel))
		fileBytes, err := os.ReadFile(fullPath)
		if err != nil {
			errors.ExitJSON(errors.CliError{
				Code:    errors.DigestFailed,
				Type:    "digest_error",
				Message: "Failed to read file for hashing",
				Details: map[string]any{
					"path":  rel,
					"error": err.Error(),
				},
			})
		}

		if !utf8.Valid(fileBytes) {
			errors.ExitJSON(errors.CliError{
				Code:    errors.DigestFailed,
				Type:    "digest_error",
				Message: "Definition file is not valid UTF-8",
				Details: map[string]any{"path": rel},
			})
		}

		sha256Hex := digest.FileHash(fileBytes)

		files = append(files, digest.ManifestFile{
			Path:   rel,
			SHA256: sha256Hex,
		})
	}

	// Step 4: Compute pack digest
	result, err := digest.ComputePackDigest(files)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.DigestFailed,
			Type:    "digest_error",
			Message: "Failed to compute digest",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 5: Apply digest format (short = 12 chars per spec)
	packDigest := result.PackDigest
	if *digestFormat == "short" {
		const shortLen = 12 // Per spec: 12-char hex
		if len(result.PackDigestHex) >= shortLen {
			packDigest = "sha256:" + result.PackDigestHex[:shortLen]
		}
	}

	// Step 6: Output result
	if *text {
		// Text output per spec
		fmt.Printf("PACK_DIGEST: %s\n", packDigest)
		fmt.Println("Manifest version: 1")
		fmt.Printf("Files: %d\n", len(result.Manifest))
		return 0
	}

	// JSON output (default) - per spec fields only
	output := map[string]any{
		"pack_digest":      packDigest,
		"manifest_version": "1",
		"file_count":       len(result.Manifest),
	}

	if *showManifest {
		output["manifest"] = map[string]any{
			"version": "1",
			"files":   result.Manifest,
		}
	}

	errors.PrintJSON(output)
	return 0
}

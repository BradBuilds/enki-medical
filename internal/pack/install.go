package pack

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	stderrs "errors"

	"gdu/internal/digest"
	"gdu/internal/errors"
)

func CmdInstall(argv []string) int {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	packDir := fs.String("pack-dir", ".", "")
	registry := fs.String("registry", "", "")
	verify := fs.Bool("verify", false, "")
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
	if *registry == "" {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_arguments",
			Message: "--registry is required",
		})
	}

	// Step 1: Validate pack and compute digest
	meta, defs, validationErrs, err := ValidatePackForDigest(*packDir, false)
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
			Message: "Pack validation failed during install",
			Details: map[string]any{"errors": validationErrs},
		})
	}

	// Step 2: Compute digest (same as digest command)
	root := filepath.Clean(*packDir)
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

		// No UTF-8 check needed here; ValidatePackForDigest already verified it
		sha256Sum := digest.FileHash(fileBytes)

		files = append(files, digest.ManifestFile{
			Path:   rel,
			SHA256: sha256Sum,
		})
	}

	result, err := digest.ComputePackDigest(files)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.DigestFailed,
			Type:    "digest_error",
			Message: "Failed to compute digest",
			Details: map[string]any{"error": err.Error()},
		})
	}

	packDigestHex := result.PackDigestHex

	// Step 3: Determine install paths
	registryPath, err := filepath.Abs(*registry)
	if err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InvalidArgs,
			Type:    "invalid_registry_path",
			Message: "Failed to resolve registry path",
			Details: map[string]any{"error": err.Error()},
		})
	}

	packsDir := filepath.Join(registryPath, "packs")
	targetDir := filepath.Join(packsDir, packDigestHex)
	tmpDir := filepath.Join(packsDir, packDigestHex+".tmp")

	if *dryRun {
		// Just show what would happen
		stat, err := os.Stat(targetDir)
		status := "would_install"
		if err == nil && stat.IsDir() {
			status = "would_already_exist"
		}

		if *text {
			fmt.Printf("DRY-RUN: %s\n", status)
			fmt.Printf("  Pack: %s v%s\n", meta.PackID, meta.Version)
			fmt.Printf("  Digest: sha256:%s\n", packDigestHex)
			fmt.Printf("  Location: %s\n", targetDir)
			return 0
		}

		output := map[string]any{
			"status":      status,
			"pack_id":     meta.PackID,
			"version":     meta.Version,
			"pack_digest": "sha256:" + packDigestHex,
			"install_path": targetDir,
		}
		errors.PrintJSON(output)
		return 0
	}

	// Step 4: Check if already installed
	stat, err := os.Stat(targetDir)
	if err == nil && stat.IsDir() {
		// Already exists: if --verify, verify it
		if *verify {
			// Recompute digest of installed pack
			installedDefsDir := filepath.Join(targetDir, "definitions")
			var installedFiles []digest.ManifestFile

			err := filepath.Walk(installedDefsDir, func(path string, info os.FileInfo, err error) error {
				if err != nil {
					return err
				}
				if !info.IsDir() && filepath.Ext(path) == ".json" {
					rel, err := filepath.Rel(targetDir, path)
					if err != nil {
						return err
					}
					rel = filepath.ToSlash(rel)

					fileBytes, err := os.ReadFile(path)
					if err != nil {
						return err
					}

					sha256Sum := digest.FileHash(fileBytes)
					installedFiles = append(installedFiles, digest.ManifestFile{
						Path:   rel,
						SHA256: sha256Sum,
					})
				}
				return nil
			})
			if err != nil {
				errors.ExitJSON(errors.CliError{
					Code:    errors.VerificationFailed,
					Type:    "verification_error",
					Message: "Failed to read installed pack for verification",
					Details: map[string]any{"error": err.Error()},
				})
			}

			// Verify digest matches
			installedResult, err := digest.ComputePackDigest(installedFiles)
			if err != nil {
				errors.ExitJSON(errors.CliError{
					Code:    errors.VerificationFailed,
					Type:    "digest_error",
					Message: "Failed to compute digest for verification",
					Details: map[string]any{"error": err.Error()},
				})
			}

			if installedResult.PackDigestHex != packDigestHex {
				errors.ExitJSON(errors.CliError{
					Code:    errors.VerificationFailed,
					Type:    "digest_mismatch",
					Message: "Installed pack digest does not match",
					Details: map[string]any{
						"expected": packDigestHex,
						"actual":   installedResult.PackDigestHex,
					},
				})
			}
		}

		// Output: already installed
		if *text {
			fmt.Printf("✓ Pack already installed (digest match)\n")
			fmt.Printf("  Pack: %s v%s\n", meta.PackID, meta.Version)
			fmt.Printf("  Digest: sha256:%s\n", packDigestHex)
			fmt.Printf("  Location: %s\n", targetDir)
			return 0
		}

		output := map[string]any{
			"status":              "already_installed",
			"pack_id":             meta.PackID,
			"version":             meta.Version,
			"pack_digest":         "sha256:" + packDigestHex,
			"install_path":        targetDir,
			"install_path_note":   "Path uses PACK_DIGEST_HEX (no sha256: prefix)",
		}
		errors.PrintJSON(output)
		return 0
	} else if !os.IsNotExist(err) {
		// Some other error
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "stat_failed",
			Message: "Failed to check install path",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 5: Create packs directory if needed
	if err := os.MkdirAll(packsDir, 0755); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "mkdir_failed",
			Message: "Failed to create packs directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 6: Clean up any leftover .tmp from previous crash
	_ = os.RemoveAll(tmpDir)

	// Step 7: Create tmp directory
	if err := os.MkdirAll(tmpDir, 0755); err != nil {
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "mkdir_failed",
			Message: "Failed to create temporary install directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 8: Copy pack.json
	packJSONSrc := filepath.Join(root, "pack.json")
	packJSONDst := filepath.Join(tmpDir, "pack.json")
	packBytes, err := os.ReadFile(packJSONSrc)
	if err != nil {
		_ = os.RemoveAll(tmpDir)
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "copy_failed",
			Message: "Failed to read pack.json",
			Details: map[string]any{"error": err.Error()},
		})
	}

	if err := os.WriteFile(packJSONDst, packBytes, 0644); err != nil {
		_ = os.RemoveAll(tmpDir)
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "copy_failed",
			Message: "Failed to write pack.json",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 9: Copy definitions/ directory recursively
	srcDefsDir := filepath.Join(root, "definitions")
	dstDefsDir := filepath.Join(tmpDir, "definitions")

	if err := copyDirRecursive(srcDefsDir, dstDefsDir); err != nil {
		_ = os.RemoveAll(tmpDir)
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "copy_failed",
			Message: "Failed to copy definitions directory",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Step 10: Atomic rename tmp → target
	if err := os.Rename(tmpDir, targetDir); err != nil {
		_ = os.RemoveAll(tmpDir)
		errors.ExitJSON(errors.CliError{
			Code:    errors.InstallFailed,
			Type:    "rename_failed",
			Message: "Failed to finalize installation (atomic rename)",
			Details: map[string]any{"error": err.Error()},
		})
	}

	// Success output
	if *text {
		fmt.Printf("✓ Pack installed successfully\n")
		fmt.Printf("  Pack: %s v%s\n", meta.PackID, meta.Version)
		fmt.Printf("  Digest: sha256:%s\n", packDigestHex)
		fmt.Printf("  Location: %s\n", targetDir)
		return 0
	}

	output := map[string]any{
		"status":             "installed",
		"pack_id":            meta.PackID,
		"version":            meta.Version,
		"pack_digest":        "sha256:" + packDigestHex,
		"install_path":       targetDir,
		"install_path_note":  "Path uses PACK_DIGEST_HEX (no sha256: prefix)",
		"verified":           false,
	}
	errors.PrintJSON(output)
	return 0
}

// copyDirRecursive copies src directory to dst, including all files and subdirectories.
func copyDirRecursive(src, dst string) error {
	if err := os.MkdirAll(dst, 0755); err != nil {
		return err
	}

	entries, err := os.ReadDir(src)
	if err != nil {
		return err
	}

	for _, entry := range entries {
		srcPath := filepath.Join(src, entry.Name())
		dstPath := filepath.Join(dst, entry.Name())

		if entry.IsDir() {
			if err := copyDirRecursive(srcPath, dstPath); err != nil {
				return err
			}
		} else {
			// Copy file
			bytes, err := os.ReadFile(srcPath)
			if err != nil {
				return err
			}
			if err := os.WriteFile(dstPath, bytes, 0644); err != nil {
				return err
			}
		}
	}

	return nil
}

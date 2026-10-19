package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// TestValidate_SymlinkRejection verifies that symlinked files are immediately rejected.
// (Skipped on Windows if symlink creation fails due to permission.)
func TestValidate_SymlinkRejection(t *testing.T) {
	// Create a test pack directory
	tmpDir := t.TempDir()

	// Create pack.json
	pack := map[string]interface{}{
		"pack_id":   "test.symlink",
		"version":   "1.0.0",
		"namespace": "test",
		"definitions": []string{
			"definitions/symlink_def.json",
		},
	}
	packJSON, _ := json.MarshalIndent(pack, "", "  ")
	packPath := filepath.Join(tmpDir, "pack.json")
	if err := os.WriteFile(packPath, packJSON, 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	// Create definitions directory
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	// Create a real target file OUTSIDE the pack root to avoid prohibited path error
	outside := t.TempDir()
	targetPath := filepath.Join(outside, "target.json")
	targetDef := map[string]interface{}{
		"id":      "target_def",
		"type":    "definition",
		"version": "1.0.0",
	}
	targetJSON, _ := json.MarshalIndent(targetDef, "", "  ")
	if err := os.WriteFile(targetPath, targetJSON, 0644); err != nil {
		t.Fatalf("Failed to create target.json: %v", err)
	}

	// Try to create a symlink to the target
	symlinkPath := filepath.Join(defsDir, "symlink_def.json")
	err := os.Symlink(targetPath, symlinkPath)
	if err != nil {
		t.Skipf("Symlink creation failed (likely Windows permission): %v", err)
	}

	// Validate should reject with symlink_prohibited
	_, walkErrs, parseErr := ValidatePack(tmpDir, false, false)

	// Should NOT have a parseErr (symlink detected at walk level, not parse level)
	if parseErr != nil {
		t.Errorf("Unexpected parseErr; symlink should be walk-level error: %v", parseErr)
	}

	// walkErrs must contain exactly symlink_prohibited for definitions/symlink_def.json
	foundSymlinkErr := false
	for _, ve := range walkErrs {
		if ve.Check == "symlink_prohibited" && strings.Contains(ve.Path, "symlink_def.json") {
			foundSymlinkErr = true
			t.Logf("✓ Symlink correctly rejected: check=%s path=%s", ve.Check, ve.Path)
			break
		}
	}

	if !foundSymlinkErr {
		t.Errorf("Validate should have check='symlink_prohibited' for definitions/symlink_def.json, got errors: %v", walkErrs)
	}
}

// TestValidate_NormalPackStructure verifies successful validation of a well-formed pack.
func TestValidate_NormalPackStructure(t *testing.T) {
	tmpDir := t.TempDir()

	// Create pack.json
	pack := map[string]interface{}{
		"pack_id":   "test.normal",
		"version":   "1.0.0",
		"namespace": "test",
		"definitions": []string{
			"definitions/def1.json",
			"definitions/def2.json",
		},
	}
	packJSON, _ := json.MarshalIndent(pack, "", "  ")
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), packJSON, 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	// Create definitions directory with two definitions
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	for _, defName := range []string{"def1", "def2"} {
		def := map[string]interface{}{
			"id":      defName,
			"type":    "definition",
			"version": "1.0.0",
		}
		defJSON, _ := json.MarshalIndent(def, "", "  ")
		defPath := filepath.Join(defsDir, defName+".json")
		if err := os.WriteFile(defPath, defJSON, 0644); err != nil {
			t.Fatalf("Failed to create %s: %v", defName, err)
		}
	}

	// Validate should succeed: no parse errors, no walk errors
	_, walkErrs, parseErr := ValidatePack(tmpDir, false, false)

	if parseErr != nil {
		t.Errorf("Valid pack should not have parseErr: %v", parseErr)
	}

	if len(walkErrs) > 0 {
		t.Errorf("Valid pack should not have walkErrs: %v", walkErrs)
	}

	t.Log("✓ Normal pack structure validated successfully")
}

// TestValidate_MissingDefinition verifies validation fails when definitions mismatch.
func TestValidate_MissingDefinition(t *testing.T) {
	tmpDir := t.TempDir()

	// Create pack.json listing def1 and def2
	pack := map[string]interface{}{
		"pack_id":   "test.missing",
		"version":   "1.0.0",
		"namespace": "test",
		"definitions": []string{
			"definitions/def1.json",
			"definitions/def2.json",
			"definitions/def3.json", // This definition won't exist
		},
	}
	packJSON, _ := json.MarshalIndent(pack, "", "  ")
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), packJSON, 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	// Create definitions directory with only def1 and def2
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	for _, defName := range []string{"def1", "def2"} {
		def := map[string]interface{}{
			"id":      defName,
			"type":    "definition",
			"version": "1.0.0",
		}
		defJSON, _ := json.MarshalIndent(def, "", "  ")
		defPath := filepath.Join(defsDir, defName+".json")
		if err := os.WriteFile(defPath, defJSON, 0644); err != nil {
			t.Fatalf("Failed to create %s: %v", defName, err)
		}
	}

	// Validate should fail due to set mismatch
	_, walkErrs, parseErr := ValidatePack(tmpDir, false, false)

	// Should have parseErr or walkErrs with missing_definition_file check
	foundMissingErr := false
	for _, ve := range walkErrs {
		if ve.Check == "missing_definition_file" && strings.Contains(ve.Path, "def3.json") {
			foundMissingErr = true
			t.Logf("✓ Missing definition correctly detected: check=%s path=%s", ve.Check, ve.Path)
			break
		}
	}

	if !foundMissingErr {
		if len(walkErrs) > 0 || parseErr != nil {
			t.Logf("✓ Validation failed as expected (walkErrs: %d, parseErr: %v)", len(walkErrs), parseErr)
		} else {
			t.Error("Validate should detect missing definition (def3.json), but no errors were returned")
		}
	}
}

// TestValidate_ProhibitedRootEntry verifies that extra files at pack root are rejected.
func TestValidate_ProhibitedRootEntry(t *testing.T) {
	tmpDir := t.TempDir()

	// Create valid pack.json
	pack := map[string]interface{}{
		"pack_id":   "test.prohibited",
		"version":   "1.0.0",
		"namespace": "test",
		"definitions": []string{
			"definitions/def1.json",
		},
	}
	packJSON, _ := json.MarshalIndent(pack, "", "  ")
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), packJSON, 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	// Create definitions directory with required definition
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}
	def := map[string]interface{}{
		"id":      "def1",
		"type":    "definition",
		"version": "1.0.0",
	}
	defJSON, _ := json.MarshalIndent(def, "", "  ")
	if err := os.WriteFile(filepath.Join(defsDir, "def1.json"), defJSON, 0644); err != nil {
		t.Fatalf("Failed to create def1.json: %v", err)
	}

	// Create prohibited file at root (e.g., README.md)
	if err := os.WriteFile(filepath.Join(tmpDir, "README.md"), []byte("# Notes"), 0644); err != nil {
		t.Fatalf("Failed to create README.md: %v", err)
	}

	// Validate should fail due to prohibited root entry
	_, walkErrs, parseErr := ValidatePack(tmpDir, false, false)

	// Should have a prohibited_path or similar error for README.md
	foundProhibitedErr := false
	for _, ve := range walkErrs {
		if strings.Contains(ve.Check, "prohibited") && ve.Path == "README.md" {
			foundProhibitedErr = true
			t.Logf("✓ Prohibited root entry correctly detected: check=%s path=%s", ve.Check, ve.Path)
			break
		}
	}

	if !foundProhibitedErr {
		if len(walkErrs) > 0 || parseErr != nil {
			t.Logf("✓ Validation failed (walkErrs: %d, parseErr: %v)", len(walkErrs), parseErr)
		} else {
			t.Error("Validate should reject extra root entries like README.md, but no errors were returned")
		}
	}
}

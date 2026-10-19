package pack

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"gdu/internal/errors"
)

// TestCmdDigest_GoldenFixture verifies that CmdDigest produces the exact golden digest
// for the fixture pack (alpha, beta, äpfel.json).
func TestCmdDigest_GoldenFixture(t *testing.T) {
	// Create temporary fixture pack
	tmpDir := t.TempDir()
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	// Create pack.json with required fields
	packJSON := `{"pack_id":"test-pack","namespace":"test","version":"1.0.0","definitions":["definitions/alpha.json","definitions/beta.json","definitions/äpfel.json"]}`
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte(packJSON), 0644); err != nil {
		t.Fatalf("Failed to write pack.json: %v", err)
	}

	// Create 3 definition files
	alphaContent := `{"id":"alpha","type":"assertion","name":"Alpha Test"}`
	if err := os.WriteFile(filepath.Join(defsDir, "alpha.json"), []byte(alphaContent), 0644); err != nil {
		t.Fatalf("Failed to write alpha.json: %v", err)
	}

	betaContent := `{"id":"beta","type":"audit","name":"Beta Tëst"}`
	if err := os.WriteFile(filepath.Join(defsDir, "beta.json"), []byte(betaContent), 0644); err != nil {
		t.Fatalf("Failed to write beta.json: %v", err)
	}

	apfelContent := `{"id":"apfel","type":"assertion","name":"Äpfel"}`
	if err := os.WriteFile(filepath.Join(defsDir, "äpfel.json"), []byte(apfelContent), 0644); err != nil {
		t.Fatalf("Failed to write äpfel.json: %v", err)
	}

	// Inject output buffer
	outBuf := &bytes.Buffer{}
	origStdout := errors.Stdout
	errors.Stdout = outBuf
	defer func() { errors.Stdout = origStdout }()

	// Run CmdDigest
	code := CmdDigest([]string{"-pack-dir", tmpDir})

	// Verify exit code
	if code != 0 {
		t.Errorf("Expected exit code 0, got %d", code)
	}

	// Verify output is valid JSON
	var result map[string]any
	if err := json.Unmarshal(outBuf.Bytes(), &result); err != nil {
		t.Fatalf("Failed to parse JSON output: %v (output: %s)", err, outBuf.String())
	}

	// Verify golden digest
	packDigest, ok := result["pack_digest"].(string)
	if !ok {
		t.Fatalf("pack_digest not found or not string in output: %v", result)
	}

	const expectedGolden = "sha256:3344af39bc4c022e5be467d137c4424321127c7807a63dce03174f608b22e438"
	if packDigest != expectedGolden {
		t.Errorf("PACK_DIGEST mismatch: expected %s, got %s", expectedGolden, packDigest)
	}

	// Verify file count
	fileCount, ok := result["file_count"].(float64)
	if !ok || int(fileCount) != 3 {
		t.Errorf("Expected 3 files, got %v", fileCount)
	}

	t.Logf("✓ CmdDigest golden test passed: %s (3 files)", packDigest)
}

// TestCmdDigest_WithManifest verifies that --show-manifest includes the manifest in output.
func TestCmdDigest_WithManifest(t *testing.T) {
	tmpDir := t.TempDir()
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	packJSON := `{"pack_id":"test-pack","namespace":"test","version":"1.0.0","definitions":["definitions/simple.json"]}`
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte(packJSON), 0644); err != nil {
		t.Fatalf("Failed to write pack.json: %v", err)
	}

	defContent := `{"id":"simple","type":"assertion","name":"Simple"}`
	if err := os.WriteFile(filepath.Join(defsDir, "simple.json"), []byte(defContent), 0644); err != nil {
		t.Fatalf("Failed to write simple.json: %v", err)
	}

	outBuf := &bytes.Buffer{}
	origStdout := errors.Stdout
	errors.Stdout = outBuf
	defer func() { errors.Stdout = origStdout }()

	code := CmdDigest([]string{"-pack-dir", tmpDir, "-show-manifest"})

	if code != 0 {
		t.Errorf("Expected exit code 0, got %d", code)
	}

	var result map[string]any
	if err := json.Unmarshal(outBuf.Bytes(), &result); err != nil {
		t.Fatalf("Failed to parse JSON output: %v", err)
	}

	manifest, ok := result["manifest"].(map[string]any)
	if !ok {
		t.Fatalf("manifest not found or not map in output: %v", result)
	}

	files, ok := manifest["files"].([]any)
	if !ok || len(files) != 1 {
		t.Errorf("Expected 1 file in manifest, got %v", files)
	}

	t.Logf("✓ CmdDigest --show-manifest test passed")
}

// TestCmdDigest_InvalidPack verifies that CmdDigest fails if pack validation fails.
func TestCmdDigest_InvalidPack(t *testing.T) {
	tmpDir := t.TempDir()
	packJSON := `{"pack_id":"test-pack","namespace":"test","version":"1.0.0","definitions":[]}`
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte(packJSON), 0644); err != nil {
		t.Fatalf("Failed to write pack.json: %v", err)
	}

	errors.ExitFn = func(code int) { panic(code) }
	defer func() { errors.ExitFn = os.Exit }()

	errBuf := &bytes.Buffer{}
	origStderr := errors.Stderr
	errors.Stderr = errBuf
	defer func() { errors.Stderr = origStderr }()

	var exitCode int
	func() {
		defer func() {
			if r := recover(); r != nil {
				if c, ok := r.(int); ok {
					exitCode = c
				}
			}
		}()
		_ = CmdDigest([]string{"-pack-dir", tmpDir})
	}()

	if exitCode != 5 {
		t.Errorf("Expected exit code 5 (validation failed), got %d", exitCode)
	}

	if errBuf.Len() == 0 {
		t.Errorf("Expected error output to stderr, got empty")
	}

	t.Logf("✓ CmdDigest invalid pack test passed (exit %d)", exitCode)
}

// TestCmdDigest_Deterministic verifies that running CmdDigest twice produces identical output.
func TestCmdDigest_Deterministic(t *testing.T) {
	tmpDir := t.TempDir()
	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	packJSON := `{"pack_id":"test-pack","namespace":"test","version":"1.0.0","definitions":["definitions/test.json"]}`
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte(packJSON), 0644); err != nil {
		t.Fatalf("Failed to write pack.json: %v", err)
	}

	defContent := `{"id":"test","type":"assertion","name":"Test"}`
	if err := os.WriteFile(filepath.Join(defsDir, "test.json"), []byte(defContent), 0644); err != nil {
		t.Fatalf("Failed to write test.json: %v", err)
	}

	origStdout := errors.Stdout
	defer func() { errors.Stdout = origStdout }()

	outBuf1 := &bytes.Buffer{}
	errors.Stdout = outBuf1
	code1 := CmdDigest([]string{"-pack-dir", tmpDir})

	outBuf2 := &bytes.Buffer{}
	errors.Stdout = outBuf2
	code2 := CmdDigest([]string{"-pack-dir", tmpDir})

	if code1 != 0 || code2 != 0 {
		t.Errorf("Expected exit code 0 for both runs, got %d and %d", code1, code2)
	}

	if outBuf1.String() != outBuf2.String() {
		t.Errorf("Output differs between runs")
	}

	t.Logf("✓ CmdDigest deterministic test passed")
}

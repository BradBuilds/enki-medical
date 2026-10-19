package pack

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"gdu/internal/errors"
)

// TestCmdDigest_ShortFormat verifies that --digest-format short truncates to 12 chars
func TestCmdDigest_ShortFormat(t *testing.T) {
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

	// Test hex format (default, full length)
	outBufHex := &bytes.Buffer{}
	errors.Stdout = outBufHex
	codeHex := CmdDigest([]string{"-pack-dir", tmpDir, "-digest-format", "hex"})

	if codeHex != 0 {
		t.Errorf("Expected exit code 0 for hex format, got %d", codeHex)
	}

	var resultHex map[string]any
	if err := json.Unmarshal(outBufHex.Bytes(), &resultHex); err != nil {
		t.Fatalf("Failed to parse hex output: %v", err)
	}

	hexDigest, ok := resultHex["pack_digest"].(string)
	if !ok {
		t.Fatalf("pack_digest not found in hex output")
	}

	// Test short format (12 chars)
	outBufShort := &bytes.Buffer{}
	errors.Stdout = outBufShort
	codeShort := CmdDigest([]string{"-pack-dir", tmpDir, "-digest-format", "short"})

	if codeShort != 0 {
		t.Errorf("Expected exit code 0 for short format, got %d", codeShort)
	}

	var resultShort map[string]any
	if err := json.Unmarshal(outBufShort.Bytes(), &resultShort); err != nil {
		t.Fatalf("Failed to parse short output: %v", err)
	}

	shortDigest, ok := resultShort["pack_digest"].(string)
	if !ok {
		t.Fatalf("pack_digest not found in short output")
	}

	// Verify short format is prefix of hex format
	if !strings.HasPrefix(hexDigest, shortDigest) {
		t.Errorf("Short digest %s is not prefix of hex digest %s", shortDigest, hexDigest)
	}

	// Verify short format is exactly 19 chars ("sha256:" + 12 hex chars)
	expectedLen := len("sha256:") + 12
	if len(shortDigest) != expectedLen {
		t.Errorf("Short digest should be %d chars, got %d: %s", expectedLen, len(shortDigest), shortDigest)
	}

	t.Logf("✓ CmdDigest short format test passed")
	t.Logf("  Hex:   %s", hexDigest)
	t.Logf("  Short: %s", shortDigest)
}

// TestCmdDigest_TextOutput verifies that --text flag produces human-readable output
func TestCmdDigest_TextOutput(t *testing.T) {
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

	// Capture stdout (text mode writes directly to stdout, not via errors.Stdout)
	origStdout := os.Stdout
	r, w, _ := os.Pipe()
	os.Stdout = w

	code := CmdDigest([]string{"-pack-dir", tmpDir, "-text"})

	w.Close()
	os.Stdout = origStdout

	outBytes := make([]byte, 1024)
	n, _ := r.Read(outBytes)
	output := string(outBytes[:n])

	if code != 0 {
		t.Errorf("Expected exit code 0, got %d", code)
	}

	// Verify text output contains expected strings
	if !strings.Contains(output, "PACK_DIGEST: sha256:") {
		t.Errorf("Text output missing PACK_DIGEST line: %s", output)
	}

	if !strings.Contains(output, "Manifest version: 1") {
		t.Errorf("Text output missing manifest version line: %s", output)
	}

	if !strings.Contains(output, "Files: 1") {
		t.Errorf("Text output missing files count line: %s", output)
	}

	t.Logf("✓ CmdDigest text output test passed")
	t.Logf("  Output:\n%s", output)
}

// TestCmdDigest_InvalidDigestFormat verifies that invalid --digest-format values are rejected
func TestCmdDigest_InvalidDigestFormat(t *testing.T) {
	tmpDir := t.TempDir()

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
		_ = CmdDigest([]string{"-pack-dir", tmpDir, "-digest-format", "invalid"})
	}()

	if exitCode != 1 { // InvalidArgs = 1
		t.Errorf("Expected exit code 1 (invalid args), got %d", exitCode)
	}

	if errBuf.Len() == 0 {
		t.Errorf("Expected error output to stderr, got empty")
	}

	t.Logf("✓ CmdDigest invalid digest format test passed (exit %d)", exitCode)
}

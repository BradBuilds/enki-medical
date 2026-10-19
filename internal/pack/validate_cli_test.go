package pack

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"gdu/internal/errors"
)

// Helper to create a valid test pack
func makeValidPack(t *testing.T, tmpDir string) {
	pack := map[string]interface{}{
		"pack_id":   "test.valid",
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
}

// TestCmdValidate_SuccessGoesToStdout verifies that valid pack JSON goes to stdout with exit 0.
// This is the real stream contract test.
func TestCmdValidate_SuccessGoesToStdout(t *testing.T) {
	tmpDir := t.TempDir()
	makeValidPack(t, tmpDir)

	// Inject buffers to capture output
	var stdout, stderr bytes.Buffer
	origStdout := errors.Stdout
	origStderr := errors.Stderr
	origExit := errors.ExitFn
	errors.Stdout = &stdout
	errors.Stderr = &stderr
	errors.ExitFn = func(code int) {}

	t.Cleanup(func() {
		errors.Stdout = origStdout
		errors.Stderr = origStderr
		errors.ExitFn = origExit
	})

	// Run command
	code := CmdValidate([]string{"--pack-dir", tmpDir})

	// Verify exit code
	if code != int(errors.OK) {
		t.Errorf("Expected exit 0, got %d", code)
	}

	// Verify stdout has JSON
	if stdout.Len() == 0 {
		t.Fatal("Expected success JSON on stdout, but stdout is empty")
	}

	// Verify stderr is empty
	if stderr.Len() != 0 {
		t.Errorf("Expected empty stderr for success, got: %s", stderr.String())
	}

	// Verify stdout is valid JSON with status "valid"
	var result validateSuccess
	if err := json.Unmarshal(stdout.Bytes(), &result); err != nil {
		t.Errorf("Stdout is not valid JSON: %v", err)
	}

	if result.Status != "valid" {
		t.Errorf("Expected status='valid', got %q", result.Status)
	}

	t.Logf("✓ Success: status=valid sent to stdout, exit 0")
}

// TestCmdValidate_InvalidPackGoesToStderr verifies that invalid pack errors go to stderr with exit 5.
func TestCmdValidate_InvalidPackGoesToStderr(t *testing.T) {
	tmpDir := t.TempDir()

	// Create pack with missing definition
	pack := map[string]interface{}{
		"pack_id":   "test.missing",
		"version":   "1.0.0",
		"namespace": "test",
		"definitions": []string{
			"definitions/missing.json",
		},
	}
	packJSON, _ := json.MarshalIndent(pack, "", "  ")
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), packJSON, 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	defsDir := filepath.Join(tmpDir, "definitions")
	if err := os.Mkdir(defsDir, 0755); err != nil {
		t.Fatalf("Failed to create definitions dir: %v", err)
	}

	// Inject buffers
	var stdout, stderr bytes.Buffer
	origStdout := errors.Stdout
	origStderr := errors.Stderr
	origExit := errors.ExitFn
	errors.Stdout = &stdout
	errors.Stderr = &stderr
	errors.ExitFn = func(code int) {
		panic(code) // panic to stop execution (simulates os.Exit)
	}

	t.Cleanup(func() {
		errors.Stdout = origStdout
		errors.Stderr = origStderr
		errors.ExitFn = origExit
	})

	// Run command
	defer func() {
		if r := recover(); r != nil {
			// ExitFn was called (panic)
			code := r.(int)
			// Verify exit code is 5 (ValidationFailed)
			if code != int(errors.ValidationFailed) {
				t.Errorf("Expected exit 5, got %d", code)
			}

			// Verify stderr has JSON
			if stderr.Len() == 0 {
				t.Fatal("Expected error JSON on stderr, but stderr is empty")
			}

			// Verify stdout is empty
			if stdout.Len() != 0 {
				t.Errorf("Expected empty stdout for error, got: %s", stdout.String())
			}

			// Verify stderr contains error envelope with validation_failed type
			var errorEnv map[string]interface{}
			if err := json.Unmarshal(stderr.Bytes(), &errorEnv); err != nil {
				t.Errorf("Stderr is not valid JSON: %v", err)
			}

			if errorEnv["error_type"] != "validation_failed" {
				t.Errorf("Expected error_type='validation_failed', got %v", errorEnv["error_type"])
			}

			t.Logf("✓ Error: validation_failed sent to stderr, exit 5")
		}
	}()

	code := CmdValidate([]string{"--pack-dir", tmpDir})
	_ = code // code won't be reached if panic occurs
}

// TestCmdValidate_InvalidJSONGoesToStderr verifies that JSON parse errors go to stderr with exit 4.
func TestCmdValidate_InvalidJSONGoesToStderr(t *testing.T) {
	tmpDir := t.TempDir()

	// Create malformed pack.json
	if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte("{invalid"), 0644); err != nil {
		t.Fatalf("Failed to create pack.json: %v", err)
	}

	// Inject buffers
	var stdout, stderr bytes.Buffer
	origStdout := errors.Stdout
	origStderr := errors.Stderr
	origExit := errors.ExitFn
	errors.Stdout = &stdout
	errors.Stderr = &stderr
	errors.ExitFn = func(code int) {
		panic(code)
	}

	t.Cleanup(func() {
		errors.Stdout = origStdout
		errors.Stderr = origStderr
		errors.ExitFn = origExit
	})

	// Run command
	defer func() {
		if r := recover(); r != nil {
			code := r.(int)
			// Verify exit code is 4 (InvalidJSON)
			if code != int(errors.InvalidJSON) {
				t.Errorf("Expected exit 4, got %d", code)
			}

			// Verify stderr has JSON
			if stderr.Len() == 0 {
				t.Fatal("Expected error JSON on stderr, but stderr is empty")
			}

			// Verify stdout is empty
			if stdout.Len() != 0 {
				t.Errorf("Expected empty stdout for error, got: %s", stdout.String())
			}

			// Verify error type
			var errorEnv map[string]interface{}
			if err := json.Unmarshal(stderr.Bytes(), &errorEnv); err != nil {
				t.Errorf("Stderr is not valid JSON: %v", err)
			}

			if errorEnv["error_code"] != float64(errors.InvalidJSON) {
				t.Errorf("Expected error_code=4, got %v", errorEnv["error_code"])
			}

			t.Logf("✓ Error: invalid JSON sent to stderr, exit 4")
		}
	}()

	code := CmdValidate([]string{"--pack-dir", tmpDir})
	_ = code
}

// TestCmdValidate_InvalidArgsGoesToStderr verifies that invalid CLI args go to stderr with exit 1.
func TestCmdValidate_InvalidArgsGoesToStderr(t *testing.T) {
	// Inject buffers
	var stdout, stderr bytes.Buffer
	origStdout := errors.Stdout
	origStderr := errors.Stderr
	origExit := errors.ExitFn
	errors.Stdout = &stdout
	errors.Stderr = &stderr
	errors.ExitFn = func(code int) {
		panic(code)
	}

	t.Cleanup(func() {
		errors.Stdout = origStdout
		errors.Stderr = origStderr
		errors.ExitFn = origExit
	})

	// Run command with bad flag
	defer func() {
		if r := recover(); r != nil {
			code := r.(int)
			// Verify exit code is 1 (InvalidArgs)
			if code != int(errors.InvalidArgs) {
				t.Errorf("Expected exit 1, got %d", code)
			}

			// Verify error on stderr
			if stderr.Len() == 0 {
				t.Fatal("Expected error JSON on stderr")
			}

			if stdout.Len() != 0 {
				t.Errorf("Expected empty stdout for invalid args")
			}

			t.Logf("✓ Error: invalid args sent to stderr, exit 1")
		}
	}()

	code := CmdValidate([]string{"--invalid-flag"})
	_ = code
}

// TestStreamContract_AllErrorsGoToStderr is a meta-test that documents the contract.
func TestStreamContract_AllErrorsGoToStderr(t *testing.T) {
	tests := []struct {
		name         string
		setupFunc    func(tmpDir string) error
		expectedCode errors.ExitCode
	}{
		{
			name: "ValidationFailed",
			setupFunc: func(tmpDir string) error {
				pack := map[string]interface{}{
					"pack_id":   "test.err",
					"version":   "1.0.0",
					"namespace": "test",
					"definitions": []string{
						"definitions/missing.json",
					},
				}
				packJSON, _ := json.MarshalIndent(pack, "", "  ")
				if err := os.WriteFile(filepath.Join(tmpDir, "pack.json"), packJSON, 0644); err != nil {
					return err
				}
				return os.Mkdir(filepath.Join(tmpDir, "definitions"), 0755)
			},
			expectedCode: errors.ValidationFailed,
		},
		{
			name: "InvalidJSON",
			setupFunc: func(tmpDir string) error {
				return os.WriteFile(filepath.Join(tmpDir, "pack.json"), []byte("{bad}"), 0644)
			},
			expectedCode: errors.InvalidJSON,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tmpDir := t.TempDir()
			if err := tt.setupFunc(tmpDir); err != nil {
				t.Fatalf("Setup failed: %v", err)
			}

			var stdout, stderr bytes.Buffer
			origStdout := errors.Stdout
			origStderr := errors.Stderr
			origExit := errors.ExitFn
			errors.Stdout = &stdout
			errors.Stderr = &stderr
			errors.ExitFn = func(code int) {
				panic(code)
			}

			defer func() {
				errors.Stdout = origStdout
				errors.Stderr = origStderr
				errors.ExitFn = origExit
				
				if r := recover(); r != nil {
					code := r.(int)
					// Core contract: all errors go to stderr, nothing on stdout
					if stdout.Len() != 0 {
						t.Errorf("%s: expected empty stdout, got: %s", tt.name, stdout.String())
					}

					if stderr.Len() == 0 {
						t.Errorf("%s: expected error JSON on stderr, but stderr is empty", tt.name)
					}

					// Verify stderr is valid JSON
					var errorEnv map[string]interface{}
					if err := json.Unmarshal(stderr.Bytes(), &errorEnv); err != nil {
						t.Errorf("%s: stderr is not valid JSON: %v", tt.name, err)
					}

					t.Logf("✓ %s: error correctly sent to stderr, exit %d", tt.name, code)
				}
			}()

			CmdValidate([]string{"--pack-dir", tmpDir})
		})
	}
}


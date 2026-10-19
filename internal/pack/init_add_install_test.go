package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"gdu/internal/errors"
)

func TestInitBasic(t *testing.T) {
	tmpDir := t.TempDir()
	outDir := filepath.Join(tmpDir, "test-pack")

	code := CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--namespace", "test",
		"--author", "Test Author",
		"--output", outDir,
	})

	if code != 0 {
		t.Fatalf("CmdInit failed with code %d", code)
	}

	// Verify pack.json was created
	packJSONPath := filepath.Join(outDir, "pack.json")
	if _, err := os.Stat(packJSONPath); err != nil {
		t.Fatalf("pack.json not created: %v", err)
	}

	// Verify definitions/ directory was created
	defsDir := filepath.Join(outDir, "definitions")
	if _, err := os.Stat(defsDir); err != nil {
		t.Fatalf("definitions/ not created: %v", err)
	}

	// Verify pack.json content
	packBytes, err := os.ReadFile(packJSONPath)
	if err != nil {
		t.Fatalf("Failed to read pack.json: %v", err)
	}

	var pack map[string]any
	if err := json.Unmarshal(packBytes, &pack); err != nil {
		t.Fatalf("pack.json is not valid JSON: %v", err)
	}

	if pack["pack_id"] != "test-pack" {
		t.Errorf("pack_id mismatch: got %v, want test-pack", pack["pack_id"])
	}

	if pack["version"] != "1.0.0" {
		t.Errorf("version mismatch: got %v, want 1.0.0", pack["version"])
	}

	if pack["namespace"] != "test" {
		t.Errorf("namespace mismatch: got %v, want test", pack["namespace"])
	}

	if pack["author"] != "Test Author" {
		t.Errorf("author mismatch: got %v, want Test Author", pack["author"])
	}

	// Verify definitions is an empty array
	defs, ok := pack["definitions"].([]any)
	if !ok || len(defs) != 0 {
		t.Errorf("definitions should be empty array, got %v", pack["definitions"])
	}
}

func TestInitWithForce(t *testing.T) {
	tmpDir := t.TempDir()
	outDir := filepath.Join(tmpDir, "test-pack")

	// First init
	code := CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--output", outDir,
	})
	if code != 0 {
		t.Fatalf("First CmdInit failed with code %d", code)
	}

	// Second init with --force should succeed
	code = CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "2.0.0",
		"--output", outDir,
		"--force",
	})
	if code != 0 {
		t.Fatalf("CmdInit with --force failed with code %d", code)
	}

	// Verify version was updated
	packBytes, err := os.ReadFile(filepath.Join(outDir, "pack.json"))
	if err != nil {
		t.Fatalf("Failed to read pack.json: %v", err)
	}

	var pack map[string]any
	json.Unmarshal(packBytes, &pack)

	if pack["version"] != "2.0.0" {
		t.Errorf("version not updated: got %v, want 2.0.0", pack["version"])
	}
}

func TestAddDefinitions(t *testing.T) {
	tmpDir := t.TempDir()
	packDir := filepath.Join(tmpDir, "test-pack")

	// Init pack
	CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--output", packDir,
	})

	// Create source JSON files
	srcDir := filepath.Join(tmpDir, "src")
	os.MkdirAll(srcDir, 0755)

	def1 := `{"id":"system","name":"System Definition"}`
	def2 := `{"id":"digits","name":"Digit Definitions"}`

	file1 := filepath.Join(srcDir, "system.json")
	file2 := filepath.Join(srcDir, "digits.json")

	if err := os.WriteFile(file1, []byte(def1), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	if err := os.WriteFile(file2, []byte(def2), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	// Add files to pack (pass both files as separate args, with --pack-dir before)
	code := CmdAdd([]string{
		"--pack-dir", packDir,
		"--base", srcDir,
		file1,
	})

	if code != 0 {
		t.Fatalf("CmdAdd file1 failed with code %d", code)
	}

	code = CmdAdd([]string{
		"--pack-dir", packDir,
		"--base", srcDir,
		file2,
	})

	if code != 0 {
		t.Fatalf("CmdAdd file2 failed with code %d", code)
	}

	// Verify files were copied to definitions/
	if _, err := os.Stat(filepath.Join(packDir, "definitions", "system.json")); err != nil {
		t.Fatalf("system.json not copied: %v", err)
	}

	if _, err := os.Stat(filepath.Join(packDir, "definitions", "digits.json")); err != nil {
		t.Fatalf("digits.json not copied: %v", err)
	}

	// Verify pack.json was updated
	packBytes, err := os.ReadFile(filepath.Join(packDir, "pack.json"))
	if err != nil {
		t.Fatalf("Failed to read pack.json: %v", err)
	}

	var pack map[string]any
	json.Unmarshal(packBytes, &pack)

	defs := pack["definitions"].([]any)
	if len(defs) != 2 {
		t.Errorf("Expected 2 definitions, got %d", len(defs))
	}
}

func TestInstallBasic(t *testing.T) {
	tmpDir := t.TempDir()
	packDir := filepath.Join(tmpDir, "test-pack")
	registry := filepath.Join(tmpDir, "registry")

	// Init pack
	CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--output", packDir,
	})

	// Add a definition
	defPath := filepath.Join(packDir, "definitions", "test.json")
	if err := os.WriteFile(defPath, []byte(`{"id":"test"}`), 0644); err != nil {
		t.Fatalf("Failed to create definition: %v", err)
	}

	// Update pack.json to include definition
	packBytes, _ := os.ReadFile(filepath.Join(packDir, "pack.json"))
	var pack map[string]any
	json.Unmarshal(packBytes, &pack)
	pack["definitions"] = []string{"definitions/test.json"}
	updatedBytes, _ := json.MarshalIndent(pack, "", "  ")
	os.WriteFile(filepath.Join(packDir, "pack.json"), append(updatedBytes, '\n'), 0644)

	// Install pack
	code := CmdInstall([]string{
		"--pack-dir", packDir,
		"--registry", registry,
	})

	if code != 0 {
		t.Fatalf("CmdInstall failed with code %d", code)
	}

	// Verify installation directory structure exists
	packsDirs, err := os.ReadDir(filepath.Join(registry, "packs"))
	if err != nil {
		t.Fatalf("Failed to read packs directory: %v", err)
	}

	if len(packsDirs) == 0 {
		t.Fatalf("No pack installed")
	}

	installedDir := filepath.Join(registry, "packs", packsDirs[0].Name())

	// Verify pack.json exists in installed location
	if _, err := os.Stat(filepath.Join(installedDir, "pack.json")); err != nil {
		t.Fatalf("pack.json not installed: %v", err)
	}

	// Verify definitions/ directory exists
	if _, err := os.Stat(filepath.Join(installedDir, "definitions")); err != nil {
		t.Fatalf("definitions/ not installed: %v", err)
	}

	// Verify definition file was copied
	if _, err := os.Stat(filepath.Join(installedDir, "definitions", "test.json")); err != nil {
		t.Fatalf("test.json not installed: %v", err)
	}
}

func TestVolatileFieldRejection(t *testing.T) {
	tmpDir := t.TempDir()
	packDir := filepath.Join(tmpDir, "test-pack")

	// Init pack
	CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--output", packDir,
	})

	// Create a file with a volatile field
	srcDir := filepath.Join(tmpDir, "src")
	os.MkdirAll(srcDir, 0755)

	volatileDef := `{"id":"test","created_at":"2026-01-12T00:00:00Z"}`
	badFile := filepath.Join(srcDir, "bad.json")
	if err := os.WriteFile(badFile, []byte(volatileDef), 0644); err != nil {
		t.Fatalf("Failed to create test file: %v", err)
	}

	// Capture exit code
	origExit := errors.ExitFn
	var capturedCode int
	errors.ExitFn = func(code int) {
		capturedCode = code
		panic("exit")
	}
	defer func() {
		errors.ExitFn = origExit
	}()

	// Try to add file with volatile field (should fail with exit code 3)
	func() {
		defer func() {
			if r := recover(); r == nil {
				t.Fatalf("Expected panic from ExitFn")
			}
		}()

		CmdAdd([]string{
			"--pack-dir", packDir,
			badFile,
		})
	}()

	if capturedCode != 3 {
		t.Fatalf("CmdAdd should have failed with code 3 (volatile), got %d", capturedCode)
	}
}

func TestAddIdempotent(t *testing.T) {
	tmpDir := t.TempDir()
	packDir := filepath.Join(tmpDir, "test-pack")

	// Init pack
	CmdInit([]string{
		"--pack-id", "test-pack",
		"--version", "1.0.0",
		"--output", packDir,
	})

	// Create source file
	srcDir := filepath.Join(tmpDir, "src")
	os.MkdirAll(srcDir, 0755)
	defPath := filepath.Join(srcDir, "test.json")
	defContent := `{"id":"test"}`
	os.WriteFile(defPath, []byte(defContent), 0644)

	// Add file first time (with --base to establish proper path mapping)
	code1 := CmdAdd([]string{
		"--pack-dir", packDir,
		"--base", srcDir,
		defPath,
	})
	if code1 != 0 {
		t.Fatalf("First CmdAdd failed with code %d", code1)
	}

	// Add same file again (should be idempotent)
	code2 := CmdAdd([]string{
		"--pack-dir", packDir,
		"--base", srcDir,
		defPath,
	})
	if code2 != 0 {
		t.Fatalf("Second CmdAdd failed with code %d", code2)
	}

	// Verify only one copy exists and pack.json has one entry
	packBytes, _ := os.ReadFile(filepath.Join(packDir, "pack.json"))
	var pack map[string]any
	json.Unmarshal(packBytes, &pack)

	defs := pack["definitions"].([]any)
	if len(defs) != 1 {
		t.Errorf("Expected 1 definition after idempotent add, got %d", len(defs))
	}
}

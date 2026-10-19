package paths

import (
	"testing"
	"unicode/utf8"

	"golang.org/x/text/unicode/norm"
)

// TestNFCNormalization verifies that paths must be NFC-normalized.
func TestNFCNormalization(t *testing.T) {
	tests := []struct {
		name     string
		input    string
		shouldBe string // what it should be after NFC normalization
	}{
		{
			name:     "ASCII path unchanged",
			input:    "definitions/foo.json",
			shouldBe: "definitions/foo.json",
		},
		{
			name:     "Already NFC (combined form)",
			input:    "definitions/café.json", // é as U+00E9 (single codepoint)
			shouldBe: "definitions/café.json",
		},
		{
			name:     "Decomposed form (NFD) converts to NFC",
			input:    "definitions/cafe\u0301.json", // e + combining acute (NFD)
			shouldBe: "definitions/café.json",         // should become NFC (é)
		},
		{
			name:     "Multiple decomposed forms",
			input:    "definitions/a\u0300a\u0301a\u0302.json", // à á â (decomposed)
			shouldBe: "definitions/àáâ.json",                    // NFC forms
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// NFC normalize the input
			nfc := norm.NFC.String(tt.input)
			if nfc != tt.shouldBe {
				t.Errorf("NFC normalization failed: input %q should normalize to %q, got %q",
					tt.input, tt.shouldBe, nfc)
			}

			// Verify that NormalizePath rejects non-NFC
			if nfc != tt.input {
				// This input is NOT NFC
				result, err := NormalizePath("", tt.input)
				if err == nil {
					t.Errorf("NormalizePath should reject non-NFC path %q, but accepted it with result %q",
						tt.input, result.Clean)
				}
			} else {
				// This input IS NFC; should pass
				result, err := NormalizePath("", tt.input)
				if err != nil {
					t.Errorf("NormalizePath should accept NFC path %q, but rejected with error: %v",
						tt.input, err)
				}
				if result.Clean != tt.shouldBe {
					t.Errorf("NormalizePath result mismatch: expected %q, got %q",
						tt.shouldBe, result.Clean)
				}
			}
		})
	}
}

// TestToNFC verifies the ToNFC helper produces correct NFC normalization.
func TestToNFC(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"cafe\u0301", "café"},     // decomposed é → combined é
		{"\u0041\u0300", "À"},      // A + combining grave → À
		{"\u006f\u0301", "ó"},      // o + combining acute → ó
	}

	for _, tt := range tests {
		result := ToNFC(tt.input)
		if result != tt.expected {
			t.Errorf("ToNFC(%q) = %q, expected %q", tt.input, result, tt.expected)
		}
	}
}

// TestNormalizePath_Rejection verifies fail-closed behavior on invalid paths.
func TestNormalizePath_Rejection(t *testing.T) {
	tests := []struct {
		name        string
		input       string
		expectError bool
	}{
		{
			name:        "Absolute path rejection",
			input:       "/absolute/path.json",
			expectError: true,
		},
		{
			name:        "DotDot rejection",
			input:       "definitions/../escape.json",
			expectError: true,
		},
		{
			name:        "Windows drive prefix rejection (C:)",
			input:       "C:\\definitions\\file.json",
			expectError: true,
		},
		{
			name:        "UNC prefix rejection",
			input:       "\\\\?\\definitions\\file.json",
			expectError: true,
		},
		{
			name:        "Valid relative path",
			input:       "definitions/my_file.json",
			expectError: false,
		},
		{
			name:        "Valid nested path",
			input:       "definitions/sub/dir/file.json",
			expectError: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := NormalizePath("", tt.input)
			if tt.expectError {
				if err == nil {
					t.Errorf("NormalizePath should reject %q, but accepted it", tt.input)
				}
			} else {
				if err != nil {
					t.Errorf("NormalizePath should accept %q, but rejected with: %v", tt.input, err)
				}
				if result.Clean == "" && tt.input != "." {
					t.Errorf("NormalizePath result.Clean is empty for valid input %q", tt.input)
				}
			}
		})
	}
}

// TestNormalizePath_UTF8Validity ensures all normalized paths are valid UTF-8.
func TestNormalizePath_UTF8Validity(t *testing.T) {
	tests := []string{
		"definitions/café.json",
		"definitions/αβγ.json",
		"definitions/日本語.json",
		"definitions/emoji_🌍.json",
	}

	for _, input := range tests {
		result, err := NormalizePath("", input)
		if err != nil {
			t.Logf("Skipping %q (rejected): %v", input, err)
			continue
		}
		if !utf8.ValidString(result.Clean) {
			t.Errorf("NormalizePath result for %q is not valid UTF-8: %q", input, result.Clean)
		}
	}
}

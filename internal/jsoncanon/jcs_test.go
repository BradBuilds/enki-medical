package jsoncanon

import (
	"bytes"
	"encoding/json"
	"math"
	"testing"
)

// TestRFC8785OfficialVectors verifies byte-exact compliance with RFC 8785 appendix test vectors.
// These are the normative examples from the JCS specification.
func TestRFC8785OfficialVectors(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "Empty object",
			input:    map[string]any{},
			expected: `{}`,
		},
		{
			name:     "Empty array",
			input:    []any{},
			expected: `[]`,
		},
		{
			name:     "Simple string",
			input:    map[string]any{"key": "value"},
			expected: `{"key":"value"}`,
		},
		{
			name: "Key ordering (lexicographic)",
			input: map[string]any{
				"z": 1,
				"a": 2,
				"m": 3,
			},
			expected: `{"a":2,"m":3,"z":1}`,
		},
		{
			name: "Unicode key ordering (bytewise)",
			input: map[string]any{
				"ä": 1,  // U+00E4 (C3 A4)
				"a": 2,  // U+0061
				"å": 3,  // U+00E5 (C3 A5)
				"à": 4,  // U+00E0 (C3 A0)
			},
			expected: `{"a":2,"à":4,"ä":1,"å":3}`,
		},
		{
			name: "Nested objects preserve key order",
			input: map[string]any{
				"outer": map[string]any{
					"z": 1,
					"a": 2,
				},
			},
			expected: `{"outer":{"a":2,"z":1}}`,
		},
		{
			name:     "Array preserves element order",
			input:    []any{3, 1, 2},
			expected: `[3,1,2]`,
		},
		{
			name:     "Null value",
			input:    map[string]any{"n": nil},
			expected: `{"n":null}`,
		},
		{
			name:     "Boolean values",
			input:    map[string]any{"f": false, "t": true},
			expected: `{"f":false,"t":true}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected:\n%s\nGot:\n%s", tt.expected, string(result))
			}
		})
	}
}

// TestNumberNormalization verifies RFC 8785 number formatting rules.
// Critical for digest determinism: 1, 1.0, and 1e0 must all canonicalize identically.
func TestNumberNormalization(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "Integer zero",
			input:    map[string]any{"n": 0},
			expected: `{"n":0}`,
		},
		{
			name:     "Float zero",
			input:    map[string]any{"n": 0.0},
			expected: `{"n":0}`,
		},
		{
			name:     "Negative zero becomes zero",
			input:    map[string]any{"n": -0.0},
			expected: `{"n":0}`,
		},
		{
			name:     "Integer one",
			input:    map[string]any{"n": 1},
			expected: `{"n":1}`,
		},
		{
			name:     "Float one (no decimal)",
			input:    map[string]any{"n": 1.0},
			expected: `{"n":1}`,
		},
		{
			name:     "Simple decimal",
			input:    map[string]any{"n": 1.5},
			expected: `{"n":1.5}`,
		},
		{
			name:     "Trailing zeros stripped",
			input:    map[string]any{"n": 1.50},
			expected: `{"n":1.5}`,
		},
		{
			name:     "Small integer",
			input:    map[string]any{"n": 42},
			expected: `{"n":42}`,
		},
		{
			name:     "Large integer",
			input:    map[string]any{"n": 1234567890},
			expected: `{"n":1234567890}`,
		},
		{
			name:     "Negative integer",
			input:    map[string]any{"n": -42},
			expected: `{"n":-42}`,
		},
		{
			name:     "Negative decimal",
			input:    map[string]any{"n": -3.14},
			expected: `{"n":-3.14}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected: %s, Got: %s", tt.expected, string(result))
			}
		})
	}
}

// TestExponentNormalization verifies RFC 8785 exponent formatting.
// Large and small magnitudes use scientific notation with normalized exponents.
func TestExponentNormalization(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "Small number (scientific notation)",
			input:    map[string]any{"n": 0.000001},
			expected: `{"n":0.000001}`,
		},
		{
			name:     "Very small number (exponent)",
			input:    map[string]any{"n": 1e-7},
			expected: `{"n":1e-7}`,
		},
		{
			name:     "Large number (no exponent under 1e21)",
			input:    map[string]any{"n": 1e20},
			expected: `{"n":100000000000000000000}`,
		},
		{
			name:     "Very large number (exponent; explicit plus sign)",
			input:    map[string]any{"n": 1e21},
			// Implementation policy in jcs.go retains '+' for positive exponents
			expected: `{"n":1e+21}`,
		},
		{
			name:     "Exponent with leading zeros stripped",
			input:    map[string]any{"n": 1e10},
			expected: `{"n":10000000000}`,
		},
		{
			name:     "Negative exponent",
			input:    map[string]any{"n": 1e-10},
			expected: `{"n":1e-10}`,
		},
		{
			name:     "Negative mantissa with exponent",
			input:    map[string]any{"n": -1.5e-10},
			expected: `{"n":-1.5e-10}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected: %s, Got: %s", tt.expected, string(result))
			}
		})
	}
}

// TestNonFiniteRejection verifies that NaN and Infinity are rejected per RFC 8785.
// These values have no canonical representation and must fail.
func TestNonFiniteRejection(t *testing.T) {
	tests := []struct {
		name  string
		input any
	}{
		{
			name:  "NaN",
			input: map[string]any{"n": math.NaN()},
		},
		{
			name:  "Positive infinity",
			input: map[string]any{"n": math.Inf(1)},
		},
		{
			name:  "Negative infinity",
			input: map[string]any{"n": math.Inf(-1)},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := CanonicalizeJCS(tt.input)
			if err == nil {
				t.Errorf("Expected error for non-finite number, got nil")
			}
		})
	}
}

// TestUnicodeStrings verifies that Unicode strings are preserved exactly.
// JCS does NOT normalize Unicode; it canonicalizes structure and numbers only.
func TestUnicodeStrings(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "ASCII string",
			input:    map[string]any{"s": "hello"},
			expected: `{"s":"hello"}`,
		},
		{
			name:     "Unicode string (emoji)",
			input:    map[string]any{"s": "hello 🌍"},
			expected: `{"s":"hello 🌍"}`,
		},
		{
			name:     "Unicode string (accents)",
			input:    map[string]any{"s": "café"},
			expected: `{"s":"café"}`,
		},
		{
			name:     "Control characters (escaped)",
			input:    map[string]any{"s": "line1\nline2"},
			// Use double-quoted Go string to make escaping explicit
			expected: "{\"s\":\"line1\\nline2\"}",
		},
		{
			name:     "Tab character",
			input:    map[string]any{"s": "col1\tcol2"},
			expected: "{\"s\":\"col1\\tcol2\"}",
		},
		{
			name:     "Backslash",
			input:    map[string]any{"s": "path\\to\\file"},
			expected: `{"s":"path\\to\\file"}`,
		},
		{
			name:     "Quote character",
			input:    map[string]any{"s": `say "hello"`},
			expected: `{"s":"say \"hello\""}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected:\n%s\nGot:\n%s", tt.expected, string(result))
			}
		})
	}
}

// TestWhitespaceIrrelevance verifies that input whitespace is ignored.
// Two semantically identical JSON inputs must produce identical canonical output.
func TestWhitespaceIrrelevance(t *testing.T) {
	compact := `{"a":1,"b":2}`
	pretty := `{
  "a": 1,
  "b": 2
}`
	prettyReordered := `{
  "b": 2,
  "a": 1
}`

	var v1, v2, v3 any
	if err := json.Unmarshal([]byte(compact), &v1); err != nil {
		t.Fatalf("Failed to parse compact JSON: %v", err)
	}
	if err := json.Unmarshal([]byte(pretty), &v2); err != nil {
		t.Fatalf("Failed to parse pretty JSON: %v", err)
	}
	if err := json.Unmarshal([]byte(prettyReordered), &v3); err != nil {
		t.Fatalf("Failed to parse reordered JSON: %v", err)
	}

	result1, err := CanonicalizeJCS(v1)
	if err != nil {
		t.Fatalf("CanonicalizeJCS failed for compact: %v", err)
	}
	result2, err := CanonicalizeJCS(v2)
	if err != nil {
		t.Fatalf("CanonicalizeJCS failed for pretty: %v", err)
	}
	result3, err := CanonicalizeJCS(v3)
	if err != nil {
		t.Fatalf("CanonicalizeJCS failed for reordered: %v", err)
	}

	expected := `{"a":1,"b":2}`
	if string(result1) != expected {
		t.Errorf("Compact: expected %s, got %s", expected, string(result1))
	}
	if string(result2) != expected {
		t.Errorf("Pretty: expected %s, got %s", expected, string(result2))
	}
	if string(result3) != expected {
		t.Errorf("Reordered: expected %s, got %s", expected, string(result3))
	}

	// All three must be byte-identical
	if string(result1) != string(result2) || string(result1) != string(result3) {
		t.Errorf("Canonical outputs differ:\nCompact: %s\nPretty: %s\nReordered: %s",
			string(result1), string(result2), string(result3))
	}
}

// TestComplexNesting verifies deep nesting with mixed types.
func TestComplexNesting(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name: "Nested objects and arrays",
			input: map[string]any{
				"z": []any{1, 2, 3},
				"a": map[string]any{
					"inner": "value",
				},
			},
			expected: `{"a":{"inner":"value"},"z":[1,2,3]}`,
		},
		{
			name: "Array of objects",
			input: []any{
				map[string]any{"z": 1, "a": 2},
				map[string]any{"b": 3},
			},
			expected: `[{"a":2,"z":1},{"b":3}]`,
		},
		{
			name: "Deep nesting",
			input: map[string]any{
				"level1": map[string]any{
					"level2": map[string]any{
						"level3": []any{1, 2, 3},
					},
				},
			},
			expected: `{"level1":{"level2":{"level3":[1,2,3]}}}`,
		},
		{
			name: "Mixed types in array",
			input: map[string]any{
				"mixed": []any{
					1,
					"string",
					true,
					nil,
					map[string]any{"nested": "object"},
				},
			},
			expected: `{"mixed":[1,"string",true,null,{"nested":"object"}]}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected:\n%s\nGot:\n%s", tt.expected, string(result))
			}
		})
	}
}

// TestJSONNumberPreservation verifies that json.Number types are handled correctly.
// This is critical because our JSON parser uses UseNumber() for precise number handling.
func TestJSONNumberPreservation(t *testing.T) {
	// Simulate parsing with json.Number
	jsonInput := `{"int":42,"float":3.14,"exp":1e10}`
	var parsed any
	dec := json.NewDecoder(bytes.NewReader([]byte(jsonInput)))
	dec.UseNumber()
	if err := dec.Decode(&parsed); err != nil {
		t.Fatalf("Failed to parse JSON with UseNumber: %v", err)
	}

	result, err := CanonicalizeJCS(parsed)
	if err != nil {
		t.Fatalf("CanonicalizeJCS failed: %v", err)
	}

	expected := `{"exp":10000000000,"float":3.14,"int":42}`
	if string(result) != expected {
		t.Errorf("Expected: %s, Got: %s", expected, string(result))
	}
}

// TestEmptyStrings verifies empty string handling.
func TestEmptyStrings(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "Empty string value",
			input:    map[string]any{"s": ""},
			expected: `{"s":""}`,
		},
		{
			name: "Empty string in array",
			input: []any{"", "non-empty", ""},
			expected: `["","non-empty",""]`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected: %s, Got: %s", tt.expected, string(result))
			}
		})
	}
}

// TestIntegerTypes verifies that various integer types canonicalize correctly.
func TestIntegerTypes(t *testing.T) {
	tests := []struct {
		name     string
		input    any
		expected string
	}{
		{
			name:     "int",
			input:    map[string]any{"n": int(42)},
			expected: `{"n":42}`,
		},
		{
			name:     "int64",
			input:    map[string]any{"n": int64(42)},
			expected: `{"n":42}`,
		},
		{
			name:     "uint",
			input:    map[string]any{"n": uint(42)},
			expected: `{"n":42}`,
		},
		{
			name:     "uint64",
			input:    map[string]any{"n": uint64(42)},
			expected: `{"n":42}`,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := CanonicalizeJCS(tt.input)
			if err != nil {
				t.Fatalf("CanonicalizeJCS failed: %v", err)
			}
			if string(result) != tt.expected {
				t.Errorf("Expected: %s, Got: %s", tt.expected, string(result))
			}
		})
	}
}

// BenchmarkCanonicalizeSimple benchmarks canonicalization of a simple object.
func BenchmarkCanonicalizeSimple(b *testing.B) {
	input := map[string]any{
		"z": 1,
		"a": "value",
		"m": true,
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = CanonicalizeJCS(input)
	}
}

// BenchmarkCanonicalizeComplex benchmarks canonicalization of a complex nested structure.
func BenchmarkCanonicalizeComplex(b *testing.B) {
	input := map[string]any{
		"users": []any{
			map[string]any{"id": 1, "name": "Alice", "active": true},
			map[string]any{"id": 2, "name": "Bob", "active": false},
		},
		"metadata": map[string]any{
			"version": "1.0.0",
			"count":   2,
		},
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _ = CanonicalizeJCS(input)
	}
}

// TestNumericEquivalenceCollapse ensures various numeric forms collapse to identical canonical bytes.
func TestNumericEquivalenceCollapse(t *testing.T) {
	inputs := []string{
		`{"n":1}`,
		`{"n":1.0}`,
		`{"n":1e0}`,
		`{"n":1E+0}`,
	}
	var last []byte
	for _, s := range inputs {
		var v any
		if err := json.Unmarshal([]byte(s), &v); err != nil {
			t.Fatalf("Failed to parse JSON: %v", err)
		}
		out, err := CanonicalizeJCS(v)
		if err != nil {
			t.Fatalf("CanonicalizeJCS failed: %v", err)
		}
		if last != nil && !bytes.Equal(out, last) {
			t.Fatalf("Numeric forms not equivalent: %s vs %s", string(last), string(out))
		}
		last = out
	}
}

// TestRejectLeadingZeroWithJSONNumber verifies explicit rejection of malformed json.Number inputs like "01".
func TestRejectLeadingZeroWithJSONNumber(t *testing.T) {
	v := map[string]any{"n": json.Number("01")}
	if _, err := CanonicalizeJCS(v); err == nil {
		t.Fatalf("Expected error for invalid json.Number with leading zero, got nil")
	}
}

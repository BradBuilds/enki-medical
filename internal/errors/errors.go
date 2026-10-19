package errors

import (
    "encoding/json"
    "fmt"
	"io"
	"os"
)

// Injected dependencies for testability (can be overridden in tests)
var Stdout io.Writer = os.Stdout
var Stderr io.Writer = os.Stderr
var ExitFn = os.Exit

type ExitCode int

const (
	OK                ExitCode = 0
	InvalidArgs       ExitCode = 1
	DirConflict       ExitCode = 2
	VolatileDetected  ExitCode = 3
	InvalidJSON       ExitCode = 4
	ValidationFailed  ExitCode = 5
	DigestFailed      ExitCode = 6
	InstallFailed     ExitCode = 7
	VerificationFailed ExitCode = 8
)

type CliError struct {
    Code    ExitCode `json:"error_code"`
    Type    string   `json:"error_type"`
    Message string   `json:"message"`
    Details any      `json:"details,omitempty"`
    Help    string   `json:"help,omitempty"`
}

type ErrorEnvelope struct {
    Status string `json:"status"`
    CliError
}

// ExitJSON writes error JSON to stderr (per spec: "Errors: always JSON to stderr")
// and calls ExitFn with the specified code. This is fail-closed: even marshal failures
// are reported to stderr before exit.
func ExitJSON(e CliError) {
	env := ErrorEnvelope{Status: "error", CliError: e}
	b, _ := json.Marshal(env)
	if len(b) == 0 {
		_, _ = fmt.Fprintln(Stderr, `{"status":"error","error_code":6,"error_type":"internal_error","message":"failed to encode error"}`)
		ExitFn(int(DigestFailed))
	}
	_, _ = Stderr.Write(append(b, '\n'))
	ExitFn(int(e.Code))
}

// PrintJSON writes success JSON to stdout (per spec: default JSON output).
// Marshal failures are treated as fatal errors and exit via ExitJSON (stderr).
func PrintJSON(v any) {
	b, err := json.Marshal(v)
	if err != nil {
		ExitJSON(CliError{
			Code:    DigestFailed,
			Type:    "json_output_failed",
			Message: "Failed to encode JSON output",
			Details: map[string]any{"error": err.Error()},
		})
	}
	_, _ = Stdout.Write(append(b, '\n'))
}

package jsoncanon

import (
    "bytes"
    "encoding/json"
    "errors"
    "math"
    "regexp"
    "sort"
    "strconv"
    "strings"
)

// CanonicalizeJCS produces RFC 8785 canonical JSON bytes for the given value.
// It avoids whitespace, orders object keys lexicographically, and normalizes
// number formatting per the spec. Non-finite numbers are rejected.
func CanonicalizeJCS(v any) ([]byte, error) {
    var buf bytes.Buffer
    enc := encoder{buf: &buf}
    if err := enc.encode(v); err != nil {
        return nil, err
    }
    return buf.Bytes(), nil
}

type encoder struct {
    buf *bytes.Buffer
}

func (e *encoder) encode(v any) error {
    switch t := v.(type) {
    case nil:
        e.buf.WriteString("null")
    case bool:
        if t {
            e.buf.WriteString("true")
        } else {
            e.buf.WriteString("false")
        }
    case string:
        e.buf.WriteString(strconv.Quote(t))
    case json.Number:
        // Validate original numeric string against JSON number grammar before parsing
        // Grammar: -?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?
        numStr := string(t)
        if !isValidJSONNumberString(numStr) {
            return errors.New("invalid_json_number_format")
        }
        s, err := formatNumberString(numStr)
        if err != nil {
            return err
        }
        e.buf.WriteString(s)
    case float64:
        s, err := formatFloat(t)
        if err != nil {
            return err
        }
        e.buf.WriteString(s)
    case float32:
        s, err := formatFloat(float64(t))
        if err != nil {
            return err
        }
        e.buf.WriteString(s)
    case int, int8, int16, int32, int64:
        e.buf.WriteString(strconv.FormatInt(reflectToInt64(t), 10))
    case uint, uint8, uint16, uint32, uint64, uintptr:
        e.buf.WriteString(strconv.FormatUint(reflectToUint64(t), 10))
    case []interface{}:
        e.buf.WriteByte('[')
        for i, item := range t {
            if i > 0 {
                e.buf.WriteByte(',')
            }
            if err := e.encode(item); err != nil {
                return err
            }
        }
        e.buf.WriteByte(']')
    case map[string]interface{}:
        keys := make([]string, 0, len(t))
        for k := range t {
            keys = append(keys, k)
        }
        sort.Strings(keys)
        e.buf.WriteByte('{')
        for i, k := range keys {
            if i > 0 {
                e.buf.WriteByte(',')
            }
            e.buf.WriteString(strconv.Quote(k))
            e.buf.WriteByte(':')
            if err := e.encode(t[k]); err != nil {
                return err
            }
        }
        e.buf.WriteByte('}')

    default:
        // Support structs by re-marshal into map for deterministic ordering
        b, err := json.Marshal(t)
        if err != nil {
            return err
        }
        var val any
        dec := json.NewDecoder(bytes.NewReader(b))
        dec.UseNumber()
        if err := dec.Decode(&val); err != nil {
            return err
        }
        return e.encode(val)
    }
    return nil
}

func formatNumberString(s string) (string, error) {
    f, err := strconv.ParseFloat(s, 64)
    if err != nil {
        return "", err
    }
    return formatFloat(f)
}

func formatFloat(f float64) (string, error) {
    if math.IsNaN(f) || math.IsInf(f, 0) {
        return "", errors.New("non-finite numbers are not allowed")
    }
    if f == 0 {
        return "0", nil
    }
    if f == -0 {
        return "0", nil
    }

    abs := math.Abs(f)
    if abs >= 1e21 || abs < 1e-6 {
        s := strings.ToLower(strconv.FormatFloat(f, 'e', -1, 64))
        // Normalize exponent: strip leading zeros and optional plus sign
        if idx := strings.IndexByte(s, 'e'); idx != -1 {
            mant := s[:idx]
            exp := s[idx+1:]
            sign := ""
            if len(exp) > 0 && (exp[0] == '+' || exp[0] == '-') {
                sign = exp[:1]
                exp = exp[1:]
            }
            exp = strings.TrimLeft(exp, "0")
            if exp == "" {
                exp = "0"
            }
            // Implementation policy: retain '+' for positive exponents to keep explicit sign (e.g., 1e+21)
            s = mant + "e" + sign + exp
        }
        return s, nil
    }

    s := strconv.FormatFloat(f, 'f', -1, 64)
    if strings.Contains(s, ".") {
        s = strings.TrimRight(s, "0")
        s = strings.TrimRight(s, ".")
    }
    return s, nil
}

func reflectToInt64(v any) int64 {
    switch n := v.(type) {
    case int:
        return int64(n)
    case int8:
        return int64(n)
    case int16:
        return int64(n)
    case int32:
        return int64(n)
    case int64:
        return n
    default:
        return 0
    }
}

func reflectToUint64(v any) uint64 {
    switch n := v.(type) {
    case uint:
        return uint64(n)
    case uint8:
        return uint64(n)
    case uint16:
        return uint64(n)
    case uint32:
        return uint64(n)
    case uint64:
        return n
    case uintptr:
        return uint64(n)
    default:
        return 0
    }
}

// isValidJSONNumberString validates a numeric string against the JSON number grammar.
// Pattern: -?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?
var jsonNumberRe = regexp.MustCompile(`^-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?$`)

func isValidJSONNumberString(s string) bool {
    return jsonNumberRe.MatchString(s)
}

package volatile

import (
    "regexp"
    "sort"
    "strings"
)

type VolatileViolation struct {
    Field  string `json:"field"`
    Value  any    `json:"value"`
    Reason string `json:"reason"`
}

type ScanOptions struct {
    StrictHeuristic bool
}

var blacklist = map[string]struct{}{
    "created":              {},
    "created_at":           {},
    "created_timestamp":    {},
    "modified":             {},
    "modified_at":          {},
    "modified_timestamp":   {},
    "activated_at":         {},
    "activation_timestamp": {},
    "timestamp":            {},
    "usage_count":          {},
    "usage_metric":         {},
    "access_counter":       {},
    "hit_count":            {},
    "last_accessed":        {},
    "last_modified":        {},
    "last_used":            {},
}

var allowlist = map[string]struct{}{
    "digit_count":           {},
    "place_value_positions": {},
    "carry_threshold":       {},
}

var heuristic = regexp.MustCompile(`(?i).*(time|timestamp|modified|created|access|usage|count|counter|metric).*`)

func ScanVolatile(root map[string]any, opts ScanOptions) []VolatileViolation {
    var out []VolatileViolation

    var walk func(prefix string, v any)
    walk = func(prefix string, v any) {
        switch t := v.(type) {
        case map[string]any:
            keys := make([]string, 0, len(t))
            for k := range t {
                keys = append(keys, k)
            }
            sort.Strings(keys)
            for _, k := range keys {
                val := t[k]
                path := k
                if prefix != "" {
                    path = prefix + "." + k
                }

                lk := strings.ToLower(k)
                if _, ok := blacklist[lk]; ok {
                    out = append(out, VolatileViolation{Field: path, Value: val, Reason: "Timestamp/counter/volatile fields are prohibited in packs"})
                } else if opts.StrictHeuristic {
                    if heuristic.MatchString(k) {
                        if _, allowed := allowlist[lk]; !allowed {
                            out = append(out, VolatileViolation{Field: path, Value: val, Reason: "Strict volatile heuristic rejected this key"})
                        }
                    }
                }
                walk(path, val)
            }
        case []any:
            for i := range t {
                walk(prefix, t[i])
            }
        default:
        }
    }

    walk("", root)
    return out
}

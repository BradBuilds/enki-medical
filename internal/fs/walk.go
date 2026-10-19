package fs

import (
    "io/fs"
    "os"
    "path/filepath"
    "sort"
    "strings"

    "gdu/internal/paths"
)

type WalkEntry struct {
    RelPath string
    Info    fs.FileInfo
}

type WalkOptions struct {
    BaseDir    string
    AllowFiles func(rel string, info fs.FileInfo) bool
}

func WalkNoSymlink(opts WalkOptions) ([]WalkEntry, error) {
    var out []WalkEntry

    base := filepath.Clean(opts.BaseDir)
    err := filepath.WalkDir(base, func(p string, d fs.DirEntry, walkErr error) error {
        if walkErr != nil {
            return walkErr
        }

        relRaw, err := filepath.Rel(base, p)
        if err != nil {
            return err
        }
        relRaw = filepath.ToSlash(relRaw)

        fi, err := os.Lstat(p)
        if err != nil {
            return err
        }
        if fi.Mode()&os.ModeSymlink != 0 {
            return ErrSymlinkDetected{Path: relRaw}
        }

        // Fail if NFC normalization changes the path (enforce NFC) unless base itself
        if relRaw != "." {
            nfc := paths.ToNFC(relRaw)
            if nfc != relRaw {
                return ErrNFCMismatch{Path: relRaw}
            }
            relRaw = nfc
        }

        if relRaw == "." {
            return nil
        }

        if opts.AllowFiles != nil {
            if !opts.AllowFiles(relRaw, fi) {
                return ErrDisallowedPath{Path: relRaw}
            }
        }

        out = append(out, WalkEntry{RelPath: relRaw, Info: fi})
        return nil
    })
    if err != nil {
        return nil, err
    }

    sort.Slice(out, func(i, j int) bool { return out[i].RelPath < out[j].RelPath })
    return out, nil
}

func IsJSON(rel string) bool {
    return strings.HasSuffix(rel, ".json")
}

type ErrSymlinkDetected struct{ Path string }

func (e ErrSymlinkDetected) Error() string { return "symlink_detected:" + e.Path }

type ErrDisallowedPath struct{ Path string }

func (e ErrDisallowedPath) Error() string { return "disallowed_path:" + e.Path }

type ErrNFCMismatch struct{ Path string }

func (e ErrNFCMismatch) Error() string { return "nfc_mismatch:" + e.Path }

type simpleErr string

func (e simpleErr) Error() string { return string(e) }

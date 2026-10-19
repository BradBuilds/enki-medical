package digest

import (
	"crypto/sha256"
	"encoding/hex"
	"sort"

	"gdu/internal/jsoncanon"
)

type ManifestFile struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
}

type PackDigestResult struct {
	Manifest      []ManifestFile
	CanonicalJSON []byte
	PackDigestHex string
	PackDigest    string
}

// FileHash computes SHA-256 hash of file bytes and returns hex string.
func FileHash(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func ComputePackDigest(files []ManifestFile) (PackDigestResult, error) {
	sort.Slice(files, func(i, j int) bool { return files[i].Path < files[j].Path })

	manifest := map[string]any{
		"version": "1",
		"files":   files,
	}

	canon, err := jsoncanon.CanonicalizeJCS(manifest)
	if err != nil {
		return PackDigestResult{}, err
	}

	sum := sha256.Sum256(canon)
	hex64 := hex.EncodeToString(sum[:])

	return PackDigestResult{
		Manifest:      files,
		CanonicalJSON: canon,
		PackDigestHex: hex64,
		PackDigest:    "sha256:" + hex64,
	}, nil
}

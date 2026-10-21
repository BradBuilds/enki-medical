"""
Test suite for storage.auth.root_key module.

Validates:
- Root key generation (Ed25519)
- Encrypted persistence (AES-256-GCM)
- Sign/verify round-trip
- Public key stability
- Password protection
- Nonce randomness

No mocks. Real cryptography only.
"""
import pytest
import json
import tempfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from storage.auth.root_key import (
    RootKey,
    generate_root_key,
    load_root_key,
)


class TestRootKeyGeneration:
    """Test root key generation and persistence."""

    def test_generate_creates_encrypted_file(self, tmp_path):
        """Root key generation creates JSON envelope, not PEM."""
        key_path = tmp_path / "root.enc"
        password = "test-password-123"
        
        root_key = generate_root_key(str(key_path), password)
        
        # File must exist
        assert key_path.exists()
        
        # File must be valid JSON
        content = key_path.read_text(encoding="utf-8")
        envelope = json.loads(content)
        
        # Envelope structure correct
        assert "kdf" in envelope
        assert "iterations" in envelope
        assert "salt" in envelope
        assert "nonce" in envelope
        assert "ciphertext" in envelope
        assert len(envelope) == 5  # kdf, iterations, salt, nonce, ciphertext
        
        # No PEM markers anywhere
        assert "-----BEGIN" not in content
        assert "-----END" not in content
        assert "PRIVATE KEY" not in content

    def test_generate_returns_valid_root_key(self, tmp_path):
        """Generated root key has correct structure and methods."""
        key_path = tmp_path / "root.enc"
        password = "test-password-456"
        
        root_key = generate_root_key(str(key_path), password)
        
        # RootKey dataclass fields present
        assert hasattr(root_key, 'private_key')
        assert isinstance(root_key.private_key, ed25519.Ed25519PrivateKey)
        
        # Methods available
        assert callable(root_key.sign)
        assert callable(root_key.public_key_bytes_raw)
        assert callable(root_key.public_key_base64)

    def test_public_key_correct_length(self, tmp_path):
        """Ed25519 public key is exactly 32 bytes."""
        key_path = tmp_path / "root.enc"
        password = "test-password-789"
        
        root_key = generate_root_key(str(key_path), password)
        public_bytes = root_key.public_key_bytes_raw()
        
        assert len(public_bytes) == 32

    def test_nonce_randomness_across_generations(self, tmp_path):
        """Each generation uses different nonce (no deterministic encryption)."""
        key_path_1 = tmp_path / "root1.enc"
        key_path_2 = tmp_path / "root2.enc"
        password = "same-password"
        
        # Generate two keys with same password
        generate_root_key(str(key_path_1), password)
        generate_root_key(str(key_path_2), password)
        
        # Read raw ciphertext
        envelope_1 = json.loads(key_path_1.read_text())
        envelope_2 = json.loads(key_path_2.read_text())
        
        # Nonces must differ (CRITICAL: prevents identical ciphertext attacks)
        assert envelope_1["nonce"] != envelope_2["nonce"]
        
        # Ciphertexts must differ
        assert envelope_1["ciphertext"] != envelope_2["ciphertext"]


class TestRootKeyLoading:
    """Test root key loading and password handling."""

    def test_load_succeeds_with_correct_password(self, tmp_path):
        """Loading with correct password returns working key."""
        key_path = tmp_path / "root.enc"
        password = "correct-password"
        
        original = generate_root_key(str(key_path), password)
        loaded = load_root_key(str(key_path), password)
        
        # Public keys must match
        assert original.public_key_bytes_raw() == loaded.public_key_bytes_raw()

    def test_load_fails_with_wrong_password(self, tmp_path):
        """Loading with wrong password raises exception."""
        key_path = tmp_path / "root.enc"
        correct_password = "correct-password"
        wrong_password = "wrong-password"
        
        generate_root_key(str(key_path), correct_password)
        
        # Must raise cryptography exception (InvalidTag from AES-GCM)
        with pytest.raises(Exception) as exc_info:
            load_root_key(str(key_path), wrong_password)
        
        # Verify it's a crypto failure, not a logic error
        assert "InvalidTag" in str(type(exc_info.value).__name__) or "decrypt" in str(exc_info.value).lower()

    def test_public_key_stable_across_loads(self, tmp_path):
        """Multiple loads return same public key."""
        key_path = tmp_path / "root.enc"
        password = "stable-test"
        
        generate_root_key(str(key_path), password)
        
        # Load three times
        key1 = load_root_key(str(key_path), password)
        key2 = load_root_key(str(key_path), password)
        key3 = load_root_key(str(key_path), password)
        
        pub1 = key1.public_key_bytes_raw()
        pub2 = key2.public_key_bytes_raw()
        pub3 = key3.public_key_bytes_raw()
        
        assert pub1 == pub2 == pub3


class TestRootKeySigning:
    """Test signing and verification operations."""

    def test_sign_verify_roundtrip(self, tmp_path):
        """Sign → verify with same key succeeds."""
        key_path = tmp_path / "root.enc"
        password = "signing-test"
        message = b"test message payload"
        
        root_key = generate_root_key(str(key_path), password)
        
        # Sign message
        signature = root_key.sign(message)
        
        # Verify with public key
        public_key = root_key.private_key.public_key()
        public_key.verify(signature, message)  # Raises if invalid
        
        # Explicit success (no exception = pass)
        assert len(signature) == 64  # Ed25519 signatures are 64 bytes

    def test_signature_invalid_for_tampered_message(self, tmp_path):
        """Signature verification fails for tampered message."""
        key_path = tmp_path / "root.enc"
        password = "tamper-test"
        original_message = b"original message"
        tampered_message = b"tampered message"
        
        root_key = generate_root_key(str(key_path), password)
        
        # Sign original
        signature = root_key.sign(original_message)
        
        # Verify with tampered message must fail
        public_key = root_key.private_key.public_key()
        with pytest.raises(InvalidSignature):
            public_key.verify(signature, tampered_message)

    def test_signature_deterministic_for_same_message(self, tmp_path):
        """Ed25519 signatures are deterministic (same message → same signature)."""
        key_path = tmp_path / "root.enc"
        password = "example-test-password"
        message = b"deterministic test message"
        
        root_key = generate_root_key(str(key_path), password)
        
        # Sign same message twice
        sig1 = root_key.sign(message)
        sig2 = root_key.sign(message)
        
        # Must be identical (Ed25519 property)
        assert sig1 == sig2


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

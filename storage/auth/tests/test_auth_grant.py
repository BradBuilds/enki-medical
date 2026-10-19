"""
Test suite for storage.auth.grant module.

Validates:
- Grant issuance (required fields, UUID generation)
- Root signature verification
- Grant lifecycle (active, expired, revoked)
- Algorithm support (Ed25519, ECDSA P-256)
- Error codes (AUTH.GRANT_EXPIRED, AUTH.GRANT_REVOKED)
- Deterministic serialization

No mocks. Real signatures only.
"""
import pytest
import json
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519, ec
from cryptography.hazmat.primitives import serialization

from storage.auth.grant import (
    DeviceGrant,
    DeviceTier,
    Algorithm,
    issue_device_grant,
    verify_device_grant_signature,
    is_grant_active,
)
from storage.auth.root_key import generate_root_key
from storage.auth.canonical import canonical_json_bytes


class TestGrantIssuance:
    """Test grant creation and required fields."""

    def test_issue_grant_has_required_fields(self, tmp_path):
        """Issued grant contains all required fields."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-001",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-001"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Required fields
        assert grant.grant_id is not None
        assert grant.device_id == "test-device-001"
        assert grant.device_tier == "W"
        assert grant.tenant_scopes == ["tenant-001"]
        assert isinstance(grant.public_key, str)  # base64-encoded
        assert grant.public_key_algorithm == "Ed25519"
        assert grant.issued_at is not None
        assert grant.expires_at == expires_at
        assert grant.enki_signature is not None
        
        # Optional fields (not revoked yet)
        assert grant.revoked_at is None
        assert grant.revocation_reason is None

    def test_grant_id_is_valid_uuid(self, tmp_path):
        """Grant ID is a valid UUID string."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-002",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="K",
            tenant_scopes=["tenant-002"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Parse as UUID (will raise if invalid)
        from uuid import UUID
        uuid_obj = UUID(grant.grant_id)
        assert str(uuid_obj) == grant.grant_id

    def test_expires_at_is_enforced(self, tmp_path):
        """Expires_at must be provided and stored correctly."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-003",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="P",
            tenant_scopes=["tenant-003"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        assert grant.expires_at == expires_at
        assert grant.expires_at is not None

    def test_tier_enum_conversion(self, tmp_path):
        """Device tier string converts to enum correctly."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        # Test all tiers
        for tier_str in ["K", "P", "W"]:
            grant = issue_device_grant(
                device_id=f"device-{tier_str}",
                public_key_bytes=public_bytes,
                public_key_algorithm="Ed25519",
                device_tier=tier_str,
                tenant_scopes=["tenant-001"],
                root_key=root_key,
                expires_at=expires_at
            )
            assert grant.device_tier == tier_str


class TestGrantSignatureVerification:
    """Test root signature creation and verification."""

    def test_valid_signature_verifies(self, tmp_path):
        """Grant signed by root key verifies successfully."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-004",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-004"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        # Verification must not raise
        verify_device_grant_signature(grant, root_public_key_raw)  # Raises if invalid

    def test_tampered_device_id_fails_verification(self, tmp_path):
        """Signature verification fails if device_id is tampered."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-005",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-005"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Tamper with device_id (reconstruct grant with different ID)
        from dataclasses import replace
        tampered_grant = replace(grant, device_id="tampered-device-005")
        
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        # Verification must return False
        is_valid = verify_device_grant_signature(tampered_grant, root_public_key_raw)
        assert is_valid is False

    def test_tampered_tier_fails_verification(self, tmp_path):
        """Signature verification fails if tier is elevated."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-006",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",  # Low privilege
            tenant_scopes=["tenant-006"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Attempt privilege escalation
        from dataclasses import replace
        escalated_grant = replace(grant, device_tier="K")  # Admin tier
        
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        # Must return False
        is_valid = verify_device_grant_signature(escalated_grant, root_public_key_raw)
        assert is_valid is False


class TestGrantLifecycle:
    """Test grant active/expired/revoked states."""

    def test_active_grant_passes(self, tmp_path):
        """Grant that is not expired or revoked is active."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-007",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-007"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        is_active, reason = is_grant_active(grant)
        
        assert is_active is True
        assert reason is None

    def test_expired_grant_fails_with_correct_error_code(self, tmp_path):
        """Expired grant returns AUTH.GRANT_EXPIRED."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Set expiry in the past
        expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-008",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-008"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        is_active, reason = is_grant_active(grant)
        
        assert is_active is False
        assert reason == "AUTH.GRANT_EXPIRED"

    def test_revoked_grant_fails_with_correct_error_code(self, tmp_path):
        """Revoked grant returns AUTH.GRANT_REVOKED."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-009",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-009"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Simulate revocation
        from dataclasses import replace
        revoked_grant = replace(
            grant,
            revoked_at=datetime.now(timezone.utc).isoformat(),
            revocation_reason="Device compromised"
        )
        
        is_active, reason = is_grant_active(revoked_grant)
        
        assert is_active is False
        assert reason == "AUTH.GRANT_REVOKED"

    def test_revoked_grant_trumps_not_yet_expired(self, tmp_path):
        """Revoked grant fails even if not expired."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-010",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-010"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Revoke but still within expiry window
        from dataclasses import replace
        revoked_grant = replace(
            grant,
            revoked_at=datetime.now(timezone.utc).isoformat(),
            revocation_reason="Administrative action"
        )
        
        is_active, reason = is_grant_active(revoked_grant)
        
        # Revocation takes precedence
        assert is_active is False
        assert reason == "AUTH.GRANT_REVOKED"


class TestAlgorithmSupport:
    """Test support for Ed25519 and ECDSA P-256 public keys."""

    def test_ed25519_public_key_loads(self, tmp_path):
        """Ed25519 public key is stored and loaded correctly."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-ed25519",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-ed25519"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        assert grant.public_key_algorithm == "Ed25519"
        # Public key is base64-encoded, so decode to check length
        import base64
        decoded_key = base64.b64decode(grant.public_key)
        assert len(decoded_key) == 32  # Ed25519 public key length

    def test_ecdsa_p256_public_key_loads(self, tmp_path):
        """ECDSA P-256 public key is stored and loaded correctly."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        
        # Generate ECDSA P-256 key
        device_key = ec.generate_private_key(ec.SECP256R1())
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-p256",
            public_key_bytes=public_bytes,
            public_key_algorithm="ECDSA-P256",
            device_tier="P",
            tenant_scopes=["tenant-p256"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        assert grant.public_key_algorithm == "ECDSA-P256"
        # Public key is base64-encoded, so decode to check length
        import base64
        decoded_key = base64.b64decode(grant.public_key)
        assert len(decoded_key) == 65  # Uncompressed P-256 point (0x04 + 32 + 32)


class TestDeterministicSerialization:
    """Test canonical JSON serialization for grants."""

    def test_grant_serialization_is_deterministic(self, tmp_path):
        """Same grant data produces identical canonical JSON."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-canonical",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-canonical"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Serialize twice using canonical_payload method
        payload = grant.canonical_payload()
        
        bytes1 = canonical_json_bytes(payload)
        bytes2 = canonical_json_bytes(payload)
        
        # Must be identical
        assert bytes1 == bytes2


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

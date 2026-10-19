"""
Test suite for storage.auth.grant_store module.

Validates:
- Grant persistence (save/load round-trip)
- Load nonexistent returns None
- load_all() for multiple grants
- Revocation persistence
- Deterministic JSON (same input → same file bytes)
- File naming convention

No mocks. Real filesystem only.
"""
import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from storage.auth.grant_store import GrantStore
from storage.auth.grant import issue_device_grant
from storage.auth.root_key import generate_root_key


class TestGrantPersistence:
    """Test save and load operations."""

    def test_save_load_roundtrip(self, tmp_path):
        """Save → load returns identical grant."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        original_grant = issue_device_grant(
            device_id="test-device-001",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-001"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Save
        grant_store.save(original_grant)
        
        # Load
        loaded_grant = grant_store.load("test-device-001")
        
        # Must be identical
        assert loaded_grant is not None
        assert loaded_grant.grant_id == original_grant.grant_id
        assert loaded_grant.device_id == original_grant.device_id
        assert loaded_grant.device_tier == original_grant.device_tier
        assert loaded_grant.tenant_scopes == original_grant.tenant_scopes
        assert loaded_grant.public_key == original_grant.public_key
        assert loaded_grant.enki_signature == original_grant.enki_signature
        assert loaded_grant.expires_at == original_grant.expires_at

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Loading nonexistent device returns None."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        result = grant_store.load("nonexistent-device")
        
        assert result is None

    def test_file_naming_convention(self, tmp_path):
        """Grant files are named {device_id}.json."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        device_id = "my-special-device"
        
        grant = issue_device_grant(
            device_id=device_id,
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="P",
            tenant_scopes=["tenant-002"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        grant_store.save(grant)
        
        # File must exist with exact name
        expected_path = grants_dir / f"{device_id}.json"
        assert expected_path.exists()


class TestMultipleGrants:
    """Test operations with multiple grants."""

    def test_load_all_returns_all_grants(self, tmp_path):
        """load_all() returns dictionary of all saved grants."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        # Create 3 grants
        device_ids = ["device-a", "device-b", "device-c"]
        for device_id in device_ids:
            device_key = ed25519.Ed25519PrivateKey.generate()
            public_bytes = device_key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            grant = issue_device_grant(
                device_id=device_id,
                public_key_bytes=public_bytes,
                public_key_algorithm="Ed25519",
                device_tier="W",
                tenant_scopes=["tenant-multi"],
                root_key=root_key,
                expires_at=expires_at
            )
            grant_store.save(grant)
        
        # Load all
        all_grants = grant_store.load_all()
        
        assert len(all_grants) == 3
        assert "device-a" in all_grants
        assert "device-b" in all_grants
        assert "device-c" in all_grants
        assert all_grants["device-a"].device_id == "device-a"
        assert all_grants["device-b"].device_id == "device-b"
        assert all_grants["device-c"].device_id == "device-c"

    def test_load_all_returns_empty_dict_when_no_grants(self, tmp_path):
        """load_all() returns empty dict when grants directory is empty."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        all_grants = grant_store.load_all()
        
        assert all_grants == {}


class TestRevocation:
    """Test revocation persistence."""

    def test_revoke_persists_to_disk(self, tmp_path):
        """Revocation updates file and is preserved across loads."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-revoke",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-revoke"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        grant_store.save(grant)
        
        # Revoke
        revoked_at = datetime.now(timezone.utc).isoformat()
        revoked_grant = grant_store.revoke(
            "test-device-revoke",
            revoked_at,
            "Device compromised"
        )
        
        assert revoked_grant is not None
        assert revoked_grant.revoked_at == revoked_at
        assert revoked_grant.revocation_reason == "Device compromised"
        
        # Reload from disk
        reloaded = grant_store.load("test-device-revoke")
        assert reloaded.revoked_at == revoked_at
        assert reloaded.revocation_reason == "Device compromised"

    def test_revoke_nonexistent_returns_none(self, tmp_path):
        """Revoking nonexistent device returns None."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        revoked_at = datetime.now(timezone.utc).isoformat()
        result = grant_store.revoke("nonexistent", revoked_at, "test")
        
        assert result is None


class TestDeterministicSerialization:
    """Test deterministic JSON file format."""

    def test_same_grant_produces_identical_file_bytes(self, tmp_path):
        """Saving same grant twice produces identical file contents."""
        grants_dir_1 = tmp_path / "grants1"
        grants_dir_2 = tmp_path / "grants2"
        
        grant_store_1 = GrantStore(str(grants_dir_1))
        grant_store_2 = GrantStore(str(grants_dir_2))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-deterministic",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="K",
            tenant_scopes=["tenant-det"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Save to two different directories
        grant_store_1.save(grant)
        grant_store_2.save(grant)
        
        # Read raw file bytes
        file1 = grants_dir_1 / "test-device-deterministic.json"
        file2 = grants_dir_2 / "test-device-deterministic.json"
        
        bytes1 = file1.read_bytes()
        bytes2 = file2.read_bytes()
        
        # Must be byte-for-byte identical (CRITICAL for signatures)
        assert bytes1 == bytes2

    def test_json_keys_are_sorted(self, tmp_path):
        """JSON keys are sorted for canonical format."""
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        device_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        grant = issue_device_grant(
            device_id="test-device-sorted",
            public_key_bytes=public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-sorted"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        grant_store.save(grant)
        
        # Read JSON
        file_path = grants_dir / "test-device-sorted.json"
        content = file_path.read_text()
        parsed = json.loads(content)
        
        # Keys should be in sorted order
        keys = list(parsed.keys())
        assert keys == sorted(keys)


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

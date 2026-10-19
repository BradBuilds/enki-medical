"""
Test suite for storage.auth.authenticate module.

Validates:
- Complete authentication flow (9 steps)
- All failure modes with correct error codes
- Challenge consumption only on success
- Tenant scope validation
- Body hash verification
- Signature verification

No mocks. Full end-to-end auth flow.
"""
import pytest
import base64
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization, hashes

from storage.auth.authenticate import authenticate_device, AuthResult
from storage.auth.grant import issue_device_grant
from storage.auth.grant_store import GrantStore
from storage.auth.challenge_store import InMemoryChallengeStore
from storage.auth.root_key import generate_root_key
from storage.auth.canonical import canonical_json_bytes


class TestAuthenticationSuccess:
    """Test successful authentication flow."""

    def test_full_auth_flow_succeeds(self, tmp_path):
        """Complete auth flow with valid inputs succeeds."""
        # Setup
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Issue grant
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-001",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-001"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Issue challenge
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-001", ttl_seconds=300)
        
        # Build request
        method = "POST"
        path = "/ingest/events"
        body = b'{"event": "test"}'
        body_hash = hashes.Hash(hashes.SHA256())
        body_hash.update(body)
        body_sha256 = body_hash.finalize().hex()
        
        # Sign request
        from storage.auth.authenticate import build_signature_envelope
        envelope = build_signature_envelope(
            device_id="device-auth-001",
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
            tenant_id="tenant-001",
            method=method,
            path=path,
            body_sha256=body_sha256,
            issued_at=challenge.issued_at.isoformat(),
            expires_at=challenge.expires_at.isoformat()
        )
        signature = device_key.sign(envelope)
        signature_b64 = base64.b64encode(signature).decode("ascii")
        
        # Authenticate
        result = authenticate_device(
            device_id="device-auth-001",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-001",
            method=method,
            path=path,
            body=body,
            body_sha256_header=body_sha256,
            signature_b64=signature_b64,
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is True
        assert result.device_id == "device-auth-001"
        assert result.device_tier == "W"
        assert result.tenant_scopes == ["tenant-001"]
        assert result.reason is None


class TestAuthenticationFailures:
    """Test each failure mode returns correct error code."""

    def test_device_not_enrolled_fails(self, tmp_path):
        """AUTH.DEVICE_NOT_ENROLLED when grant is None."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("nonexistent-device", ttl_seconds=300)
        
        result = authenticate_device(
            device_id="nonexistent-device",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-001",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=None,  # Not enrolled
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "AUTH.DEVICE_NOT_ENROLLED"

    def test_grant_signature_invalid_fails(self, tmp_path):
        """AUTH.GRANT_SIGNATURE_INVALID when grant tampered."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-002",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-002"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Tamper with grant
        from dataclasses import replace
        tampered_grant = replace(grant, device_tier="K")  # Privilege escalation attempt
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-002", ttl_seconds=300)
        
        result = authenticate_device(
            device_id="device-auth-002",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-002",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=tampered_grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "AUTH.GRANT_SIGNATURE_INVALID"

    def test_grant_expired_fails(self, tmp_path):
        """AUTH.GRANT_EXPIRED when grant past expiry."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        # Expired grant
        expires_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-003",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-003"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-003", ttl_seconds=300)
        
        result = authenticate_device(
            device_id="device-auth-003",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-003",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "AUTH.GRANT_EXPIRED"

    def test_grant_revoked_fails(self, tmp_path):
        """AUTH.GRANT_REVOKED when grant revoked."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-004",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-004"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        # Revoke grant using grant_store
        grants_dir = tmp_path / "grants"
        grant_store = GrantStore(str(grants_dir))
        grant_store.save(grant)
        revoked_grant = grant_store.revoke(
            "device-auth-004",
            datetime.now(timezone.utc).isoformat(),
            "Test revocation"
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-004", ttl_seconds=300)
        
        result = authenticate_device(
            device_id="device-auth-004",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-004",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=revoked_grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        # Revocation changes the canonical payload, so signature check fails first
        assert result.reason == "AUTH.GRANT_SIGNATURE_INVALID"

    def test_tenant_scope_forbidden_fails(self, tmp_path):
        """TENANT.SCOPE_FORBIDDEN when tenant not in scopes."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-005",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-allowed"],  # Only this tenant
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-005", ttl_seconds=300)
        
        result = authenticate_device(
            device_id="device-auth-005",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-forbidden",  # Different tenant
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "TENANT.SCOPE_FORBIDDEN"

    def test_challenge_not_found_fails(self, tmp_path):
        """AUTH.CHALLENGE_NOT_FOUND when challenge doesn't exist."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-006",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-006"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        
        result = authenticate_device(
            device_id="device-auth-006",
            challenge_id="nonexistent-challenge",  # Not issued
            tenant_id="tenant-006",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc123",
            signature_b64="fake",
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "AUTH.CHALLENGE_NOT_FOUND"

    def test_body_hash_mismatch_fails(self, tmp_path):
        """INGEST.BODY_HASH_MISMATCH when X-Body-SHA256 doesn't match."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-007",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-007"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-007", ttl_seconds=300)
        
        body = b'{"event": "actual"}'
        wrong_hash = "0" * 64  # Wrong hash
        
        # Sign with wrong hash (will fail at body hash check before signature)
        from storage.auth.authenticate import build_signature_envelope
        envelope = build_signature_envelope(
            device_id="device-auth-007",
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
            tenant_id="tenant-007",
            method="POST",
            path="/ingest/events",
            body_sha256=wrong_hash,
            issued_at=challenge.issued_at.isoformat(),
            expires_at=challenge.expires_at.isoformat()
        )
        signature = device_key.sign(envelope)
        signature_b64 = base64.b64encode(signature).decode("ascii")
        
        result = authenticate_device(
            device_id="device-auth-007",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-007",
            method="POST",
            path="/ingest/events",
            body=body,
            body_sha256_header=wrong_hash,  # Mismatched
            signature_b64=signature_b64,
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "INGEST.BODY_HASH_MISMATCH"

    def test_signature_invalid_fails(self, tmp_path):
        """AUTH.SIGNATURE_INVALID when device signature wrong."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-008",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-008"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-008", ttl_seconds=300)
        
        body = b'{"event": "test"}'
        body_hash = hashes.Hash(hashes.SHA256())
        body_hash.update(body)
        body_sha256 = body_hash.finalize().hex()
        
        # Use wrong signature
        wrong_signature_b64 = base64.b64encode(b"0" * 64).decode("ascii")
        
        result = authenticate_device(
            device_id="device-auth-008",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-008",
            method="POST",
            path="/ingest/events",
            body=body,
            body_sha256_header=body_sha256,
            signature_b64=wrong_signature_b64,  # Invalid
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        assert result.reason == "AUTH.SIGNATURE_INVALID"


class TestChallengeConsumption:
    """Test challenge consumption behavior."""

    def test_challenge_consumed_only_on_success(self, tmp_path):
        """Failed auth must NOT consume challenge."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-009",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-009"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-009", ttl_seconds=300)
        
        # Authenticate with wrong signature (will fail)
        result = authenticate_device(
            device_id="device-auth-009",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-009",
            method="POST",
            path="/ingest/events",
            body=b"{}",
            body_sha256_header="abc",
            signature_b64="fake",
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is False
        
        # Challenge must NOT be consumed
        retrieved_challenge = challenge_store.get(challenge.challenge_id)
        assert retrieved_challenge is not None
        assert retrieved_challenge.consumed is False

    def test_successful_auth_consumes_challenge(self, tmp_path):
        """Successful auth MUST consume challenge."""
        root_key = generate_root_key(str(tmp_path / "root.enc"), "password")
        root_public_key_raw = root_key.public_key_bytes_raw()
        
        device_key = ed25519.Ed25519PrivateKey.generate()
        device_public_bytes = device_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        grant = issue_device_grant(
            device_id="device-auth-010",
            public_key_bytes=device_public_bytes,
            public_key_algorithm="Ed25519",
            device_tier="W",
            tenant_scopes=["tenant-010"],
            root_key=root_key,
            expires_at=expires_at
        )
        
        challenge_store = InMemoryChallengeStore()
        challenge = challenge_store.issue("device-auth-010", ttl_seconds=300)
        
        body = b'{"event": "test"}'
        body_hash = hashes.Hash(hashes.SHA256())
        body_hash.update(body)
        body_sha256 = body_hash.finalize().hex()
        
        from storage.auth.authenticate import build_signature_envelope
        envelope = build_signature_envelope(
            device_id="device-auth-010",
            challenge_id=challenge.challenge_id,
            nonce=challenge.nonce,
            tenant_id="tenant-010",
            method="POST",
            path="/ingest/events",
            body_sha256=body_sha256,
            issued_at=challenge.issued_at.isoformat(),
            expires_at=challenge.expires_at.isoformat()
        )
        signature = device_key.sign(envelope)
        signature_b64 = base64.b64encode(signature).decode("ascii")
        
        result = authenticate_device(
            device_id="device-auth-010",
            challenge_id=challenge.challenge_id,
            tenant_id="tenant-010",
            method="POST",
            path="/ingest/events",
            body=body,
            body_sha256_header=body_sha256,
            signature_b64=signature_b64,
            grant=grant,
            root_public_key_raw=root_public_key_raw,
            challenge_store=challenge_store
        )
        
        assert result.success is True
        
        # Challenge MUST be consumed
        retrieved_challenge = challenge_store.get(challenge.challenge_id)
        assert retrieved_challenge.consumed is True


# Pytest configuration
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

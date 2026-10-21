"""
Phase 4 Integration Test Helpers

Provides reusable utilities for testing Phase 4 FastAPI endpoints:
- Challenge issuance
- Canonical signing envelopes
- Request authentication
- Test client setup

All helpers use REAL cryptography (no mocks).
"""

import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from storage.auth.canonical import canonical_json_bytes
from storage.auth.grant_store import GrantStore
from storage.auth.challenge_store import InMemoryChallengeStore
from storage.auth.root_key import load_root_key
from storage.auth.config import GRANTS_DIR, ROOT_KEY_PATH, ROOT_KEY_PASSWORD
from storage.auth.grant import issue_device_grant
from datetime import datetime, timedelta, timezone


def create_test_client() -> TestClient:
    """
    Create FastAPI TestClient with Phase 3.6 singletons initialized.
    
    IMPORTANT: This mimics the production startup sequence from main.py.
    """
    from services.api.src.main import create_app
    
    app = create_app()
    
    # Initialize singletons (same as production startup)
    grant_store = GrantStore(GRANTS_DIR)
    challenge_store = InMemoryChallengeStore()
    root_key = load_root_key(ROOT_KEY_PATH, ROOT_KEY_PASSWORD)
    root_public_key_raw = root_key.public_key_bytes_raw()
    
    app.state.grant_store = grant_store
    app.state.challenge_store = challenge_store
    app.state.root_key = root_key
    app.state.root_public_key_raw = root_public_key_raw
    
    return TestClient(app)


def issue_challenge(client: TestClient, device_id: str) -> dict[str, Any]:
    """
    Issue a challenge via the API (no auth required).
    
    Returns:
        {
          "challenge_id": str,
          "nonce": str (base64),
          "issued_at": str (ISO),
          "expires_at": str (ISO)
        }
    """
    response = client.get(f"/admin/challenges/issue?device_id={device_id}")
    assert response.status_code == 200, f"Challenge issuance failed: {response.text}"
    return response.json()


def sha256_hex(data: bytes) -> str:
    """Compute SHA-256 hash as hex string."""
    return hashlib.sha256(data).hexdigest()


def build_signature_envelope(
    *,
    device_id: str,
    nonce: str,
    challenge_id: str,
    body_sha256: str,
    method: str,
    path: str,
    tenant_id: str,
    issued_at: str,
    expires_at: str,
) -> dict[str, str]:
    """
    Build canonical signing envelope (Phase 3.6 contract).
    
    This MUST match storage.auth.authenticate._signed_payload exactly.
    All fields, exact key names, alphabetical order via canonical_json_bytes.
    """
    return {
        "body_sha256": body_sha256,
        "challenge_id": challenge_id,
        "device_id": device_id,
        "expires_at": expires_at,
        "issued_at": issued_at,
        "method": method,
        "nonce": nonce,
        "path": path,
        "tenant_id": tenant_id,
    }


def sign_envelope(envelope: dict[str, str], private_key: Ed25519PrivateKey) -> str:
    """
    Sign the canonical envelope with Ed25519 private key.
    
    Returns: base64-encoded signature
    """
    canonical_bytes = canonical_json_bytes(envelope)
    signature_bytes = private_key.sign(canonical_bytes)
    return base64.b64encode(signature_bytes).decode("ascii")


def build_auth_headers(
    *,
    device_id: str,
    challenge_id: str,
    tenant_id: str,
    method: str,
    path: str,
    body: bytes,
    private_key: Ed25519PrivateKey,
    nonce: str,
    issued_at: str,
    expires_at: str,
) -> dict[str, str]:
    """
    Build complete authentication headers for a request.
    
    This performs the full Phase 3.6 client-side auth flow:
    1. Compute body hash
    2. Build signing envelope
    3. Sign envelope
    4. Return headers
    
    Args:
        device_id: Device ID from grant
        challenge_id: Challenge ID from /admin/challenges/issue
        tenant_id: Tenant scope to request
        method: HTTP method (GET, POST, etc.)
        path: Request path
        body: Raw request body bytes
        private_key: Device private key (Ed25519)
        nonce: Nonce from challenge response
        issued_at: Challenge issued_at timestamp
        expires_at: Challenge expires_at timestamp
        
    Returns:
        {
          "X-Device-ID": str,
          "X-Challenge-ID": str,
          "X-Tenant-ID": str,
          "X-Body-SHA256": str (hex),
          "X-Signature": str (base64)
        }
    """
    body_hash = sha256_hex(body)
    
    envelope = build_signature_envelope(
        device_id=device_id,
        nonce=nonce,
        challenge_id=challenge_id,
        body_sha256=body_hash,
        method=method,
        path=path,
        tenant_id=tenant_id,
        issued_at=issued_at,
        expires_at=expires_at,
    )
    
    signature = sign_envelope(envelope, private_key)
    
    return {
        "X-Device-ID": device_id,
        "X-Challenge-ID": challenge_id,
        "X-Tenant-ID": tenant_id,
        "X-Body-SHA256": body_hash,
        "X-Signature": signature,
    }


def load_device_private_key(path: str) -> Ed25519PrivateKey:
    """
    Load Ed25519 private key from PEM file.
    
    Used for loading test device keys.
    """
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_admin_device_key() -> Ed25519PrivateKey:
    """Load the bootstrap admin device key."""
    import os
    return load_device_private_key(os.environ.get("ENKI_ADMIN_KEY_PATH", "storage/keys/admin_device.pem"))


def generate_device_keypair() -> Ed25519PrivateKey:
    """Generate a fresh Ed25519 private key for tests."""
    return Ed25519PrivateKey.generate()


def save_grant(grant) -> None:
    """Persist a grant using the same GrantStore path as production."""
    from storage.auth.grant import DeviceGrant
    grant_store = GrantStore(GRANTS_DIR)
    # Handle both grant objects and dicts
    if isinstance(grant, dict):
        grant = DeviceGrant(**grant)
    grant_store.save(grant)


def list_grant_files() -> set[str]:
    """Return the set of grant filenames currently persisted (for side-effect checks)."""
    return {p.name for p in Path(GRANTS_DIR).glob("*.json")}


def issue_signed_grant(
    *,
    device_id: str,
    device_tier: str,
    tenant_scopes: list[str],
    public_key_bytes: Optional[bytes] = None,
    private_key: Optional[Ed25519PrivateKey] = None,
    expires_at_iso: Optional[str] = None,
    expires_in_days: int = 365,
):
    """
    Issue a root-signed grant for tests using production signer and storage layout.
    
    Supports two calling patterns:
    1. With public_key_bytes + expires_at_iso (4.1B pattern)
    2. With private_key + expires_in_days (4.1C pattern)
    
    Returns grant object (for 4.1B) or grant dict (for 4.1C).
    """
    root_key = load_root_key(ROOT_KEY_PATH, ROOT_KEY_PASSWORD)
    
    # Determine public key bytes
    if public_key_bytes is None:
        if private_key is None:
            raise ValueError("Must provide either public_key_bytes or private_key")
        public_key_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    
    # Determine expiry
    if expires_at_iso is None:
        expires_at_iso = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
    
    grant = issue_device_grant(
        device_id=device_id,
        public_key_bytes=public_key_bytes,
        public_key_algorithm="Ed25519",
        device_tier=device_tier,  # type: ignore[arg-type]
        tenant_scopes=tenant_scopes,
        root_key=root_key,
        expires_at=expires_at_iso,
    )
    
    # If called with private_key (4.1C), return dict; otherwise return object (4.1B)
    if private_key is not None:
        return grant.to_dict()
    else:
        save_grant(grant)
        return grant


def authenticated_post(
    client: TestClient,
    url: str,
    device_id: str,
    tenant_id: str,
    private_key: Ed25519PrivateKey,
    body: bytes | dict | list,
) -> Any:
    """
    Make an authenticated POST request to the API.
    
    This is a convenience wrapper that:
    1. Issues a challenge
    2. Builds auth headers
    3. Makes the request
    4. Returns the response
    
    Args:
        client: TestClient instance
        url: Endpoint path (e.g., "/ingest/events")
        device_id: Device ID from grant
        tenant_id: Tenant scope to request
        private_key: Device private key
        body: Request body (dict/list will be JSON-serialized)
        
    Returns:
        Response object
    """
    # Serialize body if needed
    if isinstance(body, (dict, list)):
        body_bytes = json.dumps(body).encode("utf-8")
        content_type = "application/json"
    else:
        body_bytes = body
        content_type = "application/octet-stream"
    
    # Issue challenge
    challenge = issue_challenge(client, device_id)
    
    # Build auth headers
    headers = build_auth_headers(
        device_id=device_id,
        challenge_id=challenge["challenge_id"],
        tenant_id=tenant_id,
        method="POST",
        path=url,
        body=body_bytes,
        private_key=private_key,
        nonce=challenge["nonce"],
        issued_at=challenge["issued_at"],
        expires_at=challenge["expires_at"],
    )
    headers["Content-Type"] = content_type
    
    # Make request
    return client.post(url, content=body_bytes, headers=headers)


def authenticated_get(
    client: TestClient,
    url: str,
    device_id: str,
    tenant_id: str,
    private_key: Ed25519PrivateKey,
) -> Any:
    """
    Make an authenticated GET request to the API.
    
    For GET requests, body is empty bytes (body_hash = sha256(b"")).
    """
    body_bytes = b""
    
    # Issue challenge
    challenge = issue_challenge(client, device_id)
    
    # Build auth headers
    headers = build_auth_headers(
        device_id=device_id,
        challenge_id=challenge["challenge_id"],
        tenant_id=tenant_id,
        method="GET",
        path=url,
        body=body_bytes,
        private_key=private_key,
        nonce=challenge["nonce"],
        issued_at=challenge["issued_at"],
        expires_at=challenge["expires_at"],
    )
    
    # Make request
    return client.get(url, headers=headers)


def delete_grant(device_id: str) -> None:
    """Remove a test grant file if present."""
    p = Path(GRANTS_DIR) / f"{device_id}.json"
    try:
        p.unlink()
    except FileNotFoundError:
        pass

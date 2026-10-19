"""
A small Enki client you can copy into your own app.

Every request (except /health and challenge issuance) is signed: the client asks Enki for a
one-time challenge, builds a canonical envelope (device, challenge, tenant, method, path, body hash,
nonce, times), signs it with the device's Ed25519 key, and sends the signature in headers.
Needs: httpx, cryptography.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def canonical_json(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_key(path: str | Path) -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(Path(path).read_bytes(), password=None)


def new_key(path: str | Path) -> Ed25519PrivateKey:
    """Create a device key and save it (PEM, owner-only where the OS allows)."""
    key = Ed25519PrivateKey.generate()
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()))
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


class EnkiClient:
    def __init__(self, base_url: str, device_id: str, key: Ed25519PrivateKey, tenant_id: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.device_id = device_id
        self.key = key
        self.tenant_id = tenant_id
        self.http = httpx.Client(timeout=timeout)

    def health(self) -> dict:
        r = self.http.get(f"{self.base_url}/health")
        r.raise_for_status()
        return r.json()

    def _signed(self, method: str, path: str, body: bytes = b"", content_type: str | None = None) -> httpx.Response:
        challenge = self.http.get(f"{self.base_url}/admin/challenges/issue", params={"device_id": self.device_id})
        challenge.raise_for_status()
        c = challenge.json()
        body_sha256 = hashlib.sha256(body).hexdigest()
        envelope = {
            "body_sha256": body_sha256,
            "challenge_id": c["challenge_id"],
            "device_id": self.device_id,
            "expires_at": c["expires_at"],
            "issued_at": c["issued_at"],
            "method": method,
            "nonce": c["nonce"],
            "path": path,
            "tenant_id": self.tenant_id,
        }
        signature = base64.b64encode(self.key.sign(canonical_json(envelope))).decode("ascii")
        headers = {
            "X-Device-ID": self.device_id,
            "X-Challenge-ID": c["challenge_id"],
            "X-Tenant-ID": self.tenant_id,
            "X-Body-SHA256": body_sha256,
            "X-Signature": signature,
        }
        if content_type:
            headers["Content-Type"] = content_type
        return self.http.request(method, f"{self.base_url}{path}", content=body, headers=headers)

    # --- admin (Tier K) -------------------------------------------------------------------------
    def enroll_device(self, device_id: str, public_key: str, tier: str, tenant_scopes: list[str], expires_days: int = 365) -> httpx.Response:
        body = json.dumps({
            "device_id": device_id,
            "public_key": public_key,
            "public_key_algorithm": "Ed25519",
            "tenant_scopes": tenant_scopes,
            "explicit_tier": tier,
            "expires_days": expires_days,
        }).encode("utf-8")
        return self._signed("POST", "/admin/enroll_device", body, "application/json")

    # --- write (Tier W and K) -------------------------------------------------------------------
    def send_events(self, events: list[dict]) -> httpx.Response:
        body = "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in events).encode("utf-8")
        return self._signed("POST", "/ingest/events", body, "application/x-ndjson")

    # --- read (Tier P and K) --------------------------------------------------------------------
    def audit_events(self, limit: int = 20) -> httpx.Response:
        return self._signed("GET", f"/audit-events?limit={limit}")

    def receipt(self, txid: str) -> httpx.Response:
        return self._signed("GET", f"/receipts/{txid}")

    def verify_chain(self) -> httpx.Response:
        return self._signed("GET", "/chain/verify")

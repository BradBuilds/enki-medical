# storage/auth/grant.py
"""
DeviceGrant issuance + verification.

Adds:
- grant_id
- expires_at (required)
- revoked_at / revocation_reason

Root signer is Ed25519. Device keys may be Ed25519 or ECDSA P-256.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Literal
import uuid

from cryptography.hazmat.primitives.asymmetric import ed25519, ec
from cryptography.hazmat.primitives import serialization

from storage.auth.canonical import canonical_json_bytes
from storage.auth.root_key import RootKey

DeviceTier = Literal["K", "P", "W"]
Algorithm = Literal["Ed25519", "ECDSA_P256"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DeviceGrant:
    grant_id: str
    device_id: str

    # device pubkey
    public_key: str                 # base64
    public_key_algorithm: Algorithm

    # authorization semantics
    device_tier: DeviceTier
    tenant_scopes: list[str]

    issued_at: str                  # ISO8601
    expires_at: str                 # ISO8601 (required)

    # revocation
    revoked_at: Optional[str] = None
    revocation_reason: Optional[str] = None

    # root signature over canonical payload
    enki_signature: str = ""        # base64 (Ed25519)

    def to_dict(self) -> dict:
        return asdict(self)

    def canonical_payload(self) -> dict:
        """
        Canonical payload for root signing.
        NOTE: exclude enki_signature itself.
        """
        return {
            "expires_at": self.expires_at,
            "grant_id": self.grant_id,
            "device_id": self.device_id,
            "issued_at": self.issued_at,
            "public_key": self.public_key,
            "public_key_algorithm": self.public_key_algorithm,
            "device_tier": self.device_tier,
            "revoked_at": self.revoked_at,
            "revocation_reason": self.revocation_reason,
            "tenant_scopes": sorted(self.tenant_scopes),
        }

    def canonical_message(self) -> bytes:
        return canonical_json_bytes(self.canonical_payload())


def encode_public_key_b64(public_key_obj) -> tuple[str, Algorithm]:
    """
    Encode a device public key to base64 + algorithm label.
    - Ed25519: raw 32 bytes
    - ECDSA P-256: X9.62 uncompressed point
    """
    if isinstance(public_key_obj, ed25519.Ed25519PublicKey):
        b = public_key_obj.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(b).decode("ascii"), "Ed25519"

    if isinstance(public_key_obj, ec.EllipticCurvePublicKey):
        b = public_key_obj.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        return base64.b64encode(b).decode("ascii"), "ECDSA_P256"

    raise ValueError("Unsupported public key object type")


def load_device_public_key(grant: DeviceGrant):
    key_bytes = base64.b64decode(grant.public_key)

    if grant.public_key_algorithm == "Ed25519":
        return ed25519.Ed25519PublicKey.from_public_bytes(key_bytes)

    if grant.public_key_algorithm == "ECDSA_P256":
        return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), key_bytes)

    raise ValueError(f"Unsupported algorithm: {grant.public_key_algorithm}")


def issue_device_grant(
    *,
    device_id: str,
    public_key_bytes: bytes,
    public_key_algorithm: Algorithm,
    device_tier: DeviceTier,
    tenant_scopes: list[str],
    root_key: RootKey,
    expires_at: str,
) -> DeviceGrant:
    grant = DeviceGrant(
        grant_id=str(uuid.uuid4()),
        device_id=device_id,
        public_key=base64.b64encode(public_key_bytes).decode("ascii"),
        public_key_algorithm=public_key_algorithm,
        device_tier=device_tier,
        tenant_scopes=tenant_scopes,
        issued_at=utcnow_iso(),
        expires_at=expires_at,
    )

    sig = root_key.sign(grant.canonical_message())
    grant.enki_signature = base64.b64encode(sig).decode("ascii")
    return grant


def verify_device_grant_signature(grant: DeviceGrant, root_public_key_raw: bytes) -> bool:
    msg = grant.canonical_message()
    sig = base64.b64decode(grant.enki_signature)

    pub = ed25519.Ed25519PublicKey.from_public_bytes(root_public_key_raw)
    try:
        pub.verify(sig, msg)
        return True
    except Exception:
        return False


def is_grant_active(grant: DeviceGrant) -> tuple[bool, str | None]:
    """
    Returns (active, reason_code).
    Reason codes are stable strings suitable for Spec-aligned error mapping.
    """
    if grant.revoked_at is not None:
        return False, "AUTH.GRANT_REVOKED"

    try:
        exp = datetime.fromisoformat(grant.expires_at)
    except Exception:
        return False, "AUTH.GRANT_EXPIRES_AT_INVALID"

    if datetime.now(timezone.utc) >= exp:
        return False, "AUTH.GRANT_EXPIRED"

    return True, None

"""
First-run setup for an Enki node. Safe to run on every start: it only creates what is missing.

On first run it creates, inside your data folder:
  keys/root_key.enc        the node's root signing key, encrypted with ENKI_ROOT_PASSWORD
  keys/admin_device.pem    the private key of your first admin device (Tier K)
  grants/<admin id>.json   that device's grant, signed by the root key

Nothing here is ever committed: the data folder is in .gitignore. Keep admin_device.pem private;
whoever holds it can enroll devices for your tenants.

Settings (environment):
  ENKI_ROOT_PASSWORD     required; protects the root key
  ENKI_DATA_DIR          default ./enki-data (the container uses /data)
  ENKI_ADMIN_DEVICE_ID   default admin-device
  ENKI_TENANTS           comma-separated tenant ids the admin may manage; default demo-tenant
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = Path(os.environ.get("ENKI_DATA_DIR", "enki-data"))
ADMIN_KEY_PATH = Path(os.environ.get("ENKI_ADMIN_KEY_PATH", str(DATA / "keys" / "admin_device.pem")))
ADMIN_ID = os.environ.get("ENKI_ADMIN_DEVICE_ID", "admin-device")
TENANTS = [t.strip() for t in os.environ.get("ENKI_TENANTS", "demo-tenant").split(",") if t.strip()]


def main() -> int:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from storage.auth.grant import issue_device_grant
    from storage.auth.grant_store import GrantStore
    from storage.auth.root_key import generate_root_key, load_root_key

    password = os.environ.get("ENKI_ROOT_PASSWORD", "")
    if not password:
        print("ENKI_ROOT_PASSWORD is not set. Put a long random value in .env (see .env.example).")
        return 1
    if password.lower().startswith("change"):
        print("ENKI_ROOT_PASSWORD still has its example value. Set your own in .env.")
        return 1

    from storage.auth.config import GRANTS_DIR, ROOT_KEY_PATH   # same locations the API uses
    root_path = Path(ROOT_KEY_PATH)
    grants_dir = Path(GRANTS_DIR)
    root_path.parent.mkdir(parents=True, exist_ok=True)
    grants_dir.mkdir(parents=True, exist_ok=True)

    if root_path.exists():
        root_key = load_root_key(str(root_path), password)
    else:
        root_key = generate_root_key(str(root_path), password)
        print(f"Created root key: {root_path}")

    store = GrantStore(str(grants_dir))
    if store.load(ADMIN_ID) is None:
        admin = Ed25519PrivateKey.generate()
        ADMIN_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_KEY_PATH.write_bytes(admin.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                       serialization.NoEncryption()))
        try:
            os.chmod(ADMIN_KEY_PATH, 0o600)
        except OSError:
            pass
        public_raw = admin.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        expires = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        grant = issue_device_grant(device_id=ADMIN_ID, public_key_bytes=public_raw, public_key_algorithm="Ed25519",
                                   device_tier="K", tenant_scopes=TENANTS, root_key=root_key, expires_at=expires)
        store.save(grant)
        print(f"Created admin device '{ADMIN_ID}' for tenants {TENANTS}")
        print(f"  private key: {ADMIN_KEY_PATH}  (keep this private)")
    else:
        print(f"Node ready. Admin device '{ADMIN_ID}' already exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

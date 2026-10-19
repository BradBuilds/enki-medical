"""
Pytest configuration for ENKI Node test suite.

Provides:
- Auto-skip for DB-dependent tests when ENKI_DB_DSN not configured
- Custom markers registration
"""

import os
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "db: mark test as requiring database (ENKI_DB_DSN must be set)"
    )
    config.addinivalue_line(
        "markers",
        "contract: mark test as golden contract vector (executable)"
    )
    config.addinivalue_line(
        "markers",
        "contract_future: mark test as future contract vector (documented, not executable)"
    )


def pytest_collection_modifyitems(config, items):
    """
    Auto-skip DB-dependent tests when ENKI_DB_DSN not configured.
    
    Tests marked with @pytest.mark.db will be skipped unless
    ENKI_DB_DSN environment variable is set.
    """
    db_dsn = os.getenv("ENKI_DB_DSN")
    skip_db = pytest.mark.skip(reason="ENKI_DB_DSN not set - skipping DB-dependent tests")
    
    for item in items:
        if "db" in item.keywords and not db_dsn:
            item.add_marker(skip_db)


# ---------------------------------------------------------------------------
# Test identity: every test run gets its own throwaway root key, admin device key
# and admin grant in a temporary folder. Nothing secret is ever stored in the repo.
# Set these before any test imports storage.auth.config (which reads them once).
# ---------------------------------------------------------------------------
import tempfile as _tempfile

_TEST_HOME = _tempfile.mkdtemp(prefix="enki-test-")
os.environ.setdefault("ENKI_ROOT_PASSWORD", "test-only-password")
os.environ.setdefault("ENKI_ROOT_KEY_PATH", os.path.join(_TEST_HOME, "root_key.enc"))
os.environ.setdefault("ENKI_GRANTS_DIR", os.path.join(_TEST_HOME, "grants"))
os.environ.setdefault("ENKI_ADMIN_KEY_PATH", os.path.join(_TEST_HOME, "admin_device.pem"))
TEST_ADMIN_DEVICE_ID = "example-admin-device"


def _bootstrap_test_identity():
    from datetime import datetime, timedelta, timezone
    from pathlib import Path
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from storage.auth.root_key import generate_root_key
    from storage.auth.grant import issue_device_grant
    from storage.auth.grant_store import GrantStore

    if Path(os.environ["ENKI_ROOT_KEY_PATH"]).exists():
        return
    Path(os.environ["ENKI_GRANTS_DIR"]).mkdir(parents=True, exist_ok=True)
    root_key = generate_root_key(os.environ["ENKI_ROOT_KEY_PATH"], os.environ["ENKI_ROOT_PASSWORD"])
    admin_key = Ed25519PrivateKey.generate()
    Path(os.environ["ENKI_ADMIN_KEY_PATH"]).write_bytes(admin_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public_raw = admin_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    expires = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    grant = issue_device_grant(device_id=TEST_ADMIN_DEVICE_ID, public_key_bytes=public_raw, public_key_algorithm="Ed25519",
                               device_tier="K", tenant_scopes=["practice-001"], root_key=root_key, expires_at=expires)
    GrantStore(os.environ["ENKI_GRANTS_DIR"]).save(grant)


_bootstrap_test_identity()


def pytest_sessionstart(session):
    """With a database configured, create the tables once (idempotent) so a brand-new database works."""
    if os.getenv("ENKI_DB_DSN"):
        from storage.postgres.db import initialize_schema
        initialize_schema()

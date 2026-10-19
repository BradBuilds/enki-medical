"""
Contract Verification Harness (v1.0.0)

Validates golden vectors against CLIENT_CONTRACT.md conformance.

Scope:
- Minimal shape validation for v1.0.0 lock
- Exact match on status codes and error envelopes
- Variable fields (UUIDs, timestamps) validated by type/presence only

Run:
    pytest services/api/tests/test_contract_verification.py -m contract
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from services.api.src.main import create_app
from storage.auth.config import GRANTS_DIR, ROOT_KEY_PATH, ROOT_KEY_PASSWORD
from storage.auth.grant_store import GrantStore
from storage.auth.challenge_store import InMemoryChallengeStore
from storage.auth.root_key import load_root_key
from services.api.tests.helpers import (
    issue_challenge,
    build_auth_headers,
    load_admin_device_key,
    sha256_hex,
)


@pytest.fixture(scope="module")
def client():
    """
    FastAPI test client for contract verification.
    
    Note: TestClient does not automatically trigger lifespan context,
    so we manually initialize app.state (same as existing test helpers).
    """
    app = create_app()
    
    # Initialize Phase 3.6 singletons (same as production startup)
    grant_store = GrantStore(GRANTS_DIR)
    challenge_store = InMemoryChallengeStore()
    root_key = load_root_key(ROOT_KEY_PATH, ROOT_KEY_PASSWORD)
    root_public_key_raw = root_key.public_key_bytes_raw()
    
    app.state.grant_store = grant_store
    app.state.challenge_store = challenge_store
    app.state.root_key = root_key
    app.state.root_public_key_raw = root_public_key_raw
    
    return TestClient(app)


def load_vector(vector_path: Path):
    """Load request.json and response.json from a golden vector directory."""
    request_file = vector_path / "request.json"
    response_file = vector_path / "response.json"
    
    if not request_file.exists() or not response_file.exists():
        pytest.skip(f"Vector {vector_path.name} not yet implemented")
    
    with open(request_file, "r", encoding="utf-8") as f:
        request_data = json.load(f)
    
    with open(response_file, "r", encoding="utf-8") as f:
        response_data = json.load(f)
    
    return request_data, response_data


def validate_shape(actual, expected_shape):
    """
    Validate that actual response matches expected shape.
    
    Shape markers:
    - "<string>": any string value
    - "<base64 string>": base64-encoded string
    - "<ISO8601 timestamp>": ISO8601 timestamp string
    - Exact values: must match exactly
    """
    if isinstance(expected_shape, dict):
        assert isinstance(actual, dict), f"Expected dict, got {type(actual)}"
        for key, expected_value in expected_shape.items():
            assert key in actual, f"Missing key: {key}"
            if isinstance(expected_value, str) and expected_value.startswith("<") and expected_value.endswith(">"):
                # Shape marker - validate type only
                assert isinstance(actual[key], str), f"Key {key} expected string, got {type(actual[key])}"
            elif isinstance(expected_value, (dict, list)):
                validate_shape(actual[key], expected_value)
            else:
                # Exact match required
                assert actual[key] == expected_value, f"Key {key}: expected {expected_value}, got {actual[key]}"
    elif isinstance(expected_shape, list):
        assert isinstance(actual, list), f"Expected list, got {type(actual)}"
        # List validation can be expanded as needed
    else:
        assert actual == expected_shape


def run_vector_test(client: TestClient, vector_path: Path):
    """Execute a single golden vector test."""
    request_data, response_data = load_vector(vector_path)
    
    # Build request
    method = request_data["method"]
    path = request_data["path"]
    
    # Add query string if present
    if "query" in request_data and request_data["query"]:
        path = f"{path}?{request_data['query']}"
    
    headers = request_data.get("headers", {})
    body = request_data.get("body")
    
    # Detect runtime-computed auth headers (placeholders)
    needs_auth = (
        headers.get("X-Body-SHA256") == "computed-at-runtime" or
        headers.get("X-Signature") == "computed-at-runtime" or
        headers.get("X-Challenge-ID") == "<CHALLENGE_ID>"
    )
    
    if needs_auth:
        # Compute auth headers at runtime using test helpers
        device_id = headers["X-Device-ID"]
        tenant_id = headers["X-Tenant-ID"]
        
        # Serialize body to bytes
        if body is not None:
            if isinstance(body, str):
                # Body is already a string (e.g., JSONL)
                # Perform runtime placeholder substitutions to avoid storage dedup conflicts
                # Supported placeholders:
                #  - <NOW_ISO>: current UTC timestamp in ISO-8601
                #  - <UNIQ>: random unique token
                from datetime import datetime, timezone
                import uuid
                now_iso = datetime.now(timezone.utc).isoformat()
                uniq = uuid.uuid4().hex
                body_runtime = body.replace("<NOW_ISO>", now_iso).replace("<UNIQ>", uniq)
                body_bytes = body_runtime.encode("utf-8")
            else:
                # Body is dict/list, serialize to JSON
                body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
        else:
            body_bytes = b""
        
        # Issue challenge
        challenge = issue_challenge(client, device_id)
        
        # Build auth headers (this computes body hash, signature, etc.)
        admin_key = load_admin_device_key()
        auth_headers = build_auth_headers(
            device_id=device_id,
            challenge_id=challenge["challenge_id"],
            tenant_id=tenant_id,
            method=method,
            path=path,
            body=body_bytes,
            private_key=admin_key,
            nonce=challenge["nonce"],
            issued_at=challenge["issued_at"],
            expires_at=challenge["expires_at"],
        )
        
        # Check if this is a tampered signature test
        if headers.get("X-Signature") == "TAMPERED_SIGNATURE_AT_RUNTIME":
            # Flip first byte of signature to create invalid signature
            import base64
            valid_sig = base64.b64decode(auth_headers["X-Signature"])
            tampered_sig = bytes([valid_sig[0] ^ 0xFF]) + valid_sig[1:]
            auth_headers["X-Signature"] = base64.b64encode(tampered_sig).decode("ascii")
        
        # Merge auth headers (computed overrides placeholders)
        headers.update(auth_headers)
    else:
        # Non-authenticated request: convert body to bytes if present
        if body is not None:
            body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
        else:
            body_bytes = b""
    
    # Execute request
    if method == "GET":
        resp = client.get(path, headers=headers)
    elif method == "POST":
        if needs_auth:
            # Use raw bytes for authenticated POST (body already serialized above)
            resp = client.post(path, headers=headers, content=body_bytes)
        else:
            # Use JSON for non-authenticated POST
            resp = client.post(path, headers=headers, json=body)
    else:
        pytest.fail(f"Unsupported method: {method}")
    
    # Validate response
    expected_status = response_data["status_code"]
    assert resp.status_code == expected_status, f"Expected {expected_status}, got {resp.status_code}. Body: {resp.text}"
    
    # Validate body if expected
    if "body" in response_data:
        actual_body = resp.json()
        expected_body = response_data["body"]
        assert actual_body == expected_body, f"Body mismatch.\nExpected: {expected_body}\nActual: {actual_body}"
    
    # Validate body_shape if expected (for variable fields)
    if "body_shape" in response_data:
        actual_body = resp.json()
        expected_shape = response_data["body_shape"]
        validate_shape(actual_body, expected_shape)


# Golden vector directory
GOLDEN_DIR = Path("contracts/golden")


# Public endpoints (no auth)
@pytest.mark.contract
class TestPublicEndpoints:
    """Test vectors for public endpoints (no auth required)."""
    
    def test_health(self, client):
        """GET /health - Health check"""
        run_vector_test(client, GOLDEN_DIR / "health")
    
    def test_admin_challenges_issue(self, client):
        """GET /admin/challenges/issue - Challenge issuance"""
        run_vector_test(client, GOLDEN_DIR / "admin_challenges_issue")


# Auth failure vectors
@pytest.mark.contract
class TestAuthFailures:
    """Test vectors for authentication failures."""
    
    def test_missing_auth_headers(self, client):
        """Missing auth headers → 401 API.UNAUTHORIZED"""
        run_vector_test(client, GOLDEN_DIR / "auth_fail_missing_headers")
    
    def test_wrong_signature(self, client):
        """Wrong signature → 401 API.UNAUTHORIZED"""
        run_vector_test(client, GOLDEN_DIR / "auth_fail_wrong_signature")


# Authenticated endpoints (stubs for v1.0.0)
class TestAuthenticatedEndpoints:
    """Test vectors for authenticated endpoints."""
    
    @pytest.mark.contract
    def test_admin_enroll_device(self, client):
        """POST /admin/enroll_device"""
        run_vector_test(client, GOLDEN_DIR / "admin_enroll_device")
    
    @pytest.mark.db
    def test_ingest_events(self, client):
        """POST /ingest/events (DB-backed contract vector)"""
        run_vector_test(client, GOLDEN_DIR / "ingest_events")
    
    @pytest.mark.db
    def test_query_assertions(self, client):
        """GET /query/assertions (DB-backed contract vector)"""
        run_vector_test(client, GOLDEN_DIR / "query_assertions")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_receipts_get(self, client):
        """GET /receipts/{txid}"""
        run_vector_test(client, GOLDEN_DIR / "receipts_txid")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_audit_events(self, client):
        """GET /audit-events"""
        run_vector_test(client, GOLDEN_DIR / "audit_events")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_chain_verify(self, client):
        """GET /chain/verify"""
        run_vector_test(client, GOLDEN_DIR / "chain_verify")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_artifacts_post(self, client):
        """POST /artifacts"""
        run_vector_test(client, GOLDEN_DIR / "artifacts_post")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_artifacts_get(self, client):
        """GET /artifacts/{cid}"""
        run_vector_test(client, GOLDEN_DIR / "artifacts_cid_get")
    
    @pytest.mark.skip(reason="Vector not yet implemented")
    def test_artifacts_content(self, client):
        """GET /artifacts/{cid}/content"""
        run_vector_test(client, GOLDEN_DIR / "artifacts_cid_content")

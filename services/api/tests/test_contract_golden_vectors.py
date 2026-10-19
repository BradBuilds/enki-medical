"""
Phase 4.4A — Golden Vector Harness (MINIMAL_SHAPE)
- Loads vectors under contracts/golden/<endpoint>/
- Issues requests using FastAPI TestClient
- Strict diffs: status + error envelope keys (error_code/message/meta when expected)
- Happy paths: MINIMAL_SHAPE assertions (keys only)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient

from services.api.tests.helpers import create_test_client

GOLDEN_ROOT = Path("contracts/golden")

WRITTEN_VECTORS = [
    "health",
    "admin_challenges_issue",
    "admin_enroll_device",
    "auth_fail_missing_headers",
    "auth_fail_wrong_signature",
    "ingest_events",
    "query_assertions",
]
PLANNED_VECTORS = [
    "receipts_txid",
    "audit_events",
    "chain_verify",
    "artifacts_post",
    "artifacts_cid_get",
    "artifacts_cid_content",
]

FORCE_500_HEADER = "X-Test-Force-Unregistered-Code"
FORCE_500_VALUE = "TEST.UNREGISTERED"


def _load_json(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _assert_error_envelope(body: Dict[str, Any], expected: Dict[str, Any]) -> None:
    """Assert error envelope shape and values per ERROR_CONTRACT."""
    assert "detail" in body and isinstance(body["detail"], dict), "Missing detail object"
    assert "error_code" in body["detail"], "Missing error_code"
    assert "message" in body["detail"], "Missing message"
    assert "request_id" in body, "Missing request_id"

    # Strict on these if present in expected
    exp_detail = expected.get("detail", {})
    if "error_code" in exp_detail:
        assert body["detail"]["error_code"] == exp_detail["error_code"], \
            f"error_code mismatch: {body['detail']['error_code']} != {exp_detail['error_code']}"
    if "message" in exp_detail:
        assert body["detail"]["message"] == exp_detail["message"], \
            f"message mismatch: {body['detail']['message']} != {exp_detail['message']}"
    if "meta" in exp_detail:
        assert body["detail"].get("meta") == exp_detail["meta"], \
            f"meta mismatch: {body['detail'].get('meta')} != {exp_detail['meta']}"


@pytest.fixture
def golden_client():
    """TestClient with forced-500 middleware for golden vectors."""
    client = create_test_client()
    
    # TODO: Add middleware to honor X-Test-Force-Unregistered-Code header
    # If header present: raise_enki_error("TEST.UNREGISTERED") -> 500 SERVER.MISCONFIGURATION
    
    return client


@pytest.mark.contract
def test_golden_vectors_smoke(golden_client) -> None:
    """
    Minimal smoke test — replace with full parametrized loader once middleware is wired.
    """
    assert GOLDEN_ROOT.exists(), "contracts/golden missing"

    # Vectors that exist today must all be present.
    for dirname in WRITTEN_VECTORS:
        dirpath = GOLDEN_ROOT / dirname
        assert dirpath.exists(), f"Missing golden directory: {dirname}"


@pytest.mark.contract_future
@pytest.mark.xfail(reason="planned golden vectors, not written yet", strict=False)
def test_planned_golden_vectors_exist() -> None:
    """Planned vectors for the read and artifact endpoints. Writing them is open work."""
    missing = [d for d in PLANNED_VECTORS if not (GOLDEN_ROOT / d).exists()]
    assert not missing, f"planned vectors not written yet: {missing}"


# TODO: Implement parametrized test once vectors are added:
# @pytest.mark.parametrize("vector_path", collect_all_vectors())
# def test_golden_vector(golden_client, vector_path):
#     - load request.json, optional headers.json, response.json
#     - issue request via golden_client
#     - compare status + JSON shape (MINIMAL_SHAPE rules)
#     - for errors: assert envelope via _assert_error_envelope

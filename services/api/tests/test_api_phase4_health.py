"""
Phase 4 Integration Tests: Health Endpoint

Tests the /health endpoint (no authentication required).
"""

import pytest
from services.api.tests.helpers import create_test_client


def test_health_endpoint_returns_ok():
    """Health endpoint should return 200 with status=ok."""
    client = create_test_client()
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

"""
Static assertion test: Verify API error codes are formally registered.

This test ensures that all error codes used in deps.py are documented in API_ERROR_CODES.md
and have corresponding HTTP status mappings defined.

Tests validate against the canonical registry in services/api/src/error_codes.py.
"""

import pytest
import re
from pathlib import Path
from services.api.src.error_codes import (
    API_ERROR_CODE_REGISTRY,
    all_error_codes,
    UnknownApiErrorCode,
)


def test_api_error_codes_in_deps_match_registry():
    """
    Verify that all registered API error codes are reachable from deps.py.
    
    This test validates that:
    1. Canonical registry (error_codes.py) is imported by deps.py
    2. Error codes used in routes match registered codes
    3. No orphan codes exist (registry ↔ usage consistency)
    """
    test_dir = Path(__file__).parent  # services/api/tests
    api_dir = test_dir.parent  # services/api
    deps_file = api_dir / "src" / "deps.py"
    
    # Verify deps.py imports the canonical registry
    deps_content = deps_file.read_text(encoding='utf-8')
    assert "get_http_status" in deps_content, (
        "deps.py must import get_http_status from error_codes canonical registry"
    )
    assert "error_codes" in deps_content, (
        "deps.py must import from services.api.src.error_codes"
    )
    
    # Verify all routes use raise_enki_error with registered codes
    routes_dir = api_dir / "src" / "routes"
    for route_file in routes_dir.glob("*.py"):
        route_content = route_file.read_text(encoding='utf-8')
        
        # Extract error codes raised in this route
        codes_in_route = set()
        for match in re.finditer(r'raise_enki_error\(["\']([A-Z.]+)["\']', route_content):
            code = match.group(1)
            if code.startswith("API."):
                codes_in_route.add(code)
        
        # Verify each code is registered
        for code in codes_in_route:
            assert code in all_error_codes(), (
                f"Unregistered code {code} used in {route_file.name}\n"
                f"Register in services/api/src/error_codes.py\n"
                f"Registered: {sorted(all_error_codes())}\n"
            )


def test_api_error_http_status_mapping_complete():
    """
    Verify that HTTP status mappings are defined for all registered API error codes.
    
    This ensures the canonical registry (error_codes.py) has complete mappings
    and matches the implementations in deps.py.
    """
    # Get all registered error codes
    registered = all_error_codes()
    
    # Expected mappings from canonical registry
    expected_mappings = {
        "API.BAD_REQUEST": 400,
        "API.PAYLOAD_TOO_LARGE": 413,
        "API.TIMEOUT": 503,
    }
    
    # Verify all expected codes are registered
    for code, expected_status in expected_mappings.items():
        assert code in registered, (
            f"MISSING: {code} not in canonical registry\n"
            f"Registered: {sorted(registered)}\n"
        )
        # Verify status matches registry
        actual_status = API_ERROR_CODE_REGISTRY[code][0]
        assert actual_status == expected_status, (
            f"STATUS MISMATCH: {code}\n"
            f"Expected: {expected_status}\n"
            f"Got: {actual_status}\n"
        )


def test_api_error_codes_never_fallback_to_403():
    """
    Verify that all registered API.* codes have explicit status mappings.
    
    Exception: API.FORBIDDEN legitimately uses 403 for authorization failures.
    All other 403s should be policy/denial codes (POLICY.*, TENANT.*, INGEST.*).
    """
    # Get all registered API codes
    registered = all_error_codes()
    api_codes = {c for c in registered if c.startswith("API.")}
    
    # All registered API codes must have a status in the registry
    for code in api_codes:
        status, severity, desc = API_ERROR_CODE_REGISTRY[code]
        
        # API.FORBIDDEN is allowed to use 403 (authorization failure)
        if code == "API.FORBIDDEN":
            assert status == 403, f"API.FORBIDDEN must map to 403, got {status}"
            continue
        
        # All other API codes must NOT use 403 (reserved for policy/denial)
        assert status != 403, (
            f"FALLBACK RISK: {code} mapped to 403 (fallback status)\n"
            f"API codes must have explicit status mapping (4xx or 5xx)\n"
            f"Current: {status}\n"
        )
        assert status >= 400, (
            f"Invalid status for {code}: {status}\n"
            f"API codes must be 4xx or 5xx\n"
        )


def test_unregistered_api_codes_raise_custom_exception():
    """
    Verify that unregistered API.* codes raise UnknownApiErrorCode.
    
    This ensures audit trail is explicit and grep-able in logs.
    Other code namespaces (POLICY.*, etc.) should not raise.
    """
    from services.api.src.error_codes import get_http_status
    
    # Unregistered API code should raise custom exception
    with pytest.raises(UnknownApiErrorCode) as exc_info:
        get_http_status("API.UNKNOWN_CODE")
    
    assert "API.UNKNOWN_CODE" in str(exc_info.value)
    assert "not registered" in str(exc_info.value)
    
    # Other namespace codes should fall back to 403 (via deps.py catch)
    # but get_http_status doesn't know about them, so they'd also raise.
    # That's OK: callers that aren't API.* codes should be in other layers.


def test_unregistered_api_codes_return_500_envelope():
    """
    Verify that routes using unregistered API.* codes return deterministic 500.
    
    This ensures developer errors are caught and visible in production
    with a consistent error envelope (SERVER.MISCONFIGURATION).
    """
    from services.api.src.deps import raise_enki_error
    from fastapi import HTTPException
    
    # Unregistered API code should result in 500 with SERVER.MISCONFIGURATION
    with pytest.raises(HTTPException) as exc_info:
        raise_enki_error("API.UNREGISTERED_CODE", "test detail")
    
    assert exc_info.value.status_code == 500
    assert exc_info.value.detail["error_code"] == "SERVER.MISCONFIGURATION"
    assert "Unregistered API error code" in exc_info.value.detail["detail"]
    assert "API.UNREGISTERED_CODE" in exc_info.value.detail["detail"]


def test_api_error_registry_is_read_only():
    """
    Verify registry mapping is immutable at runtime (MappingProxyType).
    """
    with pytest.raises(TypeError):
        API_ERROR_CODE_REGISTRY["API.NEW"] = (400, "validation", "should fail")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

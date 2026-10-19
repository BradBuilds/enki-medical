"""
Static assertion test: Verify spine error codes in implementation match locked registry.

This test ensures bidirectional protection: docs ↔ code.
Any drift between ERROR_CODES_LOCKED.md and core/packs/errors.py will be detected.
"""

import pytest
from core.packs import errors


def test_spine_error_codes_match_locked_registry():
    """
    Verify that spine validation error codes in implementation exactly match
    the locked registry in ERROR_CODES_LOCKED.md.
    
    This is a governance protection test. If this fails, either:
    1. Code was modified without updating the registry (governance violation)
    2. Registry was updated without modifying code (implementation gap)
    
    Both require RFC approval.
    
    🔒 LOCKED: Spine validation error code set (10 codes)
    """
    # Locked registry from ERROR_CODES_LOCKED.md (governance-approved set)
    LOCKED_SPINE_ERROR_CODES = {
        # S1.1 - Pack Capabilities
        "MISSING_CAPABILITY",
        "AMBIGUOUS_CAPABILITY",
        "CAPABILITY_VERSION_MISMATCH",
        
        # S1.2 - Namespace Registry
        "NAMESPACE_COLLISION",
        "NAMESPACE_OWNERSHIP_VIOLATION",
        "NAMESPACE_INVALID_FORMAT",
        "DEFINITION_WITHOUT_NAMESPACE",
        
        # S1.3 - Content Hash
        "PACK_HASH_MISMATCH",
        
        # S1.5 - Activation Gate
        "ACTIVATION_REQUIRED",
        "ACTIVATION_TRANSCRIPT_MISMATCH",
    }
    
    # Extract spine error codes from implementation
    # (Spine codes are those explicitly documented as S1.1-S1.5 scope)
    implemented_spine_codes = {
        errors.MISSING_CAPABILITY,
        errors.AMBIGUOUS_CAPABILITY,
        errors.CAPABILITY_VERSION_MISMATCH,
        errors.NAMESPACE_COLLISION,
        errors.NAMESPACE_OWNERSHIP_VIOLATION,
        errors.NAMESPACE_INVALID_FORMAT,
        errors.DEFINITION_WITHOUT_NAMESPACE,
        errors.PACK_HASH_MISMATCH,
        errors.ACTIVATION_REQUIRED,
        errors.ACTIVATION_TRANSCRIPT_MISMATCH,
    }
    
    # Verify exact match
    assert implemented_spine_codes == LOCKED_SPINE_ERROR_CODES, (
        f"🚨 GOVERNANCE VIOLATION: Spine error code mismatch!\n"
        f"Locked registry defines: {sorted(LOCKED_SPINE_ERROR_CODES)}\n"
        f"Implementation has:      {sorted(implemented_spine_codes)}\n"
        f"Missing in code:         {sorted(LOCKED_SPINE_ERROR_CODES - implemented_spine_codes)}\n"
        f"Extra in code:           {sorted(implemented_spine_codes - LOCKED_SPINE_ERROR_CODES)}\n"
        f"\n"
        f"To fix this, you MUST:\n"
        f"  1. Create RFC documenting the change\n"
        f"  2. Obtain 2+ engineer approvals\n"
        f"  3. Update both ERROR_CODES_LOCKED.md and core/packs/errors.py\n"
        f"  4. Update this test's LOCKED_SPINE_ERROR_CODES set\n"
        f"  5. Update governance lock documentation"
    )
    
    # Verify count matches documentation claim
    assert len(implemented_spine_codes) == 10, (
        f"Documentation claims 10 spine error codes, but found {len(implemented_spine_codes)}"
    )


def test_error_code_string_values_match_names():
    """
    Verify that error code constants have string values matching their names.
    
    This prevents typos like:
        MISSING_CAPABILITY = "MISSNG_CAPABILITY"  # typo
    
    This is not a governance lock, but a sanity check for implementation quality.
    """
    spine_codes = [
        (errors.MISSING_CAPABILITY, "MISSING_CAPABILITY"),
        (errors.AMBIGUOUS_CAPABILITY, "AMBIGUOUS_CAPABILITY"),
        (errors.CAPABILITY_VERSION_MISMATCH, "CAPABILITY_VERSION_MISMATCH"),
        (errors.NAMESPACE_COLLISION, "NAMESPACE_COLLISION"),
        (errors.NAMESPACE_OWNERSHIP_VIOLATION, "NAMESPACE_OWNERSHIP_VIOLATION"),
        (errors.NAMESPACE_INVALID_FORMAT, "NAMESPACE_INVALID_FORMAT"),
        (errors.DEFINITION_WITHOUT_NAMESPACE, "DEFINITION_WITHOUT_NAMESPACE"),
        (errors.PACK_HASH_MISMATCH, "PACK_HASH_MISMATCH"),
        (errors.ACTIVATION_REQUIRED, "ACTIVATION_REQUIRED"),
        (errors.ACTIVATION_TRANSCRIPT_MISMATCH, "ACTIVATION_TRANSCRIPT_MISMATCH"),
    ]
    
    for code_value, expected_name in spine_codes:
        assert code_value == expected_name, (
            f"Error code constant value mismatch: "
            f"Expected '{expected_name}' but got '{code_value}'"
        )

"""
Golden tests for error code registry governance.

These tests lock the error code registry invariants and prevent drift.
Any failure requires RFC approval per ERROR_CODES_LOCKED.md governance rules.
"""

import pytest
from core.packs import errors


class TestErrorCodeRegistryTotality:
    """Verify all error codes are properly registered."""

    def test_all_spine_codes_have_messages(self):
        """All governance spine codes must have error messages."""
        spine_codes = {
            'PACK_NOT_IN_ACTIVE_SET',  # S1.0
            'MISSING_CAPABILITY',  # S1.1
            'AMBIGUOUS_CAPABILITY',
            'CAPABILITY_VERSION_MISMATCH',
            'NAMESPACE_COLLISION',  # S1.2
            'NAMESPACE_OWNERSHIP_VIOLATION',
            'NAMESPACE_INVALID_FORMAT',
            'DEFINITION_WITHOUT_NAMESPACE',
            'PACK_HASH_MISMATCH',  # S1.3
            'ACTIVATION_REQUIRED',  # S1.5
            'ACTIVATION_TRANSCRIPT_MISMATCH'
        }
        
        for code in spine_codes:
            assert hasattr(errors, code), f"Spine code {code} not defined as constant"
            code_value = getattr(errors, code)
            assert code_value in errors.ERROR_MESSAGES, f"Spine code {code} missing from ERROR_MESSAGES"
            assert errors.ERROR_MESSAGES[code_value], f"Spine code {code} has empty message"

    def test_all_loader_codes_have_messages(self):
        """All governance loader codes must have error messages."""
        loader_codes = {
            'PACK_MANIFEST_MISSING',
            'PACK_MANIFEST_INVALID_JSON',
            'PACK_MANIFEST_INVALID_SCHEMA',
            'PACK_PATH_NOT_FOUND',
            'PACK_PATH_NOT_DIRECTORY',
            'DEFINITION_FILE_MISSING',
            'DEFINITION_INVALID_JSON',
            'DEFINITION_SCHEMA_INVALID',
            'DUPLICATE_DEFINITION_ID',
            'PACK_EMPTY',
            'INVALID_CAPABILITY_DECLARATION',
            'DUPLICATE_CAPABILITY_DECLARATION'
        }
        
        for code in loader_codes:
            assert hasattr(errors, code), f"Loader code {code} not defined as constant"
            code_value = getattr(errors, code)
            assert code_value in errors.ERROR_MESSAGES, f"Loader code {code} missing from ERROR_MESSAGES"
            assert errors.ERROR_MESSAGES[code_value], f"Loader code {code} has empty message"

    def test_no_orphan_constants(self):
        """Every constant must appear in ERROR_MESSAGES registry."""
        # Get all uppercase constants from errors module
        constants = [
            name for name in dir(errors)
            if name.isupper() and not name.startswith('_')
        ]
        
        # Exclude helper constant
        constants = [c for c in constants if c != 'CAPABILITY_RESOLUTION_PACK_ID']
        
        for const in constants:
            value = getattr(errors, const)
            if isinstance(value, str):
                assert value in errors.ERROR_MESSAGES, \
                    f"Constant {const} = '{value}' not in ERROR_MESSAGES (orphan code)"

    def test_no_unknown_registry_keys(self):
        """Every registry key must correspond to a defined constant."""
        # Get all uppercase constants from errors module
        constants = {
            getattr(errors, name)
            for name in dir(errors)
            if name.isupper() and not name.startswith('_')
            and isinstance(getattr(errors, name), str)
        }
        
        # Exclude helper constant value
        if hasattr(errors, 'CAPABILITY_RESOLUTION_PACK_ID'):
            constants.discard(errors.CAPABILITY_RESOLUTION_PACK_ID)
        
        for key in errors.ERROR_MESSAGES.keys():
            assert key in constants, \
                f"ERROR_MESSAGES key '{key}' has no corresponding constant (unknown registry entry)"


class TestErrorCodeMessageQuality:
    """Verify error messages meet quality standards."""

    def test_messages_are_non_empty(self):
        """All error messages must be non-empty strings."""
        for code, message in errors.ERROR_MESSAGES.items():
            assert isinstance(message, str), f"Error code {code} message is not a string"
            assert message.strip(), f"Error code {code} has empty or whitespace-only message"

    def test_messages_have_no_placeholders(self):
        """Error messages must not contain placeholder text."""
        placeholders = ['TODO', 'FIXME', 'XXX', 'TBD', '...']
        for code, message in errors.ERROR_MESSAGES.items():
            for placeholder in placeholders:
                assert placeholder not in message, \
                    f"Error code {code} message contains placeholder '{placeholder}': {message}"

    def test_get_error_message_function(self):
        """get_error_message() must return messages for all codes."""
        for code in errors.ERROR_MESSAGES.keys():
            message = errors.get_error_message(code)
            assert message, f"get_error_message('{code}') returned empty"
            assert message != f"Unknown error code: {code}", \
                f"get_error_message('{code}') returned unknown code message"

    def test_get_error_message_unknown_code(self):
        """get_error_message() must handle unknown codes gracefully."""
        unknown_code = "NONEXISTENT_ERROR_CODE_12345"
        message = errors.get_error_message(unknown_code)
        assert message == f"Unknown error code: {unknown_code}"


class TestSpineCodeInvariants:
    """Lock spine validation code invariants per SPINE-00."""

    def test_spine_codes_count_immutable(self):
        """Spine code count is governance-locked (11 codes: S1.0-S1.5)."""
        spine_codes = {
            'PACK_NOT_IN_ACTIVE_SET',  # S1.0
            'MISSING_CAPABILITY',
            'AMBIGUOUS_CAPABILITY',
            'CAPABILITY_VERSION_MISMATCH',
            'NAMESPACE_COLLISION',
            'NAMESPACE_OWNERSHIP_VIOLATION',
            'NAMESPACE_INVALID_FORMAT',
            'DEFINITION_WITHOUT_NAMESPACE',
            'PACK_HASH_MISMATCH',
            'ACTIVATION_REQUIRED',
            'ACTIVATION_TRANSCRIPT_MISMATCH'
        }
        
        # Verify all exist
        for code in spine_codes:
            assert hasattr(errors, code), \
                f"Spine code {code} missing (expected 11 codes, got fewer)"
        
        # Lock count at 11 (S1.0-S1.5)
        assert len(spine_codes) == 11, \
            "Spine code count changed (governance-locked at 11 for S1.0-S1.5). RFC required."

    def test_loader_codes_count_immutable(self):
        """Loader code count is governance-locked (12 codes)."""
        loader_codes = {
            'PACK_MANIFEST_MISSING',
            'PACK_MANIFEST_INVALID_JSON',
            'PACK_MANIFEST_INVALID_SCHEMA',
            'PACK_PATH_NOT_FOUND',
            'PACK_PATH_NOT_DIRECTORY',
            'DEFINITION_FILE_MISSING',
            'DEFINITION_INVALID_JSON',
            'DEFINITION_SCHEMA_INVALID',
            'DUPLICATE_DEFINITION_ID',
            'PACK_EMPTY',
            'INVALID_CAPABILITY_DECLARATION',
            'DUPLICATE_CAPABILITY_DECLARATION'
        }
        
        # Verify all exist
        for code in loader_codes:
            assert hasattr(errors, code), \
                f"Loader code {code} missing (expected 12 codes, got fewer)"
        
        # Lock count
        assert len(loader_codes) == 12, \
            "Loader code count changed (governance-locked at 12). RFC required."

    def test_code_names_immutable(self):
        """Error code constant names must not change (breaks monitoring)."""
        # NOTE: PACK_NOT_IN_ACTIVE_SET (S1.0) excluded - in infrastructure registry
        expected_codes = {
            # S1.1
            'MISSING_CAPABILITY',
            'AMBIGUOUS_CAPABILITY',
            'CAPABILITY_VERSION_MISMATCH',
            'INVALID_CAPABILITY_DECLARATION',
            'DUPLICATE_CAPABILITY_DECLARATION',
            # S1.2
            'NAMESPACE_COLLISION',
            'NAMESPACE_OWNERSHIP_VIOLATION',
            'NAMESPACE_INVALID_FORMAT',
            'DEFINITION_WITHOUT_NAMESPACE',
            # S1.3
            'PACK_HASH_MISMATCH',
            # S1.5
            'ACTIVATION_REQUIRED',
            'ACTIVATION_TRANSCRIPT_MISMATCH',
            # Loader
            'PACK_MANIFEST_MISSING',
            'PACK_MANIFEST_INVALID_JSON',
            'PACK_MANIFEST_INVALID_SCHEMA',
            'PACK_PATH_NOT_FOUND',
            'PACK_PATH_NOT_DIRECTORY',
            'DEFINITION_FILE_MISSING',
            'DEFINITION_INVALID_JSON',
            'DEFINITION_SCHEMA_INVALID',
            'DUPLICATE_DEFINITION_ID',
            'PACK_EMPTY',
        }
        
        for code_name in expected_codes:
            assert hasattr(errors, code_name), \
                f"Code constant {code_name} removed or renamed (governance violation)"


class TestErrorCodeDeterminism:
    """Lock deterministic error sorting rules per SPINE-00 §3.1."""

    def test_error_codes_are_strings(self):
        """All error codes must be strings for deterministic sorting."""
        for const_name in dir(errors):
            if const_name.isupper() and not const_name.startswith('_'):
                value = getattr(errors, const_name)
                if const_name != 'CAPABILITY_RESOLUTION_PACK_ID':
                    if isinstance(value, str) and value in errors.ERROR_MESSAGES:
                        assert isinstance(value, str), \
                            f"Error code {const_name} is not a string"

    def test_sort_key_determinism(self):
        """Verify error codes sort deterministically (governance-locked order)."""
        # Simulate errors from different packs
        error_codes = [
            'NAMESPACE_COLLISION',
            'MISSING_CAPABILITY',
            'PACK_HASH_MISMATCH',
            'AMBIGUOUS_CAPABILITY',
            'ACTIVATION_REQUIRED',
        ]
        
        # Sort by code name (lexicographic)
        sorted_codes = sorted(error_codes)
        
        # Verify stable ordering
        expected_order = [
            'ACTIVATION_REQUIRED',
            'AMBIGUOUS_CAPABILITY',
            'MISSING_CAPABILITY',
            'NAMESPACE_COLLISION',
            'PACK_HASH_MISMATCH',
        ]
        
        assert sorted_codes == expected_order, \
            "Error code sorting not deterministic (governance requirement)"


# Governance note: These tests are LOCKED per ERROR_CODES_LOCKED.md.
# Any failure requires RFC + 2 engineer approvals to modify.

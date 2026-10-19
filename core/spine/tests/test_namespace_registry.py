"""
ENKI Spine S1.2 — Namespace Registry Tests

Tests for namespace ownership validation and collision detection.
Per SPINE-EXECUTION-PLAN S1.2 (13 minimum test cases)
"""

import pytest
from core.spine.namespace_registry import (
    validate_namespace_declarations,
    detect_namespace_collisions,
    verify_definition_ownership,
    NamespaceError
)


class TestNamespaceDeclarationValidation:
    """Test namespace format validation."""
    
    def test_valid_single_namespace(self):
        """Test case 1: Valid single namespace claim."""
        errors = validate_namespace_declarations("test_pack", ["audit"])
        assert len(errors) == 0
    
    def test_valid_nested_namespace(self):
        """Test case 2: Valid nested namespace claim."""
        errors = validate_namespace_declarations("test_pack", ["identity.actor"])
        assert len(errors) == 0
    
    def test_multiple_namespaces(self):
        """Test case 3: Multiple namespace claims."""
        errors = validate_namespace_declarations("test_pack", ["audit", "identity"])
        assert len(errors) == 0
    
    def test_invalid_uppercase(self):
        """Test case 10: Invalid namespace format (uppercase)."""
        errors = validate_namespace_declarations("test_pack", ["Audit"])
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_INVALID_FORMAT"
        assert errors[0].context["pack_id"] == "test_pack"
        assert errors[0].context["namespace"] == "Audit"
    
    def test_invalid_underscore(self):
        """Test case 11: Invalid namespace format (underscore)."""
        errors = validate_namespace_declarations("test_pack", ["audit_event"])
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_INVALID_FORMAT"
        assert errors[0].context["namespace"] == "audit_event"
    
    def test_empty_namespace_array(self):
        """Test case 12: Empty namespace array (valid - no claims)."""
        errors = validate_namespace_declarations("test_pack", [])
        assert len(errors) == 0
    
    def test_none_namespace_array(self):
        """Test case 12 variant: None namespace array (valid - no claims)."""
        errors = validate_namespace_declarations("test_pack", None)
        assert len(errors) == 0
    
    def test_invalid_namespace_type(self):
        """Additional: Invalid namespace type."""
        errors = validate_namespace_declarations("test_pack", [123, "audit"])
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_INVALID_FORMAT"
        assert "123" in errors[0].context["namespace"]


class TestNamespaceCollisionDetection:
    """Test cross-pack namespace collision detection."""
    
    def test_exact_collision(self):
        """Test case 4: Exact namespace collision."""
        packs = {
            "pack_a": ["audit"],
            "pack_b": ["audit"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_COLLISION"
        assert errors[0].context["pack_id"] == "pack_a"
        assert errors[0].context["namespace"] == "audit"
        assert errors[0].context["conflicting_pack_id"] == "pack_b"
        assert errors[0].context["conflicting_namespace"] == "audit"
    
    def test_prefix_collision(self):
        """Test case 5: Prefix namespace collision."""
        packs = {
            "pack_a": ["audit"],
            "pack_b": ["audit.event"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_COLLISION"
    
    def test_reverse_prefix_collision(self):
        """Test case 6: Reverse prefix collision."""
        packs = {
            "pack_a": ["audit.event"],
            "pack_b": ["audit"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_COLLISION"
    
    def test_non_overlapping_namespaces(self):
        """Test case 7: Non-overlapping namespaces (no collision)."""
        packs = {
            "pack_a": ["audit"],
            "pack_b": ["identity"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 0
    
    def test_empty_namespace_no_collision(self):
        """Test: Empty namespaces don't cause collisions."""
        packs = {
            "pack_a": ["audit"],
            "pack_b": [],
            "pack_c": ["identity"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 0
    
    def test_deterministic_ordering(self):
        """Test case 13: Deterministic error ordering."""
        packs = {
            "pack_z": ["audit"],
            "pack_a": ["audit"],
            "pack_m": ["identity"],
            "pack_b": ["identity"]
        }
        errors = detect_namespace_collisions(packs)
        assert len(errors) == 2
        
        # Errors should be sorted deterministically
        # Check first error is for the alphabetically first pack pair
        assert errors[0].context["pack_id"] == "pack_a"
        assert errors[0].context["conflicting_pack_id"] == "pack_z"
        assert errors[1].context["pack_id"] == "pack_b"
        assert errors[1].context["conflicting_pack_id"] == "pack_m"


class TestDefinitionOwnership:
    """Test definition ownership verification."""
    
    def test_definition_matches_owned_namespace(self):
        """Test case 1: Definition matches owned namespace."""
        errors = verify_definition_ownership(
            "test_pack",
            ["audit"],
            ["audit.alert"]
        )
        assert len(errors) == 0
    
    def test_nested_definition_matches(self):
        """Test case 2: Nested definition matches owned namespace."""
        errors = verify_definition_ownership(
            "test_pack",
            ["identity.actor"],
            ["identity.actor.user"]
        )
        assert len(errors) == 0
    
    def test_multiple_definitions_match(self):
        """Test case 3: Multiple definitions match multiple namespaces."""
        errors = verify_definition_ownership(
            "test_pack",
            ["audit", "identity"],
            ["audit.alert", "identity.user", "audit.event"]
        )
        assert len(errors) == 0
    
    def test_definition_outside_namespace(self):
        """Test case 8: Definition outside owned namespace."""
        errors = verify_definition_ownership(
            "test_pack",
            ["audit"],
            ["identity.user"]
        )
        assert len(errors) == 1
        assert errors[0].code == "NAMESPACE_OWNERSHIP_VIOLATION"
        assert errors[0].context["pack_id"] == "test_pack"
        assert errors[0].context["definition_id"] == "identity.user"
        assert errors[0].context["owned_namespaces"] == ["audit"]
    
    def test_definition_without_namespace(self):
        """Test case 9: Definition without any namespace ownership."""
        errors = verify_definition_ownership(
            "test_pack",
            [],
            ["audit.alert"]
        )
        assert len(errors) == 1
        assert errors[0].code == "DEFINITION_WITHOUT_NAMESPACE"
        assert errors[0].context["pack_id"] == "test_pack"
        assert errors[0].context["definition_id"] == "audit.alert"
    
    def test_definition_without_namespace_none(self):
        """Test case 9 variant: None namespace with definitions."""
        errors = verify_definition_ownership(
            "test_pack",
            None,
            ["audit.alert"]
        )
        assert len(errors) == 1
        assert errors[0].code == "DEFINITION_WITHOUT_NAMESPACE"
    
    def test_no_definitions_no_error(self):
        """Test: No definitions means no ownership errors."""
        errors = verify_definition_ownership(
            "test_pack",
            [],
            []
        )
        assert len(errors) == 0
    
    def test_exact_match_allowed(self):
        """Test: Definition ID exactly matches namespace."""
        errors = verify_definition_ownership(
            "test_pack",
            ["audit"],
            ["audit"]
        )
        assert len(errors) == 0
    
    def test_deterministic_ordering_ownership(self):
        """Test case 13 variant: Deterministic error ordering for ownership."""
        errors = verify_definition_ownership(
            "test_pack",
            ["owned"],
            ["zebra.def", "alpha.def", "beta.def"]
        )
        assert len(errors) == 3
        # Should be sorted by definition_id
        assert errors[0].context["definition_id"] == "alpha.def"
        assert errors[1].context["definition_id"] == "beta.def"
        assert errors[2].context["definition_id"] == "zebra.def"


class TestIntegration:
    """Integration tests combining multiple validation steps."""
    
    def test_full_validation_pipeline(self):
        """Test complete validation: format, collision, ownership."""
        # Step 1: Validate declarations
        errors_a = validate_namespace_declarations("pack_a", ["audit"])
        errors_b = validate_namespace_declarations("pack_b", ["identity"])
        assert len(errors_a) == 0
        assert len(errors_b) == 0
        
        # Step 2: Check collisions
        packs = {
            "pack_a": ["audit"],
            "pack_b": ["identity"]
        }
        collision_errors = detect_namespace_collisions(packs)
        assert len(collision_errors) == 0
        
        # Step 3: Verify ownership
        ownership_errors_a = verify_definition_ownership(
            "pack_a", ["audit"], ["audit.alert", "audit.event"]
        )
        ownership_errors_b = verify_definition_ownership(
            "pack_b", ["identity"], ["identity.user"]
        )
        assert len(ownership_errors_a) == 0
        assert len(ownership_errors_b) == 0
    
    def test_pipeline_with_violations(self):
        """Test pipeline catches all violation types."""
        # Invalid format
        format_errors = validate_namespace_declarations("pack_bad", ["Bad_Format"])
        assert len(format_errors) == 1
        assert format_errors[0].code == "NAMESPACE_INVALID_FORMAT"
        
        # Collision
        packs = {
            "pack_a": ["audit"],
            "pack_b": ["audit"]
        }
        collision_errors = detect_namespace_collisions(packs)
        assert len(collision_errors) == 1
        assert collision_errors[0].code == "NAMESPACE_COLLISION"
        
        # Ownership violation
        ownership_errors = verify_definition_ownership(
            "pack_a", ["audit"], ["identity.user"]
        )
        assert len(ownership_errors) == 1
        assert ownership_errors[0].code == "NAMESPACE_OWNERSHIP_VIOLATION"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

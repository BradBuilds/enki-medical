"""
Tests for ENKI Semantic Version Comparison

Authority: GDU Technical Build Plan v2.4.0 §SEMVER COMPARISON SPECIFICATION
"""

import pytest
from core.spine.semver import SemanticVersion


class TestSemanticVersionParsing:
    """Test semver parsing from strings."""
    
    def test_parse_valid_versions(self):
        """Parse valid semver strings."""
        v1 = SemanticVersion.parse("1.2.3")
        assert v1.to_tuple() == (1, 2, 3)
        assert v1.major == 1
        assert v1.minor == 2
        assert v1.patch == 3
        
        v2 = SemanticVersion.parse("0.0.1")
        assert v2.to_tuple() == (0, 0, 1)
        
        v3 = SemanticVersion.parse("10.20.30")
        assert v3.to_tuple() == (10, 20, 30)
    
    def test_parse_invalid_missing_patch(self):
        """Reject version missing patch number."""
        with pytest.raises(ValueError, match="must be <major>.<minor>.<patch>"):
            SemanticVersion.parse("1.2")
    
    def test_parse_invalid_prerelease(self):
        """Reject version with pre-release suffix."""
        with pytest.raises(ValueError, match="pre-release/build metadata not allowed"):
            SemanticVersion.parse("1.2.3-alpha")
    
    def test_parse_invalid_build_metadata(self):
        """Reject version with build metadata."""
        with pytest.raises(ValueError, match="pre-release/build metadata not allowed"):
            SemanticVersion.parse("1.2.3+build.123")
    
    def test_parse_invalid_empty(self):
        """Reject empty version string."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SemanticVersion.parse("")
    
    def test_parse_invalid_non_numeric(self):
        """Reject non-numeric components."""
        with pytest.raises(ValueError, match="must be <major>.<minor>.<patch>"):
            SemanticVersion.parse("1.2.x")


class TestSemanticVersionComparisons:
    """Test semver comparison operators."""
    
    def test_less_than(self):
        """Test < operator."""
        assert SemanticVersion.parse("1.0.0") < SemanticVersion.parse("2.0.0")
        assert SemanticVersion.parse("1.0.0") < SemanticVersion.parse("1.1.0")
        assert SemanticVersion.parse("1.0.0") < SemanticVersion.parse("1.0.1")
        
        # Not less than
        assert not (SemanticVersion.parse("2.0.0") < SemanticVersion.parse("1.0.0"))
        assert not (SemanticVersion.parse("1.0.0") < SemanticVersion.parse("1.0.0"))
    
    def test_less_than_or_equal(self):
        """Test <= operator."""
        assert SemanticVersion.parse("1.0.0") <= SemanticVersion.parse("2.0.0")
        assert SemanticVersion.parse("1.0.0") <= SemanticVersion.parse("1.0.0")
        
        # Not less than or equal
        assert not (SemanticVersion.parse("2.0.0") <= SemanticVersion.parse("1.0.0"))
    
    def test_greater_than(self):
        """Test > operator."""
        assert SemanticVersion.parse("2.0.0") > SemanticVersion.parse("1.0.0")
        assert SemanticVersion.parse("1.1.0") > SemanticVersion.parse("1.0.0")
        assert SemanticVersion.parse("1.0.1") > SemanticVersion.parse("1.0.0")
        
        # Not greater than
        assert not (SemanticVersion.parse("1.0.0") > SemanticVersion.parse("2.0.0"))
        assert not (SemanticVersion.parse("1.0.0") > SemanticVersion.parse("1.0.0"))
    
    def test_greater_than_or_equal(self):
        """Test >= operator."""
        assert SemanticVersion.parse("2.0.0") >= SemanticVersion.parse("1.0.0")
        assert SemanticVersion.parse("1.0.0") >= SemanticVersion.parse("1.0.0")
        assert SemanticVersion.parse("1.0.1") >= SemanticVersion.parse("1.0.0")
        
        # Not greater than or equal
        assert not (SemanticVersion.parse("1.0.0") >= SemanticVersion.parse("2.0.0"))
    
    def test_equality(self):
        """Test == operator."""
        assert SemanticVersion.parse("1.0.0") == SemanticVersion.parse("1.0.0")
        assert SemanticVersion.parse("1.2.3") == SemanticVersion.parse("1.2.3")
        
        # Not equal
        assert not (SemanticVersion.parse("1.0.0") == SemanticVersion.parse("2.0.0"))
        assert not (SemanticVersion.parse("1.0.0") == SemanticVersion.parse("1.0.1"))
    
    def test_inequality(self):
        """Test != operator."""
        assert SemanticVersion.parse("1.0.0") != SemanticVersion.parse("2.0.0")
        assert SemanticVersion.parse("1.0.0") != SemanticVersion.parse("1.0.1")
        
        # Equal (not inequal)
        assert not (SemanticVersion.parse("1.0.0") != SemanticVersion.parse("1.0.0"))
    
    def test_monotonicity_check(self):
        """Test V' > V (strictly greater) for monotonicity enforcement."""
        old_ver = SemanticVersion.parse("1.0.0")
        
        # Valid upgrades (strictly greater)
        assert SemanticVersion.parse("2.0.0") > old_ver
        assert SemanticVersion.parse("1.1.0") > old_ver
        assert SemanticVersion.parse("1.0.1") > old_ver
        
        # Invalid: same version (monotonicity violation)
        assert not (SemanticVersion.parse("1.0.0") > old_ver)
        
        # Invalid: downgrade (monotonicity violation)
        assert not (SemanticVersion.parse("0.9.9") > old_ver)


class TestSemanticVersionString:
    """Test string representation."""
    
    def test_str(self):
        """Test __str__ returns correct format."""
        v = SemanticVersion.parse("1.2.3")
        assert str(v) == "1.2.3"
        
        v2 = SemanticVersion.parse("10.20.30")
        assert str(v2) == "10.20.30"


class TestSemanticVersionImmutability:
    """Test that SemanticVersion is immutable (frozen dataclass)."""
    
    def test_cannot_modify_major(self):
        """Cannot modify major version after creation."""
        v = SemanticVersion.parse("1.2.3")
        with pytest.raises(AttributeError):
            v.major = 2
    
    def test_cannot_modify_minor(self):
        """Cannot modify minor version after creation."""
        v = SemanticVersion.parse("1.2.3")
        with pytest.raises(AttributeError):
            v.minor = 3
    
    def test_cannot_modify_patch(self):
        """Cannot modify patch version after creation."""
        v = SemanticVersion.parse("1.2.3")
        with pytest.raises(AttributeError):
            v.patch = 4


class TestSemanticVersionHashability:
    """Test that SemanticVersion can be used in sets/dicts."""
    
    def test_hashable(self):
        """SemanticVersion is hashable (can be used in sets)."""
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("2.0.0")
        v3 = SemanticVersion.parse("1.0.0")  # Duplicate
        
        version_set = {v1, v2, v3}
        assert len(version_set) == 2  # v1 and v3 are equal, so only 2 unique
        assert v1 in version_set
        assert v2 in version_set
    
    def test_dict_keys(self):
        """SemanticVersion can be used as dict keys."""
        version_dict = {
            SemanticVersion.parse("1.0.0"): "stable",
            SemanticVersion.parse("2.0.0"): "latest"
        }
        
        assert version_dict[SemanticVersion.parse("1.0.0")] == "stable"
        assert version_dict[SemanticVersion.parse("2.0.0")] == "latest"

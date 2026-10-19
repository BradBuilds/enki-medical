"""
ENKI Validation Tests

Tests for schema and semantic validation.

Author: ENKI System
Version: 0.1.0
"""

import pytest
import sys
from pathlib import Path

# Add core validation to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "core"))

from validation import (
    validate_definition,
    validate_registry_pack,
    validate_base60_digit,
    validate_base60_places,
    validate_conversion_correctness
)


class TestSchemaValidation:
    """Tests for schema validation."""
    
    def test_validate_base60_pack(self):
        """Base-60 pack validates correctly."""
        base_dir = Path(__file__).parent.parent.parent.parent
        pack_dir = base_dir / "libraries" / "base60"
        
        if pack_dir.exists():
            result = validate_registry_pack(str(pack_dir))
            
            # Print any errors or warnings
            if result["errors"]:
                print("\nValidation errors:")
                for err in result["errors"]:
                    print(f"  - {err}")
            
            if result["warnings"]:
                print("\nValidation warnings:")
                for warn in result["warnings"]:
                    print(f"  - {warn}")
            
            # Should pass validation
            assert result["ok"] is True


class TestSemanticValidation:
    """Tests for semantic validation."""
    
    def test_digit_validation(self):
        """Digit validation works correctly."""
        # Valid digits
        assert validate_base60_digit(0)["ok"]
        assert validate_base60_digit(30)["ok"]
        assert validate_base60_digit(59)["ok"]
        
        # Invalid digits
        assert not validate_base60_digit(-1)["ok"]
        assert not validate_base60_digit(60)["ok"]
        assert not validate_base60_digit(3.14)["ok"]
    
    def test_places_validation(self):
        """Places validation works correctly."""
        # Valid places
        assert validate_base60_places([1, 2, 3])["ok"]
        assert validate_base60_places([0])["ok"]
        
        # Invalid places
        assert not validate_base60_places([])["ok"]
        assert not validate_base60_places([1, None, 3])["ok"]
        assert not validate_base60_places([1, 60, 3])["ok"]
    
    def test_conversion_validation(self):
        """Conversion validation works correctly."""
        # Correct conversions
        result = validate_conversion_correctness(3723, [1, 2, 3])
        assert result["ok"]
        assert result["expected_decimal"] == 3723
        
        # Incorrect conversion
        result = validate_conversion_correctness(3723, [1, 2, 4])
        assert not result["ok"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

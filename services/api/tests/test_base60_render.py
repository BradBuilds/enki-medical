"""
ENKI Base-60 Rendering Tests

Tests for deterministic glyph rendering.

Test Philosophy:
- No randomness
- No global state
- No time dependency
- Deterministic output verification

Author: ENKI System
Version: 0.1.0
"""

import pytest
import sys
from pathlib import Path

# Add core validation to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "core"))

from validation import (
    render_digit,
    render_places,
    decimal_to_base60,
    base60_to_decimal,
    render_decimal_as_base60,
    validate_base60_digit,
    validate_base60_places,
    validate_conversion_correctness
)


class TestRenderDigit:
    """Tests for render_digit function."""
    
    def test_render_zero(self):
        """Zero renders as dedicated glyph."""
        assert render_digit(0) == "∅"
        assert render_digit(0, "wedge_unicode_modern") == "∅"
    
    def test_render_units_only(self):
        """Digits 1-9 render as unit wedges only."""
        expected_ascii = ["|", "||", "|||", "||||", "|||||", "||||||", "|||||||", "||||||||", "|||||||||"]
        for i in range(1, 10):
            assert render_digit(i, "wedge_ascii") == expected_ascii[i-1]
    
    def test_render_tens_only(self):
        """Digits 10, 20, 30, 40, 50 render as ten wedges only."""
        expected = {
            10: "<",
            20: "<<",
            30: "<<<",
            40: "<<<<",
            50: "<<<<<"
        }
        for value, glyph in expected.items():
            assert render_digit(value, "wedge_ascii") == glyph
    
    def test_render_mixed(self):
        """Digits with tens and units render both."""
        assert render_digit(11, "wedge_ascii") == "<|"
        assert render_digit(23, "wedge_ascii") == "<<|||"
        assert render_digit(45, "wedge_ascii") == "<<<<|||||"
        assert render_digit(59, "wedge_ascii") == "<<<<<|||||||||"
    
    def test_render_boundary_values(self):
        """Boundary cases: 0 and 59."""
        assert render_digit(0) == "∅"
        assert render_digit(59) == "<<<<<|||||||||"
    
    def test_render_all_digits(self):
        """All digits 0-59 render without error."""
        for i in range(60):
            result = render_digit(i)
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_invalid_digit_negative(self):
        """Negative digits raise ValueError."""
        with pytest.raises(ValueError, match="BASE60_DIGIT_RANGE"):
            render_digit(-1)
    
    def test_invalid_digit_too_large(self):
        """Digits > 59 raise ValueError."""
        with pytest.raises(ValueError, match="BASE60_DIGIT_RANGE"):
            render_digit(60)
        with pytest.raises(ValueError, match="BASE60_DIGIT_RANGE"):
            render_digit(100)
    
    def test_invalid_digit_type(self):
        """Non-integer digits raise ValueError."""
        with pytest.raises(ValueError, match="BASE60_INVALID_TYPE"):
            render_digit(3.14)
        with pytest.raises(ValueError, match="BASE60_INVALID_TYPE"):
            render_digit("42")
    
    def test_invalid_style(self):
        """Unknown style raises ValueError."""
        with pytest.raises(ValueError, match="INVALID_STYLE"):
            render_digit(10, "unknown_style")
    
    def test_unicode_style(self):
        """Unicode style renders correctly."""
        assert render_digit(0, "wedge_unicode_modern") == "∅"
        assert render_digit(1, "wedge_unicode_modern") == "𒁹"
        assert render_digit(10, "wedge_unicode_modern") == "𒌋"
        assert render_digit(11, "wedge_unicode_modern") == "𒌋𒁹"


class TestRenderPlaces:
    """Tests for render_places function."""
    
    def test_render_single_place(self):
        """Single place renders correctly."""
        assert render_places([0]) == "∅"
        assert render_places([5]) == "|||||"
        assert render_places([59]) == "<<<<<|||||||||"
    
    def test_render_multiple_places(self):
        """Multiple places render with separator."""
        assert render_places([1, 2, 3]) == "| || |||"
    
    def test_render_with_custom_separator(self):
        """Custom separator works."""
        assert render_places([1, 2, 3], separator="-") == "|-||-|||"
        assert render_places([1, 2, 3], separator="") == "||||||"
    
    def test_empty_places_raises_error(self):
        """Empty places list raises ValueError."""
        with pytest.raises(ValueError, match="BASE60_EMPTY_PLACES"):
            render_places([])
    
    def test_null_place_raises_error(self):
        """Null/None in places raises ValueError."""
        with pytest.raises(ValueError, match="BASE60_NULL_VALUE"):
            render_places([1, None, 3])
    
    def test_invalid_place_type(self):
        """Non-list places raises ValueError."""
        with pytest.raises(ValueError, match="BASE60_INVALID_TYPE"):
            render_places("123")
    
    def test_invalid_digit_in_places(self):
        """Invalid digit in places raises ValueError."""
        with pytest.raises(ValueError, match="Invalid digit at position"):
            render_places([1, 60, 3])


class TestDecimalToBase60:
    """Tests for decimal_to_base60 conversion."""
    
    def test_convert_zero(self):
        """Zero converts to [0]."""
        assert decimal_to_base60(0) == [0]
    
    def test_convert_single_digit(self):
        """Values 1-59 convert to single-place."""
        assert decimal_to_base60(1) == [1]
        assert decimal_to_base60(59) == [59]
    
    def test_convert_sixty(self):
        """60 converts to [1, 0]."""
        assert decimal_to_base60(60) == [1, 0]
    
    def test_convert_example_3723(self):
        """Example from spec: 3723 = [1, 2, 3]."""
        assert decimal_to_base60(3723) == [1, 2, 3]
    
    def test_convert_large_value(self):
        """Large values convert correctly."""
        # 3600 = 60^2 = [1, 0, 0]
        assert decimal_to_base60(3600) == [1, 0, 0]
        # 216000 = 60^3 = [1, 0, 0, 0]
        assert decimal_to_base60(216000) == [1, 0, 0, 0]
    
    def test_negative_value_raises_error(self):
        """Negative values raise ValueError."""
        with pytest.raises(ValueError, match="BASE60_NEGATIVE"):
            decimal_to_base60(-1)
    
    def test_non_integer_raises_error(self):
        """Non-integer values raise ValueError."""
        with pytest.raises(ValueError, match="BASE60_INVALID_TYPE"):
            decimal_to_base60(3.14)


class TestBase60ToDecimal:
    """Tests for base60_to_decimal conversion."""
    
    def test_convert_zero(self):
        """[0] converts to 0."""
        assert base60_to_decimal([0]) == 0
    
    def test_convert_single_digit(self):
        """Single-place values convert correctly."""
        assert base60_to_decimal([1]) == 1
        assert base60_to_decimal([59]) == 59
    
    def test_convert_sixty(self):
        """[1, 0] converts to 60."""
        assert base60_to_decimal([1, 0]) == 60
    
    def test_convert_example_3723(self):
        """Example from spec: [1, 2, 3] = 3723."""
        assert base60_to_decimal([1, 2, 3]) == 3723
    
    def test_convert_with_zeros(self):
        """Place values with zeros work correctly."""
        assert base60_to_decimal([1, 0, 0]) == 3600
        assert base60_to_decimal([2, 0, 5]) == 7205  # 2*3600 + 0*60 + 5
    
    def test_roundtrip_conversion(self):
        """Decimal → Base-60 → Decimal roundtrip."""
        test_values = [0, 1, 59, 60, 119, 3600, 3723, 10000]
        for value in test_values:
            places = decimal_to_base60(value)
            result = base60_to_decimal(places)
            assert result == value


class TestValidation:
    """Tests for validation functions."""
    
    def test_validate_digit_valid(self):
        """Valid digits pass validation."""
        for d in [0, 30, 59]:
            result = validate_base60_digit(d)
            assert result["ok"] is True
            assert len(result["errors"]) == 0
    
    def test_validate_digit_invalid(self):
        """Invalid digits fail validation."""
        result = validate_base60_digit(60)
        assert result["ok"] is False
        assert len(result["errors"]) > 0
    
    def test_validate_places_valid(self):
        """Valid places pass validation."""
        result = validate_base60_places([1, 2, 3])
        assert result["ok"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_places_invalid(self):
        """Invalid places fail validation."""
        result = validate_base60_places([1, 60, 3])
        assert result["ok"] is False
        assert len(result["errors"]) > 0
    
    def test_validate_conversion(self):
        """Conversion correctness validation works."""
        result = validate_conversion_correctness(3723, [1, 2, 3])
        assert result["ok"] is True
        assert result["expected_decimal"] == 3723
        
        # Wrong conversion
        result = validate_conversion_correctness(3723, [1, 2, 4])
        assert result["ok"] is False


class TestDeterminism:
    """Tests for deterministic behavior."""
    
    def test_same_input_same_output(self):
        """Same input always produces same output."""
        for _ in range(10):
            assert render_digit(23) == "<<|||"
            assert render_places([1, 2, 3]) == "| || |||"
            assert decimal_to_base60(3723) == [1, 2, 3]
    
    def test_no_state_dependency(self):
        """Output does not depend on previous calls."""
        # Call functions in various orders
        render_digit(10)
        render_places([5, 6])
        result1 = decimal_to_base60(3723)
        
        render_digit(50)
        decimal_to_base60(100)
        result2 = decimal_to_base60(3723)
        
        assert result1 == result2 == [1, 2, 3]


class TestFullPipeline:
    """Tests for complete rendering pipeline."""
    
    def test_render_decimal_as_base60(self):
        """Full pipeline works correctly."""
        result = render_decimal_as_base60(3723)
        assert result["decimal"] == 3723
        assert result["base60_places"] == [1, 2, 3]
        assert result["glyphs"] == "| || |||"
        assert result["style"] == "wedge_ascii"
    
    def test_render_with_different_styles(self):
        """Pipeline works with different styles."""
        result_ascii = render_decimal_as_base60(10, style="wedge_ascii")
        result_unicode = render_decimal_as_base60(10, style="wedge_unicode_modern")
        
        assert result_ascii["glyphs"] == "<"
        assert result_unicode["glyphs"] == "𒌋"
    
    def test_render_with_custom_separator(self):
        """Pipeline works with custom separator."""
        result = render_decimal_as_base60(3723, separator="|")
        assert result["glyphs"] == "||||||||"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


"""
Phase 3 Patch v1.3.2: Comprehensive RID Encoder Tests

Tests for compact RID encoding (base-55) with regression tests for IndexError bug.
"""

import pytest
from storage.ids.rid import encode_rid, decode_rid, rid_to_base60, base60_to_int, int_to_base60, ALPHABET, BASE


class TestRIDEncoderCore:
    """Core encode/decode functionality tests."""
    
    def test_alphabet_length(self):
        """Verify alphabet has 55 characters (excludes 0,O,I,l,1)."""
        assert len(ALPHABET) == 55
        assert BASE == 55
        # Verify confusables are excluded
        assert '0' not in ALPHABET
        assert 'O' not in ALPHABET
        assert 'I' not in ALPHABET
        assert 'l' not in ALPHABET
        assert '1' not in ALPHABET
    
    def test_encode_zero(self):
        """Zero encodes to first symbol '2'."""
        assert encode_rid(0) == '2'
    
    def test_encode_boundary_54(self):
        """RID 54 encodes to last symbol 'Z'."""
        assert encode_rid(54) == 'Z'
    
    def test_encode_boundary_55_regression(self):
        """
        REGRESSION TEST: RID 55 must not raise IndexError.
        
        This was the critical bug — divmod(55, 60) returned remainder 55,
        but alphabet[55] caused IndexError. With base-55, this works correctly.
        """
        result = encode_rid(55)
        assert result == '32'  # First symbol (2) followed by second symbol (3)
    
    def test_encode_100(self):
        """RID 100 encodes correctly."""
        result = encode_rid(100)
        assert isinstance(result, str)
        assert len(result) >= 1
    
    def test_encode_large_number(self):
        """Large RIDs encode without error."""
        result = encode_rid(999999)
        assert isinstance(result, str)
        assert all(c in ALPHABET for c in result)


class TestRIDDecoder:
    """Decoder functionality tests."""
    
    def test_decode_single_char(self):
        """Decode single-character RIDs."""
        assert decode_rid('2') == 0
        assert decode_rid('3') == 1
        assert decode_rid('Z') == 54
    
    def test_decode_multi_char(self):
        """Decode multi-character RIDs."""
        assert decode_rid('32') == 55
    
    def test_decode_invalid_char_raises(self):
        """Decoder rejects invalid characters."""
        with pytest.raises(ValueError, match="Invalid character"):
            decode_rid('0')  # Confusable excluded
        
        with pytest.raises(ValueError, match="Invalid character"):
            decode_rid('O')  # Confusable excluded
    
    def test_decode_empty_string_raises(self):
        """Decoder rejects empty strings."""
        with pytest.raises(ValueError, match="cannot be empty"):
            decode_rid('')


class TestRoundtrip:
    """Encode/decode roundtrip tests."""
    
    @pytest.mark.parametrize("rid_int", [
        0, 1, 2, 54, 55, 56, 100, 1000, 9999, 999999
    ])
    def test_roundtrip(self, rid_int):
        """Encode then decode returns original value."""
        encoded = encode_rid(rid_int)
        decoded = decode_rid(encoded)
        assert decoded == rid_int
    
    def test_roundtrip_all_single_char(self):
        """All single-character RIDs roundtrip correctly."""
        for i in range(55):  # 0-54 are single characters
            encoded = encode_rid(i)
            assert len(encoded) == 1
            assert decode_rid(encoded) == i


class TestBackwardCompatibility:
    """Tests for API stability (strings unchanged for existing RIDs)."""
    
    def test_backward_compat_zero(self):
        """RID 0 still encodes to '2' (unchanged)."""
        assert encode_rid(0) == '2'
    
    def test_backward_compat_54(self):
        """RID 54 still encodes to 'Z' (unchanged)."""
        assert encode_rid(54) == 'Z'
    
    def test_backward_compat_first_10(self):
        """First 10 RIDs maintain stable encoding."""
        # These should not change across versions
        expected = {
            0: '2', 1: '3', 2: '4', 3: '5', 4: '6',
            5: '7', 6: '8', 7: '9', 8: 'a', 9: 'b'
        }
        for rid_int, expected_str in expected.items():
            assert encode_rid(rid_int) == expected_str


class TestLegacyAliases:
    """Tests for backward-compatible legacy function names."""
    
    def test_rid_to_base60_alias(self):
        """Legacy rid_to_base60() still works."""
        assert rid_to_base60(0) == '2'
        assert rid_to_base60(55) == '32'  # No IndexError!
    
    def test_base60_to_int_alias(self):
        """Legacy base60_to_int() still works."""
        assert base60_to_int('2') == 0
        assert base60_to_int('32') == 55
    
    def test_int_to_base60_alias(self):
        """Legacy int_to_base60() still works."""
        assert int_to_base60(0) == '2'
        assert int_to_base60(55) == '32'
    
    def test_legacy_aliases_match_new_functions(self):
        """Legacy aliases produce identical output to new functions."""
        test_values = [0, 1, 54, 55, 100, 1000]
        for val in test_values:
            assert rid_to_base60(val) == encode_rid(val)
            assert int_to_base60(val) == encode_rid(val)
        
        test_strings = ['2', '3', 'Z', '32', 'ab']
        for s in test_strings:
            assert base60_to_int(s) == decode_rid(s)


class TestEdgeCases:
    """Edge case and error handling tests."""
    
    def test_encode_negative_raises(self):
        """Encoder rejects negative integers."""
        with pytest.raises(ValueError, match="non-negative"):
            encode_rid(-1)
    
    def test_encode_very_large_number(self):
        """Encoder handles PostgreSQL BIGINT max (2^63-1)."""
        bigint_max = 2**63 - 1
        result = encode_rid(bigint_max)
        assert isinstance(result, str)
        assert decode_rid(result) == bigint_max
    
    def test_output_uses_only_alphabet_chars(self):
        """All encoded outputs contain only valid alphabet characters."""
        for i in range(1000):
            encoded = encode_rid(i)
            for char in encoded:
                assert char in ALPHABET

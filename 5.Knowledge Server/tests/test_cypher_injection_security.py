"""
Security tests for Cypher injection prevention.

Tests the _safe_cypher_interpolation helper function and validates
that all relationship tools properly prevent Cypher injection attacks.

Related Issues:
- #H001: Cypher Query Injection Risk
"""

import pytest

from tools.relationship_tools import (
    RelationshipType,
    _normalize_relationship_type,
    _safe_cypher_interpolation,
)


class TestSafeCypherInterpolation:
    """Test suite for _safe_cypher_interpolation security function."""

    def test_valid_whitelist_value(self):
        """Test that whitelisted values are accepted."""
        allowed = {"PREREQUISITE", "RELATES_TO", "INCLUDES"}
        template = "WHERE type(rel) = '{value}'"

        result = _safe_cypher_interpolation(
            template=template,
            value_to_inject="PREREQUISITE",
            allowed_values=allowed,
            value_name="rel_type",
        )

        assert result == "WHERE type(rel) = 'PREREQUISITE'"

    def test_invalid_whitelist_value_rejected(self):
        """Test that non-whitelisted values are rejected."""
        allowed = {"PREREQUISITE", "RELATES_TO"}
        template = "WHERE type(rel) = '{value}'"

        with pytest.raises(ValueError, match="not in whitelist"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="MALICIOUS",
                allowed_values=allowed,
                value_name="rel_type",
            )

    def test_single_quote_injection_blocked(self):
        """Test that single quote injection attempts are blocked."""
        # Even if somehow in whitelist, character check should catch it
        allowed = {"test' OR 1=1 --"}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test' OR 1=1 --",
                allowed_values=allowed,
                value_name="name",
            )

    def test_double_quote_injection_blocked(self):
        """Test that double quote injection attempts are blocked."""
        allowed = {'test" OR 1=1 --'}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject='test" OR 1=1 --',
                allowed_values=allowed,
                value_name="name",
            )

    def test_semicolon_injection_blocked(self):
        """Test that semicolon command separators are blocked."""
        allowed = {"test; DROP TABLE"}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test; DROP TABLE",
                allowed_values=allowed,
                value_name="name",
            )

    def test_comment_injection_blocked(self):
        """Test that SQL/Cypher comment markers are blocked."""
        dangerous_values = ["test-- comment", "test/* comment */", "test/*", "test*/"]

        for dangerous in dangerous_values:
            allowed = {dangerous}
            template = "WHERE name = '{value}'"

            with pytest.raises(ValueError, match="dangerous character"):
                _safe_cypher_interpolation(
                    template=template,
                    value_to_inject=dangerous,
                    allowed_values=allowed,
                    value_name="name",
                )

    def test_newline_injection_blocked(self):
        """Test that newline characters are blocked (multiline injection)."""
        allowed = {"test\nMALICIOUS"}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test\nMALICIOUS",
                allowed_values=allowed,
                value_name="name",
            )

    def test_null_byte_injection_blocked(self):
        """Test that null byte injection is blocked."""
        allowed = {"test\x00"}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test\x00",
                allowed_values=allowed,
                value_name="name",
            )

    def test_backslash_injection_blocked(self):
        """Test that backslash escape injection is blocked."""
        allowed = {"test\\"}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test\\",
                allowed_values=allowed,
                value_name="name",
            )

    def test_length_limit_enforced(self):
        """Test that excessively long values are rejected."""
        allowed = {"A" * 150}
        template = "WHERE name = '{value}'"

        with pytest.raises(ValueError, match="exceeds maximum length"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="A" * 150,
                allowed_values=allowed,
                value_name="name",
            )

    def test_all_relationship_types_in_whitelist(self):
        """Test that all enum relationship types pass validation."""
        allowed_types = {e.value for e in RelationshipType}
        template = "WHERE type(rel) = '{value}'"

        for rel_type in allowed_types:
            result = _safe_cypher_interpolation(
                template=template,
                value_to_inject=rel_type,
                allowed_values=allowed_types,
                value_name="rel_type",
            )
            assert rel_type in result


class TestNormalizeRelationshipTypeWithInjection:
    """Test _normalize_relationship_type against injection attempts."""

    def test_valid_types_accepted(self):
        """Test that all valid relationship types are accepted."""
        valid_inputs = ["prerequisite", "relates_to", "includes", "contains"]
        expected_outputs = ["PREREQUISITE", "RELATES_TO", "INCLUDES", "CONTAINS"]

        for input_val, expected in zip(valid_inputs, expected_outputs, strict=False):
            result = _normalize_relationship_type(input_val)
            assert result == expected

    def test_injection_in_type_rejected(self):
        """Test that injection attempts in relationship type are rejected."""
        malicious_inputs = [
            "prerequisite' OR 1=1 --",
            "'; DROP TABLE concepts; --",
            'prerequisite"; MATCH (n) DETACH DELETE n; //',
            "prerequisite\nMATCH (n) DETACH DELETE n",
            "prerequisite; DETACH DELETE",
        ]

        for malicious in malicious_inputs:
            with pytest.raises(ValueError, match="Invalid relationship type"):
                _normalize_relationship_type(malicious)

    def test_case_insensitive_but_strict(self):
        """Test that normalization is case-insensitive but validates strictly."""
        # Valid variations
        assert _normalize_relationship_type("PREREQUISITE") == "PREREQUISITE"
        assert _normalize_relationship_type("Prerequisite") == "PREREQUISITE"
        assert _normalize_relationship_type("prerequisite") == "PREREQUISITE"

        # Invalid even with valid case variations
        with pytest.raises(ValueError):
            _normalize_relationship_type("invalid_type")

    def test_empty_and_none_rejected(self):
        """Test that empty strings and None are rejected."""
        with pytest.raises(ValueError):
            _normalize_relationship_type("")

        with pytest.raises(ValueError):
            _normalize_relationship_type(None)

    def test_numeric_types_rejected(self):
        """Test that numeric types are rejected."""
        with pytest.raises((ValueError, AttributeError)):
            _normalize_relationship_type(123)


class TestIntegrationSecurityScenarios:
    """Integration tests for real-world attack scenarios."""

    def test_chained_injection_attempt(self):
        """Test that sophisticated chained injection is blocked."""
        # Attacker tries: prerequisite' OR '1'='1
        malicious = "prerequisite' OR '1'='1"

        # Should fail at normalization
        with pytest.raises(ValueError):
            _normalize_relationship_type(malicious)

    def test_union_injection_attempt(self):
        """Test that UNION-based injection is blocked."""
        malicious = "prerequisite' UNION SELECT * FROM concepts --"

        with pytest.raises(ValueError):
            _normalize_relationship_type(malicious)

    def test_encoded_injection_attempt(self):
        """Test that URL/hex encoded injection is blocked."""
        # Attacker tries: prerequisite%27%20OR%201%3D1
        malicious = "prerequisite%27%20OR%201%3D1"

        with pytest.raises(ValueError):
            _normalize_relationship_type(malicious)

    def test_nested_query_injection(self):
        """Test that nested query injection is blocked."""
        malicious = "prerequisite' OR 1=(SELECT COUNT(*) FROM concepts WHERE '1'='1"

        with pytest.raises(ValueError):
            _normalize_relationship_type(malicious)


class TestDefenseInDepthValidation:
    """Tests that validate defense-in-depth approach works correctly."""

    def test_whitelist_is_first_defense(self):
        """Test that whitelist check happens before character check."""
        # Even if no dangerous chars, should fail whitelist
        allowed = {"SAFE_VALUE"}
        template = "WHERE x = '{value}'"

        with pytest.raises(ValueError, match="not in whitelist"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="OTHER_VALUE",
                allowed_values=allowed,
                value_name="test",
            )

    def test_character_check_is_second_defense(self):
        """Test that character check catches what whitelist might miss."""
        # If whitelist somehow allowed dangerous chars (shouldn't happen in practice)
        allowed = {"test'value"}
        template = "WHERE x = '{value}'"

        with pytest.raises(ValueError, match="dangerous character"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject="test'value",
                allowed_values=allowed,
                value_name="test",
            )

    def test_length_check_prevents_dos(self):
        """Test that length check prevents potential DoS via large inputs."""
        # Generate a very long but safe string
        long_value = "A" * 150
        allowed = {long_value}
        template = "WHERE x = '{value}'"

        with pytest.raises(ValueError, match="exceeds maximum length"):
            _safe_cypher_interpolation(
                template=template,
                value_to_inject=long_value,
                allowed_values=allowed,
                value_name="test",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

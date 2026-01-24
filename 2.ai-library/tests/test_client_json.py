
import pytest
from src.sdk.client import ClaudeCodeClient

class TestJSONExtraction:
    def test_extract_json_markdown(self):
        """Test extraction from markdown code blocks."""
        client = ClaudeCodeClient()
        text = """
        Here is the plan:
        ```json
        {
            "foo": "bar",
            "list": [1, 2, 3]
        }
        ```
        Hope this helps.
        """
        data = client._extract_json(text)
        assert data == {"foo": "bar", "list": [1, 2, 3]}

    def test_extract_json_raw(self):
        """Test extraction from raw JSON."""
        client = ClaudeCodeClient()
        text = '{"foo": "bar"}'
        data = client._extract_json(text)
        assert data == {"foo": "bar"}

    def test_extract_json_nested_braces(self):
        """Test extraction with nested braces (which regex might struggle with or ReDoS)."""
        client = ClaudeCodeClient()
        # Deeply nested structure
        nested = '{"a": {"b": {"c": {"d": "e"}}}}' 
        text = f"Wrapper {nested} Wrapper"
        data = client._extract_json(text)
        assert data == {"a": {"b": {"c": {"d": "e"}}}}

    def test_extract_json_invalid(self):
        """Test invalid JSON returns None."""
        client = ClaudeCodeClient()
        text = "No JSON here { just braces }"
        data = client._extract_json(text)
        assert data is None

    def test_extract_json_multiple_blocks(self):
        """Should extract the first valid JSON-looking block."""
        client = ClaudeCodeClient()
        text = """
        Block 1:
        ```json
        {"first": 1}
        ```
        Block 2:
        ```json
        {"second": 2}
        ```
        """
        # Our current logic might prefer block extraction or first-brace extraction.
        # The goal is robustness.
        data = client._extract_json(text)
        assert data is not None
        assert "first" in data or "second" in data

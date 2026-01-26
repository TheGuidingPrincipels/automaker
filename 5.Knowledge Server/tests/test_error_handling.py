"""
Comprehensive Error Handling Tests

Tests error response consistency, error types, logging, and user-friendly messages
across all MCP tools to ensure Task 5.5 acceptance criteria are met.
"""

from unittest.mock import Mock, patch
from tools import concept_tools, search_tools, relationship_tools, analytics_tools
from tools.responses import ErrorType


class TestErrorResponseConsistency:
    """Test that all tools return consistent error response format"""

    @pytest.mark.asyncio
    async def test_create_concept_validation_error_format(self, configured_container):
        """Test create_concept validation error has consistent format"""
        configured_container.repository = Mock()

        result = await concept_tools.create_concept(
            name="", explanation="Test"  # Invalid: empty name
        )

        assert result["success"] is False
        assert "error" in result
        assert "error" in result and "type" in result["error"]
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value

    @pytest.mark.asyncio
    async def test_get_concept_not_found_error_format(self, configured_container):
        """Test get_concept not found error has consistent format"""
        configured_container.repository = Mock()
        configured_container.repository.get_concept = Mock(return_value=None)

        result = await concept_tools.get_concept("nonexistent-id")

        assert result["success"] is False
        assert "error" in result
        assert "error" in result and "type" in result["error"]
        assert result["error"]["type"] == ErrorType.CONCEPT_NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_update_concept_no_fields_error_format(self, configured_container):
        """Test update_concept with no fields has consistent format"""
        configured_container.repository = Mock()

        result = await concept_tools.update_concept("concept-123")

        assert result["success"] is False
        assert "error" in result
        assert "error" in result and "type" in result["error"]
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value

    @pytest.mark.asyncio
    async def test_search_semantic_error_format(self, configured_container):
        """Test search_concepts_semantic error has consistent format"""
        # Mock both required services so decorator passes
        configured_container.chromadb_service = Mock()
        configured_container.embedding_service = Mock()
        configured_container.embedding_service.generate_embedding = Mock(
            side_effect=Exception("Embedding service unavailable")
        )

        result = await search_tools.search_concepts_semantic("test query")

        assert result["success"] is False
        assert "error" in result
        assert "error" in result and "type" in result["error"]

    @pytest.mark.asyncio
    async def test_create_relationship_validation_error_format(self, configured_container):
        """Test create_relationship validation error has consistent format"""
        configured_container.neo4j_service = Mock()
        configured_container.event_store = Mock()
        configured_container.outbox = Mock()

        result = await relationship_tools.create_relationship(
            source_id="src-123",
            target_id="tgt-456",
            relationship_type="invalid_type",  # Invalid type
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert "error" in result and "type" in result["error"]
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value


class TestUserFriendlyMessages:
    """Test that error messages are user-friendly and don't expose technical details"""

    @pytest.mark.asyncio
    async def test_no_stack_traces_in_responses(self, configured_container):
        """Verify that stack traces are never exposed to MCP clients"""
        configured_container.repository = Mock()
        configured_container.repository.create_concept = Mock(
            side_effect=Exception("Database connection failed with trace...")
        )

        result = await concept_tools.create_concept(name="Test", explanation="Test")

        # Should not contain technical details like "trace", "stack", etc.
        assert "trace" not in result["error"]["message"].lower()
        assert "stack" not in result["error"]["message"].lower()
        # Should be user-friendly
        assert len(result["error"]["message"]) < 200  # Reasonable message length

    @pytest.mark.asyncio
    async def test_validation_messages_are_helpful(self, configured_container):
        """Test that validation errors provide helpful guidance"""
        configured_container.repository = Mock()

        result = await concept_tools.create_concept(name="", explanation="Test")

        # Message should indicate the issue
        assert "error" in result
        assert len(result["error"]["message"]) > 0
        # Should be user-friendly (not overly technical)
        assert "validation" in result["error"]["message"].lower() or "invalid" in result["error"]["message"].lower()

    @pytest.mark.asyncio
    async def test_database_error_messages_are_generic(self, configured_container):
        """Test that database errors don't expose internal details"""
        configured_container.neo4j_service = Mock()
        configured_container.neo4j_service.execute_read = Mock(
            side_effect=Exception("Neo4j bolt://localhost:7687 connection refused")
        )

        result = await search_tools.search_concepts_exact(name="test")

        # Should not expose connection strings or internal paths
        assert "bolt://" not in result["error"]["message"]
        assert "localhost:7687" not in result["error"]["message"]
        # Should be user-friendly (contains generic error message, not technical details)
        assert "failed" in result["error"]["message"].lower() or "error" in result["error"]["message"].lower()


class TestErrorTypeClassification:
    """Test that error types are correctly classified"""

    @pytest.mark.asyncio
    async def test_validation_error_type(self, configured_container):
        """Test validation errors use VALIDATION_ERROR type"""
        configured_container.repository = Mock()

        result = await concept_tools.create_concept(name="", explanation="Test")

        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value

    @pytest.mark.asyncio
    async def test_not_found_error_type(self, configured_container):
        """Test not found errors use correct error type"""
        configured_container.repository = Mock()
        configured_container.repository.get_concept = Mock(return_value=None)

        result = await concept_tools.get_concept("nonexistent")

        assert result["error"]["type"] == ErrorType.CONCEPT_NOT_FOUND.value

    @pytest.mark.asyncio
    async def test_database_error_type(self, configured_container):
        """Test database errors use DATABASE_ERROR type"""
        configured_container.neo4j_service = Mock()
        configured_container.neo4j_service.execute_read = Mock(
            side_effect=Exception("Database error")
        )

        result = await search_tools.search_concepts_exact(name="test")

        assert result["error"]["type"] in [
            ErrorType.DATABASE_ERROR.value,
            ErrorType.NEO4J_ERROR.value
        ]

    @pytest.mark.asyncio
    async def test_embedding_error_type(self, configured_container):
        """Test embedding errors use EMBEDDING_ERROR type"""
        configured_container.embedding_service = Mock()
        configured_container.chromadb_service = Mock()
        configured_container.neo4j_service = Mock()
        configured_container.embedding_service.generate_embedding = Mock(
            side_effect=Exception("embedding model failed")
        )

        result = await search_tools.search_concepts_semantic("test")

        assert result["error"]["type"] in [
            ErrorType.EMBEDDING_ERROR.value,
            ErrorType.INTERNAL_ERROR.value,
        ]


class TestErrorLogging:
    """Test that errors are properly logged with context"""

    @pytest.mark.asyncio
    async def test_validation_errors_logged_with_context(self, configured_container):
        """Test that validation errors include contextual information"""
        configured_container.repository = Mock()

        with patch("tools.concept_tools.logger") as mock_logger:
            await concept_tools.create_concept(name="", explanation="Test")

            # Check that warning was called (validation errors use warning level)
            assert mock_logger.warning.called
            # Check that extra context was provided
            call_args = mock_logger.warning.call_args
            assert "extra" in call_args.kwargs
            assert "operation" in call_args.kwargs["extra"]

    @pytest.mark.asyncio
    async def test_unexpected_errors_logged_with_exc_info(self, configured_container):
        """Test that unexpected errors are logged with stack trace"""
        configured_container.repository = Mock()
        configured_container.repository.create_concept = Mock(
            side_effect=Exception("Unexpected error")
        )

        with patch("tools.concept_tools.logger") as mock_logger:
            await concept_tools.create_concept(name="Test", explanation="Test")

            # Check that error was called with exc_info=True
            assert mock_logger.error.called
            call_args = mock_logger.error.call_args
            assert call_args.kwargs.get("exc_info") is True
            # Check that extra context was provided
            assert "extra" in call_args.kwargs
            assert "operation" in call_args.kwargs["extra"]

    @pytest.mark.asyncio
    async def test_search_errors_include_query_context(self, configured_container):
        """Test that search errors include query in logging context"""
        configured_container.embedding_service = Mock()
        configured_container.chromadb_service = Mock()
        configured_container.embedding_service.generate_embedding = Mock(
            side_effect=Exception("Service error")
        )

        with patch("tools.search_tools.logger") as mock_logger:
            await search_tools.search_concepts_semantic("my test query")

            assert mock_logger.error.called
            call_args = mock_logger.error.call_args
            extra = call_args.kwargs.get("extra", {})
            assert "query" in extra
            assert extra["query"] == "my test query"


class TestAllToolsHaveErrorHandling:
    """Test that all MCP tools have proper try/except blocks"""

    @pytest.mark.asyncio
    async def test_concept_tools_all_have_error_handling(self, configured_container):
        """Test all concept tools handle errors gracefully"""
        configured_container.repository = Mock()
        configured_container.repository.create_concept = Mock(side_effect=Exception("Error"))
        configured_container.repository.get_concept = Mock(side_effect=Exception("Error"))
        configured_container.repository.update_concept = Mock(side_effect=Exception("Error"))
        configured_container.repository.delete_concept = Mock(side_effect=Exception("Error"))

        # All should return error responses, not raise exceptions
        result1 = await concept_tools.create_concept("Test", "Test")
        result2 = await concept_tools.get_concept("test-id")
        result3 = await concept_tools.update_concept("test-id", name="New")
        result4 = await concept_tools.delete_concept("test-id")

        assert all(r["success"] is False for r in [result1, result2, result3, result4])
        assert all("error" in r and "type" in r["error"] for r in [result1, result2, result3, result4])

    @pytest.mark.asyncio
    async def test_search_tools_all_have_error_handling(self, configured_container):
        """Test all search tools handle errors gracefully"""
        configured_container.embedding_service = Mock()
        configured_container.chromadb_service = Mock()
        configured_container.neo4j_service = Mock()

        configured_container.embedding_service.generate_embedding = Mock(side_effect=Exception("Error"))
        configured_container.neo4j_service.execute_read = Mock(side_effect=Exception("Error"))

        # All should return error responses, not raise exceptions
        result1 = await search_tools.search_concepts_semantic("test")
        result2 = await search_tools.search_concepts_exact(name="test")
        result3 = await search_tools.get_recent_concepts(days=7)

        assert all(r["success"] is False for r in [result1, result2, result3])
        assert all("error" in r and "type" in r["error"] for r in [result1, result2, result3])

    @pytest.mark.asyncio
    async def test_relationship_tools_all_have_error_handling(self, configured_container):
        """Test all relationship tools handle errors gracefully"""
        configured_container.neo4j_service = Mock()
        configured_container.event_store = Mock()
        configured_container.outbox = Mock()
        configured_container.neo4j_service.execute_read = Mock(side_effect=Exception("Error"))
        configured_container.neo4j_service.execute_write = Mock(side_effect=Exception("Error"))

        # All should return error responses, not raise exceptions
        result1 = await relationship_tools.create_relationship("s", "t", "prerequisite")
        result2 = await relationship_tools.delete_relationship("s", "t", "prerequisite")
        result3 = await relationship_tools.get_related_concepts("test-id")
        result4 = await relationship_tools.get_prerequisites("test-id")
        result5 = await relationship_tools.get_concept_chain("s", "t")

        assert all(r["success"] is False for r in [result1, result2, result3, result4, result5])
        assert all("error" in r and "type" in r["error"] for r in [result1, result2, result3, result4, result5])

    @pytest.mark.asyncio
    async def test_analytics_tools_all_have_error_handling(self, configured_container):
        """Test all analytics tools handle errors gracefully"""
        configured_container.neo4j_service = Mock()
        configured_container.neo4j_service.execute_read = Mock(side_effect=Exception("Error"))

        # All should return error responses, not raise exceptions
        result1 = await analytics_tools.list_hierarchy()
        result2 = await analytics_tools.get_concepts_by_confidence()

        assert all(r["success"] is False for r in [result1, result2])
        assert all("error" in r and "type" in r["error"] for r in [result1, result2])


class TestValidationErrorDetails:
    """Test that validation errors include field-level details"""

    @pytest.mark.asyncio
    async def test_validation_error_includes_details(self, configured_container):
        """Test that validation errors can include field details"""
        configured_container.repository = Mock()

        result = await concept_tools.create_concept(name="", explanation="Test")  # Invalid

        assert result["success"] is False
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value
        # Error message should be informative
        assert len(result["error"]["message"]) > 0

    @pytest.mark.asyncio
    async def test_relationship_validation_includes_type_details(self, configured_container):
        """Test that relationship validation errors mention the invalid type"""
        configured_container.neo4j_service = Mock()
        configured_container.event_store = Mock()
        configured_container.outbox = Mock()

        result = await relationship_tools.create_relationship(
            source_id="src", target_id="tgt", relationship_type="invalid_relationship_type"
        )

        assert result["success"] is False
        assert result["error"]["type"] == ErrorType.VALIDATION_ERROR.value
        # Should mention the issue is with the type
        assert "type" in result["error"]["message"].lower() or "invalid" in result["error"]["message"].lower()


class TestNoSensitiveDataLogged:
    """Test that sensitive data is not included in error logs"""

    @pytest.mark.asyncio
    async def test_passwords_not_in_logs(self, configured_container):
        """Verify that if password-like fields exist, they're not logged"""
        # This is a preventive test - our current tools don't handle passwords,
        # but we verify that the pattern is safe
        configured_container.repository = Mock()

        with patch("tools.concept_tools.logger") as mock_logger:
            await concept_tools.create_concept(
                name="Test", explanation="Test with password: secret123"
            )

            # The explanation might contain sensitive data,
            # but it should not be in the extra context
            call_args = mock_logger.info.call_args
            if call_args and "extra" in call_args.kwargs:
                extra = call_args.kwargs["extra"]
                # We don't log full explanation in extra context
                assert "explanation" not in extra or len(extra.get("explanation", "")) == 0

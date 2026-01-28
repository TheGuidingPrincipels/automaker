"""
Tests for outbox race condition fix (Issue #H002).

Verifies that create_relationship and delete_relationship correctly capture
and use the outbox_id to avoid race conditions in concurrent scenarios.

Related Issues:
- #H002: Race Condition in Outbox Processing
"""

from unittest.mock import Mock, patch

import pytest

from tools.relationship_tools import create_relationship, delete_relationship


@pytest.fixture
def setup_services(configured_container):
    """Setup services for tests using container fixture."""
    return {
        "neo4j": configured_container.neo4j_service,
        "event_store": configured_container.event_store,
        "outbox": configured_container.outbox
    }


class TestOutboxRaceConditionFix:
    """Test suite for outbox race condition fix."""

    @pytest.mark.asyncio
    async def test_create_relationship_captures_outbox_id(self, setup_services):
        """Test that create_relationship captures and uses outbox_id correctly."""
        services = setup_services

        with patch('projections.neo4j_projection.Neo4jProjection') as mock_projection_class:
            # Setup neo4j service to return existing concepts
            services["neo4j"].execute_read.side_effect = [
                # First call: check concepts exist
                [{"concept_id": "concept-1"}, {"concept_id": "concept-2"}],
                # Second call: check for duplicates
                [],
            ]

            # Setup outbox to return a specific outbox_id
            expected_outbox_id = "outbox-12345"
            services["outbox"].add_to_outbox.return_value = expected_outbox_id

            # Setup projection to succeed
            mock_projection_instance = Mock()
            mock_projection_instance.project_event.return_value = True
            mock_projection_class.return_value = mock_projection_instance

            # Call create_relationship
            result = await create_relationship(
                source_id="concept-1", target_id="concept-2", relationship_type="prerequisite"
            )

            # Verify success
            assert result["success"] is True

            # CRITICAL: Verify that mark_processed was called with the CAPTURED outbox_id
            services["outbox"].mark_processed.assert_called_once_with(expected_outbox_id)

            # CRITICAL: Verify that get_pending was NOT called (old buggy behavior)
            services["outbox"].get_pending.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_relationship_captures_outbox_id(self, setup_services):
        """Test that delete_relationship captures and uses outbox_id correctly."""
        services = setup_services

        with patch('projections.neo4j_projection.Neo4jProjection') as mock_projection_class:
            # Setup neo4j service to return existing relationship
            services["neo4j"].execute_read.return_value = [{"relationship_id": "rel-123"}]

            # Setup event store
            services["event_store"].get_latest_version.return_value = 1

            # Setup outbox to return a specific outbox_id
            expected_outbox_id = "outbox-67890"
            services["outbox"].add_to_outbox.return_value = expected_outbox_id

            # Setup projection to succeed
            mock_projection_instance = Mock()
            mock_projection_instance.project_event.return_value = True
            mock_projection_class.return_value = mock_projection_instance

            # Call delete_relationship
            result = await delete_relationship(
                source_id="concept-1", target_id="concept-2", relationship_type="prerequisite"
            )

            # Verify success
            assert result["success"] is True

            # CRITICAL: Verify that mark_processed was called with the CAPTURED outbox_id
            services["outbox"].mark_processed.assert_called_once_with(expected_outbox_id)

            # CRITICAL: Verify that get_pending was NOT called (old buggy behavior)
            services["outbox"].get_pending.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrent_creates_use_correct_outbox_ids(self, setup_services):
        """
        Test that multiple concurrent create operations each mark their own outbox entry.

        This simulates the race condition scenario from Issue #H002.
        """
        services = setup_services

        # Track which outbox_ids were used
        captured_outbox_ids = []

        def mock_mark_processed(outbox_id):
            captured_outbox_ids.append(outbox_id)
            return True

        with patch('projections.neo4j_projection.Neo4jProjection') as mock_projection_class:
            # Setup neo4j service
            services["neo4j"].execute_read.side_effect = [
                # Operation 1: concept check
                [{"concept_id": "concept-1"}, {"concept_id": "concept-2"}],
                # Operation 1: duplicate check
                [],
                # Operation 2: concept check
                [{"concept_id": "concept-3"}, {"concept_id": "concept-4"}],
                # Operation 2: duplicate check
                [],
            ]

            # Setup outbox to return different IDs for each operation
            outbox_ids = ["outbox-op1", "outbox-op2"]
            services["outbox"].add_to_outbox.side_effect = outbox_ids
            services["outbox"].mark_processed.side_effect = mock_mark_processed

            # Setup projection to succeed
            mock_projection_instance = Mock()
            mock_projection_instance.project_event.return_value = True
            mock_projection_class.return_value = mock_projection_instance

            # Simulate two concurrent operations
            result1 = await create_relationship(
                source_id="concept-1", target_id="concept-2", relationship_type="prerequisite"
            )

            result2 = await create_relationship(
                source_id="concept-3", target_id="concept-4", relationship_type="relates_to"
            )

            # Both should succeed
            assert result1["success"] is True
            assert result2["success"] is True

            # CRITICAL: Each operation should have marked its OWN outbox_id
            assert captured_outbox_ids == ["outbox-op1", "outbox-op2"]

            # CRITICAL: Verify get_pending was never called (would cause race condition)
            services["outbox"].get_pending.assert_not_called()

    @pytest.mark.asyncio
    async def test_projection_failure_does_not_call_mark_processed(self, setup_services):
        """Test that if projection fails, outbox entry is NOT marked as processed."""
        services = setup_services

        with patch('projections.neo4j_projection.Neo4jProjection') as mock_projection_class:
            # Setup neo4j service
            services["neo4j"].execute_read.side_effect = [
                [{"concept_id": "concept-1"}, {"concept_id": "concept-2"}],
                [],
            ]

            # Setup outbox
            services["outbox"].add_to_outbox.return_value = "outbox-fail"

            # Setup projection to FAIL
            mock_projection_instance = Mock()
            mock_projection_instance.project_event.return_value = False
            mock_projection_class.return_value = mock_projection_instance

            # Call create_relationship
            result = await create_relationship(
                source_id="concept-1", target_id="concept-2", relationship_type="prerequisite"
            )

            # Should fail
            assert result["success"] is False

            # CRITICAL: mark_processed should NOT be called if projection failed
            services["outbox"].mark_processed.assert_not_called()

            # The outbox entry remains pending for retry
            services["outbox"].add_to_outbox.assert_called_once()


class TestOutboxIdLogging:
    """Test that outbox_id is properly logged for debugging."""

    @pytest.mark.asyncio
    async def test_create_relationship_logs_outbox_id(self, setup_services):
        """Test that the outbox_id is logged when added to outbox."""
        services = setup_services

        with patch('projections.neo4j_projection.Neo4jProjection'), \
             patch('tools.relationship_tools.logger') as mock_logger:

            # Setup mocks
            services["neo4j"].execute_read.side_effect = [
                [{"concept_id": "concept-1"}, {"concept_id": "concept-2"}],
                [],
            ]
            services["outbox"].add_to_outbox.return_value = "outbox-log-test"

            # Call function
            await create_relationship(
                source_id="concept-1", target_id="concept-2", relationship_type="prerequisite"
            )

            # Verify that outbox_id was logged
            # Find the debug call that contains "Added to outbox"
            debug_calls = [
                call for call in mock_logger.debug.call_args_list if "Added to outbox" in str(call)
            ]

            assert len(debug_calls) > 0, "Expected log message with outbox_id"
            # Verify the outbox_id is in the log message
            log_message = str(debug_calls[0])
            assert "outbox-log-test" in log_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

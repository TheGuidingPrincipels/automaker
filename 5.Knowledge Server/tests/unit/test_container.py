"""
Unit tests for ServiceContainer pattern.

Tests the singleton pattern, initialization, and shutdown behavior.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from services.container import (
    ServiceContainer,
    get_container,
    set_container,
    reset_container,
)


class TestServiceContainerDataclass:
    """Tests for the ServiceContainer dataclass."""

    def test_default_initialization(self):
        """Container should initialize with all services as None."""
        container = ServiceContainer()

        assert container.event_store is None
        assert container.outbox is None
        assert container.neo4j_service is None
        assert container.chromadb_service is None
        assert container.embedding_service is None
        assert container.repository is None
        assert container.confidence_runtime is None
        assert container.confidence_listener is None
        assert container.confidence_listener_task is None

    def test_service_assignment(self):
        """Services should be assignable after initialization."""
        container = ServiceContainer()
        mock_service = Mock()

        container.neo4j_service = mock_service

        assert container.neo4j_service is mock_service

    def test_is_initialized_false_when_empty(self):
        """is_initialized should return False when core services are missing."""
        container = ServiceContainer()

        assert container.is_initialized() is False

    def test_is_initialized_true_with_core_services(self):
        """is_initialized should return True when all core services are set."""
        container = ServiceContainer()
        container.event_store = Mock()
        container.outbox = Mock()
        container.neo4j_service = Mock()
        container.chromadb_service = Mock()
        container.repository = Mock()

        assert container.is_initialized() is True

    def test_is_initialized_false_with_partial_services(self):
        """is_initialized should return False if any core service is missing."""
        container = ServiceContainer()
        container.event_store = Mock()
        container.outbox = Mock()
        container.neo4j_service = Mock()
        # chromadb_service and repository not set

        assert container.is_initialized() is False


class TestConfidenceServiceProperty:
    """Tests for the confidence_service computed property."""

    def test_confidence_service_returns_none_without_runtime(self):
        """Should return None when confidence_runtime is not set."""
        container = ServiceContainer()

        assert container.confidence_service is None

    def test_confidence_service_returns_calculator_from_runtime(self):
        """Should return calculator from confidence_runtime when set."""
        container = ServiceContainer()
        mock_calculator = Mock()
        mock_runtime = Mock()
        mock_runtime.calculator = mock_calculator
        container.confidence_runtime = mock_runtime

        assert container.confidence_service is mock_calculator


class TestGetServiceStatus:
    """Tests for the get_service_status method."""

    def test_all_services_none(self):
        """Status should show all services as False when none are set."""
        container = ServiceContainer()
        status = container.get_service_status()

        assert status["event_store"] is False
        assert status["outbox"] is False
        assert status["neo4j_service"] is False
        assert status["chromadb_service"] is False
        assert status["embedding_service"] is False
        assert status["repository"] is False
        assert status["confidence_runtime"] is False

    def test_partial_services_set(self):
        """Status should accurately reflect which services are initialized."""
        container = ServiceContainer()
        container.neo4j_service = Mock()
        container.event_store = Mock()

        status = container.get_service_status()

        assert status["event_store"] is True
        assert status["neo4j_service"] is True
        assert status["outbox"] is False
        assert status["chromadb_service"] is False


class TestShutdown:
    """Tests for the async shutdown method."""

    @pytest.mark.asyncio
    async def test_shutdown_with_no_services(self):
        """Shutdown should complete without error when no services are set."""
        container = ServiceContainer()

        # Should not raise
        await container.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cancels_listener_task(self):
        """Shutdown should cancel the confidence listener task."""
        container = ServiceContainer()

        # Create a real task that we can cancel
        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        container.confidence_listener_task = task

        await container.shutdown()

        assert task.cancelled()

    @pytest.mark.asyncio
    async def test_shutdown_closes_confidence_runtime(self):
        """Shutdown should close the confidence runtime."""
        container = ServiceContainer()
        mock_runtime = AsyncMock()
        container.confidence_runtime = mock_runtime

        await container.shutdown()

        mock_runtime.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_handles_cancelled_error(self):
        """Shutdown should handle CancelledError from task cancellation."""
        container = ServiceContainer()

        # Create a real task that will raise CancelledError when cancelled
        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        container.confidence_listener_task = task

        # Should not raise
        await container.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_closes_event_store(self):
        """Shutdown should close the event store."""
        container = ServiceContainer()
        mock_event_store = Mock()
        container.event_store = mock_event_store

        await container.shutdown()

        mock_event_store.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_outbox(self):
        """Shutdown should close the outbox."""
        container = ServiceContainer()
        mock_outbox = Mock()
        container.outbox = mock_outbox

        await container.shutdown()

        mock_outbox.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_neo4j_service(self):
        """Shutdown should close the Neo4j service."""
        container = ServiceContainer()
        mock_neo4j = Mock()
        container.neo4j_service = mock_neo4j

        await container.shutdown()

        mock_neo4j.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_chromadb_service(self):
        """Shutdown should close the ChromaDB service."""
        container = ServiceContainer()
        mock_chromadb = Mock()
        container.chromadb_service = mock_chromadb

        await container.shutdown()

        mock_chromadb.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_closes_all_services(self):
        """Shutdown should close all services with close() methods."""
        container = ServiceContainer()
        container.event_store = Mock()
        container.outbox = Mock()
        container.neo4j_service = Mock()
        container.chromadb_service = Mock()
        container.confidence_runtime = AsyncMock()

        await container.shutdown()

        container.event_store.close.assert_called_once()
        container.outbox.close.assert_called_once()
        container.neo4j_service.close.assert_called_once()
        container.chromadb_service.close.assert_called_once()
        container.confidence_runtime.close.assert_awaited_once()


class TestSingletonPattern:
    """Tests for the global container singleton pattern."""

    def test_get_container_creates_singleton(self, reset_service_container):
        """get_container should create a container if none exists."""
        container = get_container()

        assert container is not None
        assert isinstance(container, ServiceContainer)

    def test_get_container_returns_same_instance(self, reset_service_container):
        """get_container should return the same instance on subsequent calls."""
        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_set_container_replaces_global(self, reset_service_container):
        """set_container should replace the global container."""
        original = get_container()
        new_container = ServiceContainer()
        new_container.neo4j_service = Mock()

        set_container(new_container)

        assert get_container() is new_container
        assert get_container() is not original

    def test_reset_container_clears_global(self, reset_service_container):
        """reset_container should clear the global, allowing fresh creation."""
        original = get_container()
        original.neo4j_service = Mock()

        reset_container()
        fresh = get_container()

        assert fresh is not original
        assert fresh.neo4j_service is None

    def test_reset_then_get_creates_empty_container(self, reset_service_container):
        """After reset, get_container should return an empty container."""
        get_container().neo4j_service = Mock()

        reset_container()
        container = get_container()

        assert container.is_initialized() is False


class TestContainerIsolation:
    """Tests for test isolation with container fixtures."""

    def test_fixture_provides_clean_container(self, reset_service_container):
        """The reset_service_container fixture should provide isolation."""
        # Set something on the global container
        container = get_container()
        container.neo4j_service = Mock()

        # After reset (which happens at test end), next test gets clean state
        # This test verifies the fixture is in place
        assert container.neo4j_service is not None

    def test_mock_container_fixture(self, mock_container):
        """mock_container fixture should provide mocked services."""
        assert mock_container.neo4j_service is not None
        assert mock_container.event_store is not None
        assert mock_container.outbox is not None
        assert mock_container.repository is not None

    def test_configured_container_sets_global(self, configured_container):
        """configured_container should set itself as the global."""
        assert get_container() is configured_container

    def test_configured_container_has_mocks(self, configured_container):
        """configured_container should have mocked services accessible via get_container."""
        container = get_container()
        assert container.neo4j_service is not None
        assert isinstance(container.neo4j_service, Mock)

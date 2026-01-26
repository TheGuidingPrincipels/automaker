"""
Unit tests for Neo4j Service

Tests cover:
- Connection establishment and pooling
- Health check functionality
- Schema verification
- Query execution (read and write)
- Error handling and retries
- Connection cleanup
- Context manager usage
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from neo4j.exceptions import AuthError, ServiceUnavailable

from services.neo4j_service import Neo4jConfig, Neo4jService, create_neo4j_service_from_env


class TestNeo4jConfig:
    """Test Neo4jConfig model."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = Neo4jConfig()
        assert config.uri == "bolt://localhost:7687"
        assert config.user == "neo4j"
        assert config.password == "password"
        assert config.min_pool_size == 2
        assert config.max_pool_size == 10

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = Neo4jConfig(
            uri="bolt://custom:7687",
            user="custom_user",
            password="custom_pass",
            max_pool_size=20,
        )
        assert config.uri == "bolt://custom:7687"
        assert config.user == "custom_user"
        assert config.max_pool_size == 20

    def test_config_validation(self):
        """Test configuration validation."""
        # Test min_pool_size validation
        with pytest.raises(Exception):
            Neo4jConfig(min_pool_size=0)  # Should be >= 1

        # Test max_pool_size validation
        with pytest.raises(Exception):
            Neo4jConfig(max_pool_size=101)  # Should be <= 100


class TestNeo4jService:
    """Test Neo4jService functionality."""

    def test_init_with_params(self):
        """Test initialization with individual parameters."""
        service = Neo4jService(
            uri="bolt://test:7687",
            user="test_user",
            password="test_pass",
        )
        assert service.config.uri == "bolt://test:7687"
        assert service.config.user == "test_user"
        assert service.config.password == "test_pass"
        assert service.driver is None
        assert service._connected is False

    def test_init_with_config(self):
        """Test initialization with Neo4jConfig object."""
        config = Neo4jConfig(
            uri="bolt://config:7687",
            user="config_user",
            max_pool_size=15,
        )
        service = Neo4jService(config=config)
        assert service.config.uri == "bolt://config:7687"
        assert service.config.max_pool_size == 15

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_connect_success(self, mock_driver_class):
        """Test successful connection."""
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        result = service.connect()

        assert result is True
        assert service._connected is True
        assert service.driver == mock_driver
        mock_driver.verify_connectivity.assert_called_once()

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_connect_service_unavailable(self, mock_driver_class):
        """Test connection failure due to service unavailable."""
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = ServiceUnavailable("Service down")
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        result = service.connect()

        assert result is False
        assert service._connected is False

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_connect_auth_error(self, mock_driver_class):
        """Test connection failure due to authentication error."""
        mock_driver = Mock()
        mock_driver.verify_connectivity.side_effect = AuthError("Invalid credentials")
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        result = service.connect()

        assert result is False
        assert service._connected is False

    def test_close(self):
        """Test connection cleanup."""
        service = Neo4jService()
        service.driver = Mock()
        service._connected = True

        service.close()

        assert service._connected is False
        service.driver.close.assert_called_once()

    def test_is_connected(self):
        """Test connection status check."""
        service = Neo4jService()

        # Initially not connected
        assert service.is_connected() is False

        # Simulate connection
        service.driver = Mock()
        service._connected = True
        assert service.is_connected() is True

        # After closing
        service._connected = False
        assert service.is_connected() is False

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_health_check_healthy(self, mock_driver_class):
        """Test health check when service is healthy."""
        # Setup mocks
        mock_result = Mock()
        mock_result.single.return_value = {"test": 1}

        mock_db_info = Mock()
        mock_db_info.single.return_value = {
            "name": "Neo4j Kernel",
            "versions": ["5.0.0"],
            "edition": "community",
        }

        mock_session = MagicMock()
        mock_session.run.side_effect = [mock_result, mock_db_info]

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        health = service.health_check()

        assert health["status"] == "healthy"
        assert health["service"] == "neo4j"
        assert health["connected"] is True
        assert "database_info" in health

    def test_health_check_not_connected(self):
        """Test health check when not connected."""
        service = Neo4jService()

        health = service.health_check()

        assert health["status"] == "unhealthy"
        assert health["connected"] is False
        assert "error" in health

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_execute_read_success(self, mock_driver_class):
        """Test successful read query execution."""
        mock_result = [
            {"id": 1, "name": "Concept 1"},
            {"id": 2, "name": "Concept 2"},
        ]
        mock_session = MagicMock()
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        result = service.execute_read("MATCH (n) RETURN n")

        assert len(result) == 2
        assert result[0]["name"] == "Concept 1"

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_execute_write_success(self, mock_driver_class):
        """Test successful write query execution."""
        mock_summary = Mock()
        mock_summary.counters.nodes_created = 1
        mock_summary.counters.properties_set = 3
        mock_summary.counters.nodes_deleted = 0
        mock_summary.counters.relationships_created = 0
        mock_summary.counters.relationships_deleted = 0
        mock_summary.counters.labels_added = 1
        mock_summary.counters.labels_removed = 0
        mock_summary.counters.indexes_added = 0
        mock_summary.counters.indexes_removed = 0
        mock_summary.counters.constraints_added = 0
        mock_summary.counters.constraints_removed = 0

        mock_result = Mock()
        mock_result.consume.return_value = mock_summary

        mock_session = MagicMock()
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        result = service.execute_write("CREATE (n:Test {name: 'test'})")

        assert result["nodes_created"] == 1
        assert result["properties_set"] == 3
        assert result["labels_added"] == 1

    def test_execute_read_not_connected(self):
        """Test read query when not connected."""
        service = Neo4jService()

        with pytest.raises(RuntimeError, match="Not connected"):
            service.execute_read("MATCH (n) RETURN n")

    def test_execute_write_not_connected(self):
        """Test write query when not connected."""
        service = Neo4jService()

        with pytest.raises(RuntimeError, match="Not connected"):
            service.execute_write("CREATE (n:Test)")

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_context_manager(self, mock_driver_class):
        """Test context manager usage."""
        mock_driver = Mock()
        mock_driver.verify_connectivity = Mock()
        mock_driver.close = Mock()
        mock_driver_class.return_value = mock_driver

        with Neo4jService() as service:
            assert service._connected is True
            assert service.driver == mock_driver

        mock_driver.close.assert_called_once()

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_session_context_manager(self, mock_driver_class):
        """Test session context manager."""
        mock_session = Mock()
        mock_driver = Mock()
        mock_driver.session.return_value = mock_session
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        with service.session() as session:
            assert session == mock_session

        mock_session.close.assert_called_once()

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_transaction_context_manager_commit(self, mock_driver_class):
        """Test transaction context manager with successful commit."""
        mock_tx = Mock()
        mock_session = MagicMock()
        mock_session.begin_transaction.return_value = mock_tx

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        with service.transaction() as tx:
            assert tx == mock_tx

        mock_tx.commit.assert_called_once()
        mock_tx.rollback.assert_not_called()

    @patch("services.neo4j_service.GraphDatabase.driver")
    def test_transaction_context_manager_rollback(self, mock_driver_class):
        """Test transaction context manager with rollback on error."""
        mock_tx = Mock()
        mock_session = MagicMock()
        mock_session.begin_transaction.return_value = mock_tx

        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_driver.session.return_value.__exit__.return_value = None
        mock_driver.verify_connectivity = Mock()
        mock_driver_class.return_value = mock_driver

        service = Neo4jService()
        service.connect()

        with pytest.raises(ValueError), service.transaction():
            raise ValueError("Test error")

        mock_tx.rollback.assert_called_once()
        mock_tx.commit.assert_not_called()


class TestIntegrationWithRealNeo4j:
    """
    Integration tests with real Neo4j instance.

    These tests require Neo4j to be running at bolt://localhost:7687
    with credentials neo4j/password
    """

    @pytest.fixture
    def service(self):
        """Create Neo4j service connected to real instance."""
        service = Neo4jService(uri="bolt://localhost:7687", user="neo4j", password="password")
        connected = service.connect()
        if not connected:
            pytest.skip("Neo4j not available for integration tests")
        yield service
        service.close()

    def test_real_connection(self, service):
        """Test connection to real Neo4j instance."""
        assert service.is_connected() is True

    def test_real_health_check(self, service):
        """Test health check with real Neo4j instance."""
        health = service.health_check()
        assert health["status"] == "healthy"
        assert health["connected"] is True
        assert "database_info" in health

    def test_real_schema_verification(self, service):
        """Test schema verification with real Neo4j instance."""
        # Verify constraints exist
        result = service.execute_read("SHOW CONSTRAINTS")
        assert len(result) >= 4  # Should have at least 4 unique constraints

        # Verify indexes exist
        result = service.execute_read("SHOW INDEXES")
        assert len(result) >= 9  # Should have at least 9 indexes (constraints + explicit)

    def test_real_read_write_cycle(self, service):
        """Test read and write cycle with real Neo4j instance."""
        # Write a test node
        test_id = "test_concept_12345"
        write_result = service.execute_write(
            "CREATE (c:Concept {concept_id: $id, name: $name}) RETURN c",
            {"id": test_id, "name": "Test Concept"},
        )
        assert write_result["nodes_created"] == 1

        # Read it back
        read_result = service.execute_read(
            "MATCH (c:Concept {concept_id: $id}) RETURN c.name AS name", {"id": test_id}
        )
        assert len(read_result) == 1
        assert read_result[0]["name"] == "Test Concept"

        # Clean up
        service.execute_write("MATCH (c:Concept {concept_id: $id}) DELETE c", {"id": test_id})


def test_create_service_from_env():
    """Test creating service from environment variables."""
    import os

    # Set environment variables
    os.environ["NEO4J_URI"] = "bolt://env:7687"
    os.environ["NEO4J_USER"] = "env_user"
    os.environ["NEO4J_PASSWORD"] = "env_pass"

    try:
        service = create_neo4j_service_from_env()

        assert service.config.uri == "bolt://env:7687"
        assert service.config.user == "env_user"
        assert service.config.password == "env_pass"
    finally:
        # Clean up environment variables
        for key in ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]:
            if key in os.environ:
                del os.environ[key]

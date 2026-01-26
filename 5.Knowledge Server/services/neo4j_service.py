"""
Neo4j Service Module

Provides connection management and query execution for Neo4j graph database.

Features:
- Connection pooling with configurable pool size
- Health check monitoring
- Transaction management with context managers
- Error handling with retries
- Query execution methods for read and write operations
"""

import logging
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, Transaction, basic_auth
from neo4j.exceptions import (
    AuthError,
    DatabaseError,
    ServiceUnavailable,
    TransientError,
)
from neo4j.graph import Node, Path, Relationship
from neo4j.spatial import CartesianPoint, WGS84Point
from neo4j.time import Date, DateTime, Duration, Time
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class Neo4jConfig(BaseModel):
    """Configuration for Neo4j connection."""

    uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    user: str = Field(default="neo4j", description="Neo4j username")
    password: str = Field(default="password", description="Neo4j password")
    min_pool_size: int = Field(default=2, ge=1, le=100, description="Minimum connection pool size")
    max_pool_size: int = Field(default=10, ge=1, le=100, description="Maximum connection pool size")
    max_connection_lifetime: int = Field(
        default=3600, ge=60, description="Max lifetime of connections in seconds"
    )
    connection_timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")
    max_transaction_retry_time: int = Field(
        default=30, ge=1, description="Max retry time for transactions in seconds"
    )


class Neo4jService:
    """Service for managing Neo4j database connections and operations."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        config: Neo4jConfig | None = None,
    ):
        """
        Initialize Neo4j service.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            config: Optional Neo4jConfig for advanced configuration

        Raises:
            ValueError: If default password used in production environment
        """
        if config:
            self.config = config
        else:
            self.config = Neo4jConfig(uri=uri, user=user, password=password)

        # Security: Prevent default credentials in production
        import os

        if os.getenv("ENV", "development") == "production":
            if self.config.password == "password":
                raise ValueError(
                    "Default password 'password' is not allowed in production. "
                    "Set NEO4J_PASSWORD environment variable."
                )

        self.driver: Driver | None = None
        self._connected = False

    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Close existing driver if reconnecting to prevent resource leak
            if self.driver is not None:
                try:
                    self.driver.close()
                    logger.debug("Closed existing driver before reconnecting")
                except Exception as e:
                    logger.warning(f"Error closing existing driver: {e}")

            self.driver = GraphDatabase.driver(
                self.config.uri,
                auth=basic_auth(self.config.user, self.config.password),
                max_connection_pool_size=self.config.max_pool_size,
                max_connection_lifetime=self.config.max_connection_lifetime,
                connection_timeout=self.config.connection_timeout,
                max_transaction_retry_time=self.config.max_transaction_retry_time,
            )

            # Verify connectivity
            self.driver.verify_connectivity()
            self._connected = True
            logger.info(f"Connected to Neo4j at {self.config.uri}")
            return True

        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            self._connected = False
            return False
        except AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            self._connected = False
            return False

    def close(self) -> None:
        """Close Neo4j connection and cleanup resources."""
        if self.driver:
            self.driver.close()
            self._connected = False
            logger.info("Neo4j connection closed")

    def is_connected(self) -> bool:
        """
        Check if service is connected to Neo4j.

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.driver is not None

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check on Neo4j connection.

        Returns:
            Dictionary with health check results
        """
        health_status = {
            "service": "neo4j",
            "connected": self._connected,
            "uri": self.config.uri,
            "pool_size": None,
            "database_info": None,
            "status": "unhealthy",
        }

        if not self.driver or not self._connected:
            health_status["error"] = "Not connected to Neo4j"
            return health_status

        try:
            # Test connection with simple query
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_value = result.single()["test"]

                if test_value == 1:
                    # Get database info
                    db_info = session.run("CALL dbms.components() YIELD name, versions, edition")
                    db_record = db_info.single()

                    health_status["status"] = "healthy"
                    health_status["database_info"] = {
                        "name": db_record["name"],
                        "versions": db_record["versions"],
                        "edition": db_record["edition"],
                    }

        except Exception as e:
            health_status["error"] = str(e)
            health_status["status"] = "unhealthy"
            logger.error(f"Health check failed: {e}")

        return health_status

    @contextmanager
    def session(self, database: str = "neo4j"):
        """
        Context manager for Neo4j session.

        Args:
            database: Database name to connect to

        Yields:
            Neo4j session object
        """
        if not self.driver or not self._connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        session_ctx = self.driver.session(database=database)

        # Support both context-managed sessions and plain session objects (for mocks)
        if hasattr(session_ctx, "__enter__") and hasattr(session_ctx, "__exit__"):
            try:
                with session_ctx as session:
                    yield session
            finally:
                try:
                    session_ctx.close()
                except Exception as exc:
                    logger.warning("Error closing Neo4j session: %s", exc)
        else:
            try:
                yield session_ctx
            finally:
                close_method = getattr(session_ctx, "close", None)
                if callable(close_method):
                    try:
                        close_method()
                    except Exception as exc:
                        logger.warning("Error closing Neo4j session: %s", exc)

    @contextmanager
    def transaction(self, database: str = "neo4j"):
        """
        Context manager for Neo4j transaction.

        Args:
            database: Database name to connect to

        Yields:
            Neo4j transaction object
        """
        with self.session(database=database) as session:
            tx: Transaction = session.begin_transaction()
            try:
                yield tx
                tx.commit()
            except Exception as e:
                tx.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise

    def _serialize_neo4j_types(self, obj: Any) -> Any:
        """
        Recursively serialize Neo4j types to JSON-compatible format.

        Handles:
        - Temporal types: DateTime, Date, Time, Duration
        - Spatial types: CartesianPoint, WGS84Point
        - Graph types: Node, Relationship, Path
        - Collections: dict, list, tuple

        Raises:
            TypeError: If unknown non-serializable type encountered
        """
        # Handle Neo4j temporal types
        if isinstance(obj, (DateTime, Date, Time)):
            return obj.iso_format()
        elif isinstance(obj, Duration):
            return {
                "months": obj.months,
                "days": obj.days,
                "seconds": obj.seconds,
                "nanoseconds": obj.nanoseconds,
            }

        # Handle Neo4j spatial types
        elif isinstance(obj, (CartesianPoint, WGS84Point)):
            return {"x": obj.x, "y": obj.y, "z": getattr(obj, "z", None), "srid": obj.srid}

        # Handle Neo4j graph types
        elif isinstance(obj, Node):
            # Serialize node properties directly (maintain compatibility with dict(node) behavior)
            return {k: self._serialize_neo4j_types(v) for k, v in dict(obj).items()}
        elif isinstance(obj, Relationship):
            # Serialize relationship properties directly (maintain compatibility with dict(relationship) behavior)
            return {k: self._serialize_neo4j_types(v) for k, v in dict(obj).items()}
        elif isinstance(obj, Path):
            return {
                "nodes": [self._serialize_neo4j_types(n) for n in obj.nodes],
                "relationships": [self._serialize_neo4j_types(r) for r in obj.relationships],
            }

        # Recursively handle collections
        elif isinstance(obj, dict):
            return {k: self._serialize_neo4j_types(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_neo4j_types(item) for item in obj]

        # Pass through JSON-safe primitives
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj

        # Strict: raise error for unknown types
        else:
            raise TypeError(f"Cannot serialize type {type(obj).__name__}: {obj}")

    def execute_read(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> list[dict[str, Any]]:
        """
        Execute a read query on Neo4j.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name

        Returns:
            List of result records as dictionaries
        """
        if not self.driver or not self._connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        parameters = parameters or {}

        try:
            with self.session(database=database) as session:
                result = session.run(query, parameters)
                return [self._serialize_neo4j_types(dict(record)) for record in result]
        except TransientError as e:
            logger.warning(f"Transient error in read query, retrying: {e}")
            # Retry once for transient errors
            with self.session(database=database) as session:
                result = session.run(query, parameters)
                return [self._serialize_neo4j_types(dict(record)) for record in result]
        except DatabaseError as e:
            logger.error(f"Database error in read query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in read query: {e}")
            raise

    def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str = "neo4j",
    ) -> dict[str, Any]:
        """
        Execute a write query on Neo4j.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Database name

        Returns:
            Dictionary with write operation statistics
        """
        if not self.driver or not self._connected:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        parameters = parameters or {}

        try:
            with self.session(database=database) as session:
                result = session.run(query, parameters)
                summary = result.consume()

                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                    "labels_removed": summary.counters.labels_removed,
                    "indexes_added": summary.counters.indexes_added,
                    "indexes_removed": summary.counters.indexes_removed,
                    "constraints_added": summary.counters.constraints_added,
                    "constraints_removed": summary.counters.constraints_removed,
                }
        except TransientError as e:
            logger.warning(f"Transient error in write query, retrying: {e}")
            # Retry once for transient errors
            with self.session(database=database) as session:
                result = session.run(query, parameters)
                summary = result.consume()
                # Return same structure as normal success, with retry flag
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                    "labels_added": summary.counters.labels_added,
                    "labels_removed": summary.counters.labels_removed,
                    "indexes_added": summary.counters.indexes_added,
                    "indexes_removed": summary.counters.indexes_removed,
                    "constraints_added": summary.counters.constraints_added,
                    "constraints_removed": summary.counters.constraints_removed,
                    "retry": True,  # Additional flag to indicate retry occurred
                }
        except DatabaseError as e:
            logger.error(f"Database error in write query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in write query: {e}")
            raise

    def __enter__(self):
        """Context manager entry - connect to Neo4j."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close Neo4j connection."""
        self.close()


# Convenience function for creating service from environment
def create_neo4j_service_from_env() -> Neo4jService:
    """
    Create Neo4j service from environment variables.

    Uses centralized config system (config.get_settings()).

    Returns:
        Configured Neo4jService instance
    """
    from config import get_settings

    settings = get_settings()

    config = Neo4jConfig(
        uri=settings.neo4j.uri,
        user=settings.neo4j.user,
        password=settings.neo4j.password,
        min_pool_size=settings.neo4j.min_pool_size,
        max_pool_size=settings.neo4j.max_pool_size,
        max_connection_lifetime=settings.neo4j.max_connection_lifetime,
        connection_timeout=settings.neo4j.connection_timeout,
        max_transaction_retry_time=settings.neo4j.max_transaction_retry_time,
    )

    return Neo4jService(config=config)

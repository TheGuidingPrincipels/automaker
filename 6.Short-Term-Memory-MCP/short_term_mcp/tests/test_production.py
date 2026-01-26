"""
Tests for production readiness features: logging, health checks, and monitoring.

Phase 7 - Production Readiness Test Suite
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import pytest

from short_term_mcp import tools_impl
from short_term_mcp.config import LOG_DIR
from short_term_mcp.database import Database, get_db
from short_term_mcp.logging_config import get_logger, log_performance, setup_logging
from short_term_mcp.models import Concept, ConceptStatus, Session, SessionStatus


@pytest.fixture
def test_db():
    """Create a fresh test database for each test"""
    db_path = Path("test_production.db")
    db = Database(db_path)
    db.initialize()
    yield db
    db.close()
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_session(test_db):
    """Create a sample session for testing"""
    session = Session(
        session_id="2025-10-10",
        date="2025-10-10",
        learning_goal="Test production features",
        building_goal="Build monitoring system",
    )
    test_db.create_session(session)
    return session


@pytest.fixture
def sample_concepts(test_db, sample_session):
    """Create sample concepts for testing"""
    concepts = []
    for i in range(5):
        concept = Concept(
            concept_id=f"concept_{i}",
            session_id=sample_session.session_id,
            concept_name=f"Test Concept {i}",
            current_status=ConceptStatus.IDENTIFIED,
            current_data={"index": i},
        )
        test_db.create_concept(concept)
        concepts.append(concept)
    return concepts


# ==============================================================================
# HEALTH CHECK TESTS
# ==============================================================================


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_basic(self, test_db):
        """Test basic health check returns success"""
        # Override global db for testing
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.health_check_impl()

            assert result["status"] == "success"
            assert result["overall_status"] in ["healthy", "degraded"]
            assert "timestamp" in result
            assert "response_time_ms" in result
            assert "components" in result
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_health_check_database_status(self, test_db):
        """Test health check includes database status"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.health_check_impl()

            db_status = result["components"]["database"]
            assert db_status["status"] == "healthy"
            assert db_status["connection"] == "active"
            assert "integrity" in db_status
            assert "size_bytes" in db_status
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_health_check_cache_status(self, test_db):
        """Test health check includes cache status"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.health_check_impl()

            cache_status = result["components"]["cache"]
            assert cache_status["status"] == "operational"
            assert "size" in cache_status
            assert cache_status["ttl_seconds"] == 300
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, test_db):
        """Test health check completes in <50ms"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.health_check_impl()

            assert (
                result["response_time_ms"] < 50
            ), f"Health check took {result['response_time_ms']}ms (target: <50ms)"
        finally:
            db_module._db = original_db


# ==============================================================================
# SYSTEM METRICS TESTS
# ==============================================================================


class TestSystemMetrics:
    """Test system metrics functionality"""

    @pytest.mark.asyncio
    async def test_get_system_metrics_basic(self, test_db, sample_session):
        """Test basic metrics retrieval"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.get_system_metrics_impl()

            assert result["status"] == "success"
            assert "timestamp" in result
            assert "database" in result
            assert "operations" in result
            assert "performance" in result
            assert "cache" in result
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_system_metrics_database_stats(self, test_db, sample_concepts):
        """Test database statistics in metrics"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.get_system_metrics_impl()

            db_stats = result["database"]
            assert "size_bytes" in db_stats
            assert "size_mb" in db_stats
            assert db_stats["sessions"] >= 1
            assert db_stats["concepts"] == 5
            assert "stage_data_entries" in db_stats
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_system_metrics_operation_counts(self, test_db, sample_concepts):
        """Test operation counters in metrics"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Perform some operations
            test_db.record_operation("read", 1.5)
            test_db.record_operation("write", 2.5)
            test_db.record_operation("query", 0.5)

            result = await tools_impl.get_system_metrics_impl()

            ops = result["operations"]
            assert ops["reads"] >= 1
            assert ops["writes"] >= 1
            assert ops["queries"] >= 1
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_system_metrics_performance_timing(self, test_db):
        """Test performance timing statistics"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Record some operations
            for i in range(10):
                test_db.record_operation("read", 1.0 + i * 0.1)

            result = await tools_impl.get_system_metrics_impl()

            perf = result["performance"]
            assert "read_times" in perf
            read_stats = perf["read_times"]
            assert read_stats["count"] == 10
            assert read_stats["min_ms"] <= read_stats["avg_ms"] <= read_stats["max_ms"]
        finally:
            db_module._db = original_db


# ==============================================================================
# ERROR LOGGING TESTS
# ==============================================================================


class TestErrorLogging:
    """Test error logging functionality"""

    @pytest.mark.asyncio
    async def test_get_error_log_empty(self, test_db):
        """Test error log when no errors recorded"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            result = await tools_impl.get_error_log_impl()

            assert result["status"] == "success"
            assert result["error_count"] == 0
            assert result["errors"] == []
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_get_error_log_with_errors(self, test_db):
        """Test error log returns recorded errors"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Record some errors
            test_db.record_error("DatabaseError", "Connection timeout", {"op": "query"})
            test_db.record_error("ValueError", "Invalid input", {"param": "session_id"})

            result = await tools_impl.get_error_log_impl()

            assert result["error_count"] == 2
            assert len(result["errors"]) == 2

            # Check error structure
            error = result["errors"][0]
            assert "timestamp" in error
            assert "error_type" in error
            assert "message" in error
            assert "context" in error
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_get_error_log_limit(self, test_db):
        """Test error log respects limit parameter"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Record 20 errors
            for i in range(20):
                test_db.record_error("TestError", f"Error {i}")

            result = await tools_impl.get_error_log_impl(limit=5)

            assert result["error_count"] == 5
            assert len(result["errors"]) == 5
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_get_error_log_type_filter(self, test_db):
        """Test error log filters by error type"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Record different error types
            test_db.record_error("DatabaseError", "DB error 1")
            test_db.record_error("DatabaseError", "DB error 2")
            test_db.record_error("ValueError", "Value error 1")

            result = await tools_impl.get_error_log_impl(error_type="DatabaseError")

            assert result["error_count"] == 2
            assert all(e["error_type"] == "DatabaseError" for e in result["errors"])
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_get_error_log_limit_bounds(self, test_db):
        """Test error log limit is bounded correctly"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Test lower bound (should default to 10)
            result = await tools_impl.get_error_log_impl(limit=0)
            assert result["filter"]["limit"] == 10

            # Test upper bound (should cap at 100)
            result = await tools_impl.get_error_log_impl(limit=200)
            assert result["filter"]["limit"] == 100
        finally:
            db_module._db = original_db


# ==============================================================================
# LOGGING CONFIGURATION TESTS
# ==============================================================================


class TestLoggingConfiguration:
    """Test logging configuration and functionality"""

    def test_logging_setup(self):
        """Test logging setup creates handlers"""
        setup_logging(log_level="INFO", enable_file_logging=False, enable_console_logging=True)

        logger = get_logger("test_logger")
        assert logger is not None
        assert logger.level <= 20  # INFO level

    def test_log_files_created(self):
        """Test log files are created when enabled"""
        setup_logging(enable_file_logging=True)

        assert LOG_DIR.exists()
        # Note: Log files are created on first write, not on setup

    def test_logger_hierarchy(self):
        """Test logger hierarchy is set up correctly"""
        setup_logging()

        db_logger = get_logger("short_term_mcp.database")
        tools_logger = get_logger("short_term_mcp.tools_impl")

        assert db_logger is not None
        assert tools_logger is not None


# ==============================================================================
# DATABASE METRICS TESTS
# ==============================================================================


class TestDatabaseMetrics:
    """Test database metrics tracking"""

    def test_record_operation(self, test_db):
        """Test operation recording"""
        test_db.record_operation("read", 1.5)
        test_db.record_operation("write", 2.5)

        metrics = test_db.get_metrics()
        assert metrics["operations"]["reads"] == 1
        assert metrics["operations"]["writes"] == 1
        # get_metrics() returns aggregated stats, not raw lists
        assert metrics["timing"]["read_times"]["count"] == 1
        assert metrics["timing"]["write_times"]["count"] == 1
        assert metrics["timing"]["read_times"]["avg_ms"] == 1.5
        assert metrics["timing"]["write_times"]["avg_ms"] == 2.5

    def test_record_error(self, test_db):
        """Test error recording"""
        test_db.record_error("TestError", "Test message", {"key": "value"})

        errors = test_db.get_errors()
        assert len(errors) == 1
        assert errors[0]["error_type"] == "TestError"
        assert errors[0]["message"] == "Test message"
        assert errors[0]["context"]["key"] == "value"

    def test_metrics_memory_bounds(self, test_db):
        """Test metrics don't grow unbounded"""
        # Record 2000 operations (should keep only last 1000)
        for i in range(2000):
            test_db.record_operation("read", 1.0)

        metrics = test_db.get_metrics()
        assert len(test_db.metrics["timing"]["read_times"]) == 1000

    def test_error_log_memory_bounds(self, test_db):
        """Test error log doesn't grow unbounded"""
        # Record 200 errors (should keep only last 100)
        for i in range(200):
            test_db.record_error("TestError", f"Error {i}")

        errors = test_db.get_errors(limit=200)
        assert len(test_db.metrics["errors"]) == 100

    def test_get_database_size(self, test_db, sample_concepts):
        """Test database size calculation"""
        size = test_db.get_database_size()
        assert size > 0

    def test_get_health_status(self, test_db):
        """Test health status check"""
        status = test_db.get_health_status()
        assert status["status"] == "healthy"
        assert status["connection"] == "active"
        assert status["integrity"] == "ok"


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestProductionIntegration:
    """Integration tests for production features"""

    @pytest.mark.asyncio
    async def test_complete_monitoring_workflow(self, test_db, sample_concepts):
        """Test complete monitoring workflow"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # 1. Check health
            health = await tools_impl.health_check_impl()
            assert health["overall_status"] == "healthy"

            # 2. Get metrics
            metrics = await tools_impl.get_system_metrics_impl()
            assert metrics["database"]["concepts"] == 5

            # 3. Simulate error
            test_db.record_error("TestError", "Test error")

            # 4. Check error log
            errors = await tools_impl.get_error_log_impl()
            assert errors["error_count"] == 1
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_performance_under_load(self, test_db):
        """Test monitoring performance under load"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Create session and concepts
            session = Session(
                session_id="2025-10-10",
                date="2025-10-10",
                learning_goal="Load test",
                building_goal="Performance test",
            )
            test_db.create_session(session)

            # Create 100 concepts
            for i in range(100):
                concept = Concept(
                    concept_id=f"load_test_{i}",
                    session_id=session.session_id,
                    concept_name=f"Concept {i}",
                    current_status=ConceptStatus.IDENTIFIED,
                )
                test_db.create_concept(concept)

            # Test health check performance
            start = time.time()
            health = await tools_impl.health_check_impl()
            health_time = (time.time() - start) * 1000

            assert health_time < 50, f"Health check took {health_time}ms"

            # Test metrics performance
            start = time.time()
            metrics = await tools_impl.get_system_metrics_impl()
            metrics_time = (time.time() - start) * 1000

            assert metrics_time < 100, f"Metrics took {metrics_time}ms"
            assert metrics["database"]["concepts"] == 100
        finally:
            db_module._db = original_db


# ==============================================================================
# PERFORMANCE TESTS
# ==============================================================================


class TestProductionPerformance:
    """Performance tests for production features"""

    @pytest.mark.asyncio
    async def test_health_check_performance(self, test_db):
        """Test health check meets performance target"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            times = []
            for _ in range(10):
                start = time.time()
                await tools_impl.health_check_impl()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            assert avg_time < 50, f"Average health check: {avg_time:.2f}ms (target: <50ms)"
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_metrics_collection_performance(self, test_db, sample_concepts):
        """Test metrics collection performance"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            start = time.time()
            await tools_impl.get_system_metrics_impl()
            elapsed = (time.time() - start) * 1000

            assert elapsed < 100, f"Metrics collection took {elapsed:.2f}ms (target: <100ms)"
        finally:
            db_module._db = original_db

    @pytest.mark.asyncio
    async def test_error_log_retrieval_performance(self, test_db):
        """Test error log retrieval performance"""
        import short_term_mcp.database as db_module

        original_db = db_module._db
        db_module._db = test_db

        try:
            # Add 50 errors
            for i in range(50):
                test_db.record_error("TestError", f"Error {i}")

            start = time.time()
            await tools_impl.get_error_log_impl(limit=50)
            elapsed = (time.time() - start) * 1000

            assert elapsed < 50, f"Error log retrieval took {elapsed:.2f}ms (target: <50ms)"
        finally:
            db_module._db = original_db

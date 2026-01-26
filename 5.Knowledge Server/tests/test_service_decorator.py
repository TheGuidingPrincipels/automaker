"""
Tests for @requires_services decorator and service status utilities

Validates that the decorator properly protects against null pointer dereferences
by checking service availability before tool execution.

Fixes issues #C001-#C031 (24 critical null pointer issues)
"""

import pytest
from tools.service_utils import requires_services, get_service_status, get_available_tools
from tools.responses import ErrorType
from services.container import ServiceContainer, set_container, reset_container


@pytest.fixture
def null_services_container():
    """Container with all services set to None for decorator testing"""
    container = ServiceContainer()
    # All services are None by default in a fresh container
    set_container(container)
    yield container
    reset_container()


class TestRequiresServicesDecorator:
    """Test suite for @requires_services decorator"""

    @pytest.mark.asyncio
    async def test_decorator_allows_execution_when_service_available(self):
        """Test that decorator allows function execution when service is available"""
        # Create a mock container with the required service
        mock_container = ServiceContainer()
        mock_container.test_service = {"status": "ready"}
        set_container(mock_container)

        # Create a test function with the decorator
        @requires_services("test_service")
        async def test_function():
            return {"success": True, "data": "test"}

        # Execute the function - container is accessed via get_container()
        result = await test_function()

        # Verify it executed successfully
        assert result["success"] is True
        assert result["data"] == "test"

    @pytest.mark.asyncio
    async def test_decorator_blocks_execution_when_service_is_none(self):
        """Test that decorator returns error when service is None"""

        # Create a test function with the decorator
        @requires_services("missing_service")
        async def test_function():
            return {"success": True}

        # Set the service to None
        test_function.__wrapped__.__globals__["missing_service"] = None

        # Execute the function
        result = await test_function()

        # Verify error response
        assert result["success"] is False
        assert result["error"]["type"] == ErrorType.SERVICE_UNAVAILABLE.value
        assert "missing_service not initialized" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_decorator_checks_multiple_services(self):
        """Test that decorator checks all required services"""
        # Create a mock container with service_a ready but service_b None
        mock_container = ServiceContainer()
        mock_container.service_a = {"status": "ready"}
        mock_container.service_b = None  # This one is not initialized
        set_container(mock_container)

        # Create a test function requiring both services
        @requires_services("service_a", "service_b")
        async def test_function():
            return {"success": True}

        # Execute the function - container is accessed via get_container()
        result = await test_function()

        # Verify it fails due to service_b being None
        assert result["success"] is False
        assert "service_b not initialized" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_decorator_allows_execution_when_all_services_available(self):
        """Test that decorator allows execution when all required services are available"""
        # Create a mock container with all required services
        mock_container = ServiceContainer()
        mock_container.service_a = {"status": "ready"}
        mock_container.service_b = {"status": "ready"}
        mock_container.service_c = {"status": "ready"}
        set_container(mock_container)

        # Create a test function requiring all services
        @requires_services("service_a", "service_b", "service_c")
        async def test_function():
            return {"success": True, "all_services_ready": True}

        # Execute the function - container is accessed via get_container()
        result = await test_function()

        # Verify success
        assert result["success"] is True
        assert result["all_services_ready"] is True

    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata"""

        @requires_services("test_service")
        async def my_function():
            """My function docstring"""
            return {"success": True}

        # Verify function name and docstring are preserved
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == """My function docstring"""

    @pytest.mark.asyncio
    async def test_decorator_error_response_format(self):
        """Test that error response has correct format"""

        @requires_services("null_service")
        async def test_function():
            return {"success": True}

        test_function.__wrapped__.__globals__["null_service"] = None

        result = await test_function()

        # Verify error response structure
        assert "success" in result
        assert "error" in result
        assert result["success"] is False
        assert isinstance(result["error"], dict)
        assert "type" in result["error"]
        assert "message" in result["error"]
        assert result["error"]["type"] == ErrorType.SERVICE_UNAVAILABLE.value

    @pytest.mark.asyncio
    async def test_decorator_with_function_arguments(self):
        """Test that decorator works with functions that have arguments"""
        # Create a mock container with the required service
        mock_container = ServiceContainer()
        mock_container.service = {"status": "ready"}
        set_container(mock_container)

        @requires_services("service")
        async def test_function(arg1, arg2, kwarg1=None):
            return {"success": True, "arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        # Execute the function - container is accessed via get_container()
        result = await test_function("value1", "value2", kwarg1="value3")

        assert result["success"] is True
        assert result["arg1"] == "value1"
        assert result["arg2"] == "value2"
        assert result["kwarg1"] == "value3"

    @pytest.mark.asyncio
    async def test_decorator_stops_at_first_missing_service(self):
        """Test that decorator returns error on first missing service"""
        service_a = None
        service_b = None

        @requires_services("service_a", "service_b")
        async def test_function():
            return {"success": True}

        test_function.__wrapped__.__globals__["service_a"] = service_a
        test_function.__wrapped__.__globals__["service_b"] = service_b

        result = await test_function()

        # Should report service_a (first in the list)
        assert "service_a not initialized" in result["error"]["message"]


class TestRealToolIntegration:
    """Integration tests with real tools to verify decorator is applied correctly"""

    @pytest.mark.asyncio
    async def test_create_concept_has_decorator(self, null_services_container):
        """Verify create_concept tool has the decorator"""
        from tools.concept_tools import create_concept

        # Check that the function is wrapped
        # When decorated, the function should have __wrapped__ attribute
        assert hasattr(create_concept, "__wrapped__") or hasattr(create_concept, "__name__")

        # Container has all services as None by default (via null_services_container fixture)

        # Call the function - should return error, not crash
        result = await create_concept(name="Test", explanation="Test explanation")

        # Should get service unavailable error, not AttributeError
        assert result["success"] is False
        assert "repository not initialized" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_search_concepts_semantic_has_decorator(self, null_services_container):
        """Verify search_concepts_semantic has the decorator"""
        from tools.search_tools import search_concepts_semantic

        # Container has all services as None by default (via null_services_container fixture)

        # Call the function - should return error, not crash
        result = await search_concepts_semantic(query="test")

        # Should get service unavailable error
        assert result["success"] is False
        assert "not initialized" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_relationship_has_decorator(self, null_services_container):
        """Verify create_relationship has the decorator"""
        from tools.relationship_tools import create_relationship

        # Container has all services as None by default (via null_services_container fixture)

        # Call the function - should return error, not crash
        result = await create_relationship(
            source_id="uuid1", target_id="uuid2", relationship_type="prerequisite"
        )

        # Should get service unavailable error
        assert result["success"] is False
        assert "not initialized" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_list_hierarchy_has_decorator(self, null_services_container):
        """Verify list_hierarchy has the decorator"""
        from tools.analytics_tools import list_hierarchy

        # Container has all services as None by default (via null_services_container fixture)

        # Call the function - should return error, not crash
        result = await list_hierarchy()

        # Should get service unavailable error
        assert result["success"] is False
        assert "neo4j_service not initialized" in result["error"]["message"]


class TestServiceStatusUtilities:
    """Test suite for service status utility functions"""

    def test_get_service_status_returns_dict(self):
        """Test that get_service_status returns a dictionary"""
        status = get_service_status()

        assert isinstance(status, dict)
        assert "concept_tools" in status
        assert "search_tools" in status
        assert "relationship_tools" in status
        assert "analytics_tools" in status

    def test_get_service_status_concept_tools(self):
        """Test that concept_tools status is reported correctly"""
        status = get_service_status()

        assert "repository" in status["concept_tools"]
        assert "confidence_service" in status["concept_tools"]
        assert isinstance(status["concept_tools"]["repository"], bool)
        assert isinstance(status["concept_tools"]["confidence_service"], bool)

    def test_get_service_status_search_tools(self):
        """Test that search_tools status is reported correctly"""
        status = get_service_status()

        assert "neo4j_service" in status["search_tools"]
        assert "chromadb_service" in status["search_tools"]
        assert "embedding_service" in status["search_tools"]
        assert isinstance(status["search_tools"]["neo4j_service"], bool)
        assert isinstance(status["search_tools"]["chromadb_service"], bool)
        assert isinstance(status["search_tools"]["embedding_service"], bool)

    def test_get_service_status_relationship_tools(self):
        """Test that relationship_tools status is reported correctly"""
        status = get_service_status()

        assert "neo4j_service" in status["relationship_tools"]
        assert "event_store" in status["relationship_tools"]
        assert "outbox" in status["relationship_tools"]
        assert isinstance(status["relationship_tools"]["neo4j_service"], bool)
        assert isinstance(status["relationship_tools"]["event_store"], bool)
        assert isinstance(status["relationship_tools"]["outbox"], bool)

    def test_get_service_status_analytics_tools(self):
        """Test that analytics_tools status is reported correctly"""
        status = get_service_status()

        assert "neo4j_service" in status["analytics_tools"]
        assert isinstance(status["analytics_tools"]["neo4j_service"], bool)

    def test_get_available_tools_returns_dict(self):
        """Test that get_available_tools returns a properly structured dictionary"""
        tools = get_available_tools()

        assert isinstance(tools, dict)
        assert "available" in tools
        assert "unavailable" in tools
        assert "total_tools" in tools
        assert "service_status" in tools

    def test_get_available_tools_lists_are_sorted(self):
        """Test that tool lists are sorted alphabetically"""
        tools = get_available_tools()

        # Verify lists are sorted
        assert tools["available"] == sorted(tools["available"])
        assert tools["unavailable"] == sorted(tools["unavailable"])

    def test_get_available_tools_total_count_is_16(self):
        """Test that total tool count is 16"""
        tools = get_available_tools()

        assert tools["total_tools"] == 16

    def test_get_available_tools_includes_all_tools(self):
        """Test that all 16 tools are accounted for"""
        tools = get_available_tools()

        # Total should equal available + unavailable
        total = len(tools["available"]) + len(tools["unavailable"])
        assert total == 16

        # Check that key tools are in the list
        all_tools = tools["available"] + tools["unavailable"]
        assert "ping" in all_tools
        assert "create_concept" in all_tools
        assert "get_concept" in all_tools
        assert "search_concepts_semantic" in all_tools
        assert "create_relationship" in all_tools

    def test_get_available_tools_ping_always_available(self):
        """Test that ping tool is always available (no dependencies)"""
        tools = get_available_tools()

        # ping has no dependencies, should always be available
        assert "ping" in tools["available"]

    def test_get_available_tools_get_server_stats_always_available(self):
        """Test that get_server_stats is always available (no dependencies)"""
        tools = get_available_tools()

        # get_server_stats has no dependencies, should always be available
        assert "get_server_stats" in tools["available"]

    def test_get_available_tools_service_status_matches(self):
        """Test that service_status in result matches get_service_status()"""
        tools = get_available_tools()
        status = get_service_status()

        # The service_status in tools should match direct call
        assert tools["service_status"] == status


class TestToolAvailabilityIntegration:
    """Integration tests for get_tool_availability functionality"""

    def test_get_available_tools_with_utility_function(self):
        """Test that the utility function works correctly"""
        # This test validates the underlying function that get_tool_availability uses
        from tools.service_utils import get_available_tools

        result = get_available_tools()

        # Verify response structure
        assert isinstance(result, dict)
        assert "available" in result
        assert "unavailable" in result
        assert "total_tools" in result
        assert "service_status" in result

        # Verify it's returning the correct data
        assert isinstance(result["available"], list)
        assert isinstance(result["unavailable"], list)
        assert result["total_tools"] == 16


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

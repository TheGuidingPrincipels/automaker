"""
Unit Tests for Advanced Relationship Tools

Tests for delete_relationship, get_related_concepts, get_prerequisites, and get_concept_chain.
"""

from unittest.mock import Mock, patch

import pytest

from tools import relationship_tools


@pytest.fixture
def mock_services(configured_container):
    """Mock the injected services using the configured_container fixture.

    Note: Services are accessed via get_container() in relationship_tools,
    so we use configured_container which sets up the global mock container.
    """
    return {
        "neo4j": configured_container.neo4j_service,
        "event_store": configured_container.event_store,
        "outbox": configured_container.outbox
    }


# =============================================================================
# Task 4.1: delete_relationship Tests
# =============================================================================


class TestDeleteRelationship:
    """Tests for delete_relationship tool"""

    @pytest.mark.asyncio
    async def test_delete_relationship_success(self, mock_services):
        """Test successful relationship deletion"""
        # Mock existing relationship
        mock_services["neo4j"].execute_read.return_value = [{"relationship_id": "rel-abc123"}]

        # Mock event store version
        mock_services["event_store"].get_latest_version = Mock(return_value=0)

        # Mock successful projection
        with patch("projections.neo4j_projection.Neo4jProjection") as MockProjection:
            mock_projection = MockProjection.return_value
            mock_projection.project_event.return_value = True

            result = await relationship_tools.delete_relationship(
                source_id="concept-001", target_id="concept-002", relationship_type="prerequisite"
            )

        assert result["success"] is True
        mock_services["event_store"].append_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_relationship_not_found(self, mock_services):
        """Test deleting non-existent relationship"""
        # Mock no relationship found
        mock_services["neo4j"].execute_read.return_value = []

        result = await relationship_tools.delete_relationship(
            source_id="concept-001", target_id="concept-002", relationship_type="prerequisite"
        )

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["not found", "doesn't exist", "does not exist"])

    @pytest.mark.asyncio
    async def test_delete_relationship_invalid_type(self, mock_services):
        """Test deletion with invalid relationship type"""
        result = await relationship_tools.delete_relationship(
            source_id="concept-001", target_id="concept-002", relationship_type="invalid_type"
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"
        assert "must be one of" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_delete_relationship_missing_params(self, mock_services):
        """Test deletion with missing parameters"""
        result = await relationship_tools.delete_relationship(
            source_id="", target_id="concept-002", relationship_type="prerequisite"
        )

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["invalid", "validation", "required"])


# =============================================================================
# Task 4.2: get_related_concepts Tests
# =============================================================================


class TestGetRelatedConcepts:
    """Tests for get_related_concepts tool"""

    @pytest.mark.asyncio
    async def test_get_related_outgoing(self, mock_services):
        """Test getting outgoing related concepts"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "concept_id": "concept-002",
                "name": "Advanced Topic",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            },
            {
                "concept_id": "concept-003",
                "name": "Related Topic",
                "relationship_type": "RELATES_TO",
                "strength": 0.8,
                "distance": 1,
            },
        ]

        result = await relationship_tools.get_related_concepts(
            concept_id="concept-001", direction="outgoing", max_depth=1
        )

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-001"
        assert result["data"]["total"] == 2
        assert len(result["data"]["related"]) == 2
        assert result["data"]["related"][0]["concept_id"] == "concept-002"
        assert result["data"]["related"][0]["relationship_type"] == "prerequisite"

    @pytest.mark.asyncio
    async def test_get_related_incoming(self, mock_services):
        """Test getting incoming related concepts"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "concept_id": "concept-000",
                "name": "Basic Topic",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        result = await relationship_tools.get_related_concepts(
            concept_id="concept-001", direction="incoming", max_depth=1
        )

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["related"][0]["concept_id"] == "concept-000"

    @pytest.mark.asyncio
    async def test_get_related_with_type_filter(self, mock_services):
        """Test filtering by relationship type"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "concept_id": "concept-002",
                "name": "Prerequisite Topic",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        result = await relationship_tools.get_related_concepts(
            concept_id="concept-001",
            relationship_type="prerequisite",
            direction="outgoing",
            max_depth=2,
        )

        assert result["success"] is True
        assert result["data"]["total"] == 1
        assert result["data"]["related"][0]["relationship_type"] == "prerequisite"

    @pytest.mark.asyncio
    async def test_get_related_max_depth_validation(self, mock_services):
        """Test max_depth validation"""
        mock_services["neo4j"].execute_read.return_value = []

        # Test with depth too high (should auto-adjust)
        result = await relationship_tools.get_related_concepts(
            concept_id="concept-001", max_depth=10  # Will be adjusted to 5
        )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_related_invalid_direction(self, mock_services):
        """Test with invalid direction"""
        result = await relationship_tools.get_related_concepts(
            concept_id="concept-001", direction="sideways"  # Invalid
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"
        assert "must be one of" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_get_related_empty_result(self, mock_services):
        """Test with no related concepts"""
        mock_services["neo4j"].execute_read.return_value = []

        result = await relationship_tools.get_related_concepts(concept_id="concept-001")

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert result["data"]["related"] == []


# =============================================================================
# Task 4.3: get_prerequisites Tests
# =============================================================================


class TestGetPrerequisites:
    """Tests for get_prerequisites tool"""

    @pytest.mark.asyncio
    async def test_get_prerequisites_simple_chain(self, mock_services):
        """Test simple prerequisite chain"""
        mock_services["neo4j"].execute_read.return_value = [
            {"concept_id": "concept-001", "name": "Basics", "depth": 2},
            {"concept_id": "concept-002", "name": "Intermediate", "depth": 1},
        ]

        result = await relationship_tools.get_prerequisites(concept_id="concept-003", max_depth=5)

        assert result["success"] is True
        assert result["data"]["concept_id"] == "concept-003"
        assert result["data"]["total"] == 2
        assert len(result["data"]["chain"]) == 2
        # Should be ordered by depth DESC (deepest first)
        assert result["data"]["chain"][0]["depth"] == 2
        assert result["data"]["chain"][1]["depth"] == 1

    @pytest.mark.asyncio
    async def test_get_prerequisites_no_prerequisites(self, mock_services):
        """Test concept with no prerequisites"""
        mock_services["neo4j"].execute_read.return_value = []

        result = await relationship_tools.get_prerequisites(concept_id="concept-001")

        assert result["success"] is True
        assert result["data"]["total"] == 0
        assert result["data"]["chain"] == []

    @pytest.mark.asyncio
    async def test_get_prerequisites_deep_chain(self, mock_services):
        """Test deep prerequisite chain"""
        mock_services["neo4j"].execute_read.return_value = [
            {"concept_id": "concept-001", "name": "Level 1", "depth": 5},
            {"concept_id": "concept-002", "name": "Level 2", "depth": 4},
            {"concept_id": "concept-003", "name": "Level 3", "depth": 3},
            {"concept_id": "concept-004", "name": "Level 4", "depth": 2},
            {"concept_id": "concept-005", "name": "Level 5", "depth": 1},
        ]

        result = await relationship_tools.get_prerequisites(concept_id="concept-006", max_depth=10)

        assert result["success"] is True
        assert result["data"]["total"] == 5
        # Verify ordering
        for i in range(4):
            assert result["data"]["chain"][i]["depth"] > result["data"]["chain"][i + 1]["depth"]

    @pytest.mark.asyncio
    async def test_get_prerequisites_max_depth_validation(self, mock_services):
        """Test max_depth validation"""
        mock_services["neo4j"].execute_read.return_value = []

        # Test with depth too high (should auto-adjust to 10)
        result = await relationship_tools.get_prerequisites(concept_id="concept-001", max_depth=20)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_prerequisites_invalid_concept_id(self, mock_services):
        """Test with invalid concept_id"""
        result = await relationship_tools.get_prerequisites(concept_id="")

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["invalid", "validation", "required"])


# =============================================================================
# Task 4.4: get_concept_chain Tests
# =============================================================================


class TestGetConceptChain:
    """Tests for get_concept_chain tool"""

    @pytest.mark.asyncio
    async def test_get_concept_chain_found(self, mock_services):
        """Test finding shortest path between concepts"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "path": [
                    {"concept_id": "concept-001", "name": "Start"},
                    {"concept_id": "concept-002", "name": "Middle"},
                    {"concept_id": "concept-003", "name": "End"},
                ],
                "length": 2,
            }
        ]

        result = await relationship_tools.get_concept_chain(
            start_id="concept-001", end_id="concept-003"
        )

        assert result["success"] is True
        assert result["data"]["length"] == 2
        assert len(result["data"]["path"]) == 3
        assert result["data"]["path"][0]["concept_id"] == "concept-001"
        assert result["data"]["path"][2]["concept_id"] == "concept-003"

    @pytest.mark.asyncio
    async def test_get_concept_chain_not_found(self, mock_services):
        """Test when no path exists"""
        mock_services["neo4j"].execute_read.return_value = []

        result = await relationship_tools.get_concept_chain(
            start_id="concept-001", end_id="concept-999"
        )

        assert result["success"] is True
        assert result["data"]["length"] == 0
        assert result["data"]["path"] == []

    @pytest.mark.asyncio
    async def test_get_concept_chain_with_type_filter(self, mock_services):
        """Test filtering by relationship type"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "path": [
                    {"concept_id": "concept-001", "name": "Start"},
                    {"concept_id": "concept-002", "name": "End"},
                ],
                "length": 1,
            }
        ]

        result = await relationship_tools.get_concept_chain(
            start_id="concept-001", end_id="concept-002", relationship_type="prerequisite"
        )

        assert result["success"] is True
        assert result["data"]["length"] == 1

    @pytest.mark.asyncio
    async def test_get_concept_chain_direct_connection(self, mock_services):
        """Test direct connection (length 1)"""
        mock_services["neo4j"].execute_read.return_value = [
            {
                "path": [
                    {"concept_id": "concept-001", "name": "Start"},
                    {"concept_id": "concept-002", "name": "End"},
                ],
                "length": 1,
            }
        ]

        result = await relationship_tools.get_concept_chain(
            start_id="concept-001", end_id="concept-002"
        )

        assert result["success"] is True
        assert result["data"]["length"] == 1
        assert len(result["data"]["path"]) == 2

    @pytest.mark.asyncio
    async def test_get_concept_chain_invalid_params(self, mock_services):
        """Test with invalid parameters"""
        result = await relationship_tools.get_concept_chain(start_id="", end_id="concept-002")

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["invalid", "validation", "required"])

    @pytest.mark.asyncio
    async def test_get_concept_chain_invalid_type(self, mock_services):
        """Test with invalid relationship type"""
        result = await relationship_tools.get_concept_chain(
            start_id="concept-001", end_id="concept-002", relationship_type="invalid_type"
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] == "validation_error"
        assert "must be one of" in result["error"]["message"]


# =============================================================================
# Integration-style Tests (with more realistic mocking)
# =============================================================================


class TestRelationshipToolsIntegration:
    """Integration-style tests for relationship tools"""

    @pytest.mark.asyncio
    async def test_delete_and_verify_workflow(self, mock_services):
        """Test workflow: check exists → delete → verify deleted"""
        # First call: relationship exists
        mock_services["neo4j"].execute_read.return_value = [{"relationship_id": "rel-abc123"}]

        # Mock event store version
        mock_services["event_store"].get_latest_version = Mock(return_value=0)

        with patch("projections.neo4j_projection.Neo4jProjection") as MockProjection:
            mock_projection = MockProjection.return_value
            mock_projection.project_event.return_value = True

            result = await relationship_tools.delete_relationship(
                source_id="concept-001", target_id="concept-002", relationship_type="prerequisite"
            )

        assert result["success"] is True

        # Second call: relationship not found (already deleted)
        mock_services["neo4j"].execute_read.return_value = []

        result2 = await relationship_tools.delete_relationship(
            source_id="concept-001", target_id="concept-002", relationship_type="prerequisite"
        )

        assert result2["success"] is False
        assert "error" in result2
        assert any(phrase in result2["error"]["message"].lower() for phrase in ["not found", "doesn't exist", "does not exist"])

    @pytest.mark.asyncio
    async def test_get_related_to_prerequisites_workflow(self, mock_services):
        """Test workflow: find related → filter prerequisites → get chain"""
        # Step 1: Get all related concepts
        mock_services["neo4j"].execute_read.return_value = [
            {
                "concept_id": "concept-prereq-1",
                "name": "Prerequisite 1",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            },
            {
                "concept_id": "concept-related-1",
                "name": "Related Topic",
                "relationship_type": "RELATES_TO",
                "strength": 0.8,
                "distance": 1,
            },
        ]

        related_result = await relationship_tools.get_related_concepts(
            concept_id="concept-target", direction="incoming"
        )

        assert related_result["success"] is True
        assert related_result["data"]["total"] == 2

        # Step 2: Get prerequisites specifically
        mock_services["neo4j"].execute_read.return_value = [
            {"concept_id": "concept-prereq-1", "name": "Prerequisite 1", "depth": 1}
        ]

        prereq_result = await relationship_tools.get_prerequisites(concept_id="concept-target")

        assert prereq_result["success"] is True
        assert prereq_result["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_concept_chain_between_related_concepts(self, mock_services):
        """Test finding path between concepts discovered via get_related"""
        # Step 1: Find related concepts
        mock_services["neo4j"].execute_read.return_value = [
            {
                "concept_id": "concept-nearby",
                "name": "Nearby Concept",
                "relationship_type": "RELATES_TO",
                "strength": 0.9,
                "distance": 2,
            }
        ]

        related_result = await relationship_tools.get_related_concepts(
            concept_id="concept-start", max_depth=3
        )

        assert related_result["success"] is True

        # Step 2: Find exact path to that concept
        mock_services["neo4j"].execute_read.return_value = [
            {
                "path": [
                    {"concept_id": "concept-start", "name": "Start"},
                    {"concept_id": "concept-middle", "name": "Middle"},
                    {"concept_id": "concept-nearby", "name": "Nearby Concept"},
                ],
                "length": 2,
            }
        ]

        chain_result = await relationship_tools.get_concept_chain(
            start_id="concept-start", end_id="concept-nearby"
        )

        assert chain_result["success"] is True
        assert chain_result["data"]["length"] == 2

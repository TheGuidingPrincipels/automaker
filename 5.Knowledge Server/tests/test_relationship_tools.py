"""
Unit tests for relationship_tools
"""

from unittest.mock import Mock, patch

import pytest

from tools import relationship_tools


@pytest.fixture
def setup_services(configured_container):
    """Setup mock services for testing using container fixture"""
    # Configure mocks on container services
    configured_container.neo4j_service.execute_read = Mock(return_value=[])
    configured_container.neo4j_service.execute_write = Mock(return_value={"relationships_created": 1})

    configured_container.event_store.append_event = Mock()
    configured_container.event_store.get_latest_version = Mock(return_value=0)

    configured_container.outbox.add_entry = Mock()
    configured_container.outbox.add_to_outbox = Mock()
    configured_container.outbox.get_pending = Mock(return_value=[])
    configured_container.outbox.mark_processed = Mock()

    return {
        "neo4j": configured_container.neo4j_service,
        "event_store": configured_container.event_store,
        "outbox": configured_container.outbox
    }


class TestCreateRelationship:
    """Tests for create_relationship tool"""

    @pytest.mark.asyncio
    async def test_create_relationship_success(self, setup_services):
        """Test successful relationship creation"""
        services = setup_services

        # Mock concepts exist check, then duplicate check (no duplicates)
        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        # Mock projection success
        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=True)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001",
                target_id="concept-002",
                relationship_type="prerequisite",
                strength=1.0,
            )

            assert result["success"] is True
            assert result["data"]["relationship_id"] is not None
            assert result["data"]["relationship_id"].startswith("rel-")
            assert result["message"] == "Relationship created"

            # Verify event was stored
            services["event_store"].append_event.assert_called_once()

            # Verify outbox entry was added
            services["outbox"].add_to_outbox.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_type(self, setup_services):
        """Test validation of invalid relationship type"""

        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="invalid_type",
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert "relationship_type must be one of" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_relationship_invalid_strength(self, setup_services):
        """Test validation of strength range"""

        # Test strength too high
        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=1.5,
        )

        assert result["success"] is False
        assert "error" in result
        assert "strength must be a number between 0.0 and 1.0" in result["error"]["message"]

        # Test strength negative
        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=-0.1,
        )

        assert result["success"] is False
        assert "error" in result
        assert "strength must be a number between 0.0 and 1.0" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_relationship_missing_source(self, setup_services):
        """Test error when source concept doesn't exist"""
        services = setup_services

        # Mock only target exists
        services["neo4j"].execute_read = Mock(return_value=[{"concept_id": "concept-002"}])

        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["does not exist", "doesn't exist", "not found", "has been deleted"])

    @pytest.mark.asyncio
    async def test_create_relationship_missing_target(self, setup_services):
        """Test error when target concept doesn't exist"""
        services = setup_services

        # Mock only source exists
        services["neo4j"].execute_read = Mock(return_value=[{"concept_id": "concept-001"}])

        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["does not exist", "doesn't exist", "not found", "has been deleted"])

    @pytest.mark.asyncio
    async def test_create_relationship_duplicate(self, setup_services):
        """Test handling of duplicate relationship"""
        services = setup_services

        # Mock concepts exist check
        def side_effect(query, params):
            if "WHERE c.concept_id IN" in query:
                return [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}]
            else:
                # Duplicate check
                return [{"relationship_id": "rel-existing"}]

        services["neo4j"].execute_read = Mock(side_effect=side_effect)

        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert "Relationship already exists" in result["error"]["message"]
        assert result["error"]["type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_create_relationship_with_notes(self, setup_services):
        """Test creating relationship with notes"""
        services = setup_services

        # Mock concepts exist check, then duplicate check (no duplicates)
        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        # Mock projection success
        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=True)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001",
                target_id="concept-002",
                relationship_type="relates_to",
                strength=0.8,
                notes="These concepts are related",
            )

            assert result["success"] is True
            assert result["data"]["relationship_id"] is not None

            # Verify event contains notes
            event_call = services["event_store"].append_event.call_args
            event = event_call[0][0]
            assert event.event_data.get("description") == "These concepts are related"
            assert event.event_data.get("strength") == 0.8

    @pytest.mark.asyncio
    async def test_create_relationship_projection_failure(self, setup_services):
        """Test handling of projection failure"""
        services = setup_services

        # Mock concepts exist check, then duplicate check (no duplicates)
        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        # Mock projection failure
        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=False)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001",
                target_id="concept-002",
                relationship_type="prerequisite",
                strength=1.0,
            )

            assert result["success"] is False
        assert "error" in result
        assert any(phrase in result["error"]["message"].lower() for phrase in ["failed", "unavailable", "temporarily unavailable"])

    @pytest.mark.asyncio
    async def test_create_relationship_missing_source_id(self, setup_services):
        """Test validation of missing source_id"""

        result = await relationship_tools.create_relationship(
            source_id="", target_id="concept-002", relationship_type="prerequisite", strength=1.0
        )

        assert result["success"] is False
        assert "error" in result
        assert "source_id is required" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_relationship_missing_target_id(self, setup_services):
        """Test validation of missing target_id"""

        result = await relationship_tools.create_relationship(
            source_id="concept-001", target_id=None, relationship_type="prerequisite", strength=1.0
        )

        assert result["success"] is False
        assert "error" in result
        assert "target_id is required" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_relationship_unexpected_error(self, setup_services):
        """Test handling of unexpected errors"""
        services = setup_services

        services["neo4j"].execute_read = Mock(side_effect=Exception("Database error"))

        result = await relationship_tools.create_relationship(
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="prerequisite",
            strength=1.0,
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"]["type"] in ["internal_error", "unexpected_error"]


class TestRelationshipTypes:
    """Tests for different relationship types"""

    @pytest.mark.asyncio
    async def test_prerequisite_relationship(self, setup_services):
        """Test creating prerequisite relationship"""
        services = setup_services

        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=True)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001", target_id="concept-002", relationship_type="prerequisite"
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_relates_to_relationship(self, setup_services):
        """Test creating relates_to relationship"""
        services = setup_services

        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=True)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001", target_id="concept-002", relationship_type="relates_to"
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_includes_relationship(self, setup_services):
        """Test creating includes relationship"""
        services = setup_services

        services["neo4j"].execute_read = Mock(
            side_effect=[
                [{"concept_id": "concept-001"}, {"concept_id": "concept-002"}],  # concepts exist
                [],  # no duplicates
            ]
        )

        with patch("projections.neo4j_projection.Neo4jProjection") as mock_projection_class:
            mock_projection = Mock()
            mock_projection.project_event = Mock(return_value=True)
            mock_projection_class.return_value = mock_projection

            result = await relationship_tools.create_relationship(
                source_id="concept-001", target_id="concept-002", relationship_type="includes"
            )

            assert result["success"] is True


class TestNormalizeRelationshipType:
    """Tests for _normalize_relationship_type helper function"""

    def test_normalize_prerequisite(self):
        """Test normalizing prerequisite type"""
        result = relationship_tools._normalize_relationship_type("prerequisite")
        assert result == "PREREQUISITE"

    def test_normalize_relates_to(self):
        """Test normalizing relates_to type"""
        result = relationship_tools._normalize_relationship_type("relates_to")
        assert result == "RELATES_TO"

    def test_normalize_includes(self):
        """Test normalizing includes type"""
        result = relationship_tools._normalize_relationship_type("includes")
        assert result == "INCLUDES"

    def test_normalize_contains(self):
        """Test normalizing contains type"""
        result = relationship_tools._normalize_relationship_type("contains")
        assert result == "CONTAINS"

    def test_normalize_uppercase_input(self):
        """Test that uppercase input is handled correctly"""
        result = relationship_tools._normalize_relationship_type("PREREQUISITE")
        assert result == "PREREQUISITE"

    def test_normalize_mixed_case_input(self):
        """Test that mixed case input is handled correctly"""
        result = relationship_tools._normalize_relationship_type("PreRequisite")
        assert result == "PREREQUISITE"

    def test_normalize_invalid_type(self):
        """Test that invalid type raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            relationship_tools._normalize_relationship_type("invalid_type")
        assert "Invalid relationship type" in str(exc_info.value)
        assert "Must be one of" in str(exc_info.value)

    def test_normalize_empty_string(self):
        """Test that empty string raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            relationship_tools._normalize_relationship_type("")
        assert "Must be a non-empty string" in str(exc_info.value)

    def test_normalize_none(self):
        """Test that None raises ValueError"""
        with pytest.raises(ValueError) as exc_info:
            relationship_tools._normalize_relationship_type(None)
        assert "Must be a non-empty string" in str(exc_info.value)


class TestRelationshipTypeEnum:
    """Tests for RelationshipType enum"""

    def test_enum_values(self):
        """Test that enum has correct values"""
        assert relationship_tools.RelationshipType.PREREQUISITE.value == "PREREQUISITE"
        assert relationship_tools.RelationshipType.RELATES_TO.value == "RELATES_TO"
        assert relationship_tools.RelationshipType.INCLUDES.value == "INCLUDES"
        assert relationship_tools.RelationshipType.CONTAINS.value == "CONTAINS"

    def test_enum_membership(self):
        """Test that enum values can be checked for membership"""
        assert "PREREQUISITE" in [t.value for t in relationship_tools.RelationshipType]
        assert "RELATES_TO" in [t.value for t in relationship_tools.RelationshipType]
        assert "INCLUDES" in [t.value for t in relationship_tools.RelationshipType]
        assert "CONTAINS" in [t.value for t in relationship_tools.RelationshipType]

    def test_enum_iteration(self):
        """Test that enum can be iterated"""
        types = [t.value for t in relationship_tools.RelationshipType]
        assert len(types) == 4
        assert "PREREQUISITE" in types

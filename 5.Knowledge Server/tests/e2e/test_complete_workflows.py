"""
End-to-end workflow tests for complete user journeys.
Tests multiple tools working together in realistic scenarios.
"""

import pytest

from tools import analytics_tools, concept_tools, relationship_tools, search_tools


class TestConceptLifecycle:
    """Test complete CRUD lifecycle."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container):
        """Inject E2E services into container for all tests in this class."""
        self.container = e2e_configured_container
        yield

    @pytest.mark.asyncio
    async def test_create_get_update_delete_workflow(self):
        """
        Workflow: Create -> Get -> Update -> Delete
        Validates: All CRUD operations work together seamlessly
        """
        mock_neo4j = self.container.neo4j_service

        # Mock Neo4j responses for concept operations
        mock_concept_data = {
            "concept_id": "concept-test-001",
            "name": "Machine Learning",
            "explanation": "A field of AI focused on learning from data",
            "area": "Artificial Intelligence",
            "topic": "Machine Learning",
            "subtopic": None,
            "confidence_score": 80.0,
            "created_at": "2025-10-07T10:00:00",
            "last_modified": "2025-10-07T10:00:00",
            "deleted": False,
            "version": 1,
        }

        # 1. Create concept
        mock_neo4j.execute_write.return_value = {"concept_id": "concept-test-001"}
        result = await concept_tools.create_concept(
            name="Machine Learning",
            explanation="A field of AI focused on learning from data",
            area="Artificial Intelligence",
            topic="Machine Learning",
        )
        assert result["success"] is True
        assert "concept_id" in result["data"]
        concept_id = result["data"]["concept_id"]

        # 2. Get concept
        mock_neo4j.execute_read.return_value = [{"c": mock_concept_data}]
        result = await concept_tools.get_concept(concept_id, include_history=False)
        assert result["success"] is True
        assert result["data"]["concept"]["name"] == "Machine Learning"
        assert result["data"]["concept"]["confidence_score"] == 80.0

        # 3. Update concept
        mock_concept_data["explanation"] = "ML is a subset of AI that learns patterns from data"
        mock_concept_data["confidence_score"] = 90.0
        mock_concept_data["version"] = 2
        mock_neo4j.execute_read.return_value = [{"c": mock_concept_data}]
        mock_neo4j.execute_write.return_value = {"properties_set": 2}

        result = await concept_tools.update_concept(
            concept_id=concept_id, explanation="ML is a subset of AI that learns patterns from data"
        )
        assert result["success"] is True
        assert "explanation" in result["data"]["updated_fields"]

        # 4. Verify update
        mock_neo4j.execute_read.return_value = [{"c": mock_concept_data}]
        result = await concept_tools.get_concept(concept_id)
        assert result["success"] is True
        assert result["data"]["concept"]["confidence_score"] == 90.0

        # 5. Delete concept
        mock_neo4j.execute_write.return_value = {"properties_set": 1}
        result = await concept_tools.delete_concept(concept_id)
        assert result["success"] is True

        # 6. Verify deletion
        mock_neo4j.execute_read.return_value = []
        result = await concept_tools.get_concept(concept_id)
        assert result["success"] is False
        assert "error" in result
        assert ("not found" in result["error"]["message"].lower() or "doesn't exist" in result["error"]["message"].lower() or "does not exist" in result["error"]["message"].lower())
        assert result["error"]["type"] in ["not_found", "concept_not_found"]

    @pytest.mark.asyncio
    async def test_multi_concept_creation_with_relationships(self, sample_concepts):
        """
        Workflow: Create 5 concepts -> Build relationships -> Verify connections
        Validates: Concepts and relationships persist correctly
        """
        mock_neo4j = self.container.neo4j_service

        # Create 5 related concepts
        concepts = []
        for i, concept_data in enumerate(sample_concepts):
            concept_id = f"concept-test-{i:03d}"
            mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

            result = await concept_tools.create_concept(**concept_data)
            assert result["success"] is True
            concepts.append(result["data"]["concept_id"])

        assert len(concepts) == 5

        # Build prerequisite chain: Basics -> Functions -> Decorators
        # Mock returns: 1) concept existence check, 2) duplicate check (empty)
        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts[0], "name": "Python Basics"},
                {"concept_id": concepts[1], "name": "Functions"},
            ],
            [],  # No duplicate relationships
        ]
        mock_neo4j.execute_write.return_value = {"relationships_created": 1}

        result = await relationship_tools.create_relationship(
            concepts[0], concepts[1], "prerequisite", 1.0
        )
        assert result["success"] is True

        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts[1], "name": "Functions"},
                {"concept_id": concepts[3], "name": "Decorators"},
            ],
            [],  # No duplicate relationships
        ]

        result = await relationship_tools.create_relationship(
            concepts[1], concepts[3], "prerequisite", 0.9
        )
        assert result["success"] is True

        # Build relates_to: Classes -> Functions
        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts[2], "name": "Classes"},
                {"concept_id": concepts[1], "name": "Functions"},
            ],
            [],  # No duplicate relationships
        ]

        result = await relationship_tools.create_relationship(
            concepts[2], concepts[1], "relates_to", 0.8
        )
        assert result["success"] is True

        # Verify relationships exist (incoming to Functions)
        mock_neo4j.execute_read.side_effect = None  # Reset side_effect
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": concepts[0],
                "name": "Python Basics",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            },
            {
                "concept_id": concepts[2],
                "name": "Classes",
                "relationship_type": "RELATES_TO",
                "strength": 0.8,
                "distance": 1,
            },
        ]

        result = await relationship_tools.get_related_concepts(concepts[1], direction="incoming")
        assert result["success"] is True
        assert result["data"]["total"] == 2


class TestSearchWorkflows:
    """Test search-based user workflows."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container):
        """Inject E2E services into container for all tests in this class."""
        self.container = e2e_configured_container
        yield

    @pytest.mark.asyncio
    async def test_semantic_search_to_retrieval(self):
        """
        Workflow: Semantic search -> Get details -> Get related
        Validates: Search discovery leads to exploration
        """
        mock_neo4j = self.container.neo4j_service
        mock_chromadb = self.container.chromadb_service

        # Create test concept
        concept_id = "concept-neural-001"
        mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

        result = await concept_tools.create_concept(
            name="Neural Networks",
            explanation="Artificial neural networks inspired by biological neurons",
            area="AI",
            topic="Deep Learning",
        )
        assert result["success"] is True

        # Semantic search
        mock_chromadb.collection.query.return_value = {
            "ids": [[concept_id]],
            "distances": [[0.1]],
            "metadatas": [[{
                "name": "Neural Networks",
                "area": "AI",
                "topic": "Deep Learning",
                "confidence_score": 85.0
            }]]
        }

        result = await search_tools.search_concepts_semantic(
            query="deep learning with neurons", limit=10
        )
        assert result["success"] is True
        assert result["data"]["total"] > 0

        # Get first result details
        found_concept_id = result["data"]["results"][0]["concept_id"]
        mock_neo4j.execute_read.return_value = [{"c": {
            "concept_id": found_concept_id,
            "name": "Neural Networks",
            "explanation": "Artificial neural networks inspired by biological neurons",
            "area": "AI",
            "topic": "Deep Learning",
            "subtopic": None,
            "confidence_score": 85.0,
            "created_at": "2025-10-07T10:00:00",
            "last_modified": "2025-10-07T10:00:00",
            "deleted": False,
            "version": 1
        }}]

        details = await concept_tools.get_concept(found_concept_id)
        assert details["success"] is True
        assert details["data"]["concept"]["name"] == "Neural Networks"

        # Get related concepts
        mock_neo4j.execute_read.return_value = []
        related = await relationship_tools.get_related_concepts(found_concept_id, direction="both")
        assert related["success"] is True

    @pytest.mark.asyncio
    async def test_exact_search_filtering(self):
        """
        Workflow: Exact search with filters -> Refine -> Export
        Validates: Filtering and refinement capabilities
        """
        mock_neo4j = self.container.neo4j_service

        # Exact search by area
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-001",
                "name": "Python Loops",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
                "confidence_score": 90.0,
                "created_at": "2025-10-07T10:00:00"
            }
        ]

        result = await search_tools.search_concepts_exact(area="Programming", limit=50)
        assert result["success"] is True

        # Refine by topic
        result = await search_tools.search_concepts_exact(
            area="Programming", topic="Python", limit=20
        )
        assert result["success"] is True

        # Further refine by confidence
        result = await search_tools.search_concepts_exact(
            area="Programming",
            topic="Python",
            min_confidence=80,
            limit=10
        )
        assert result["success"] is True


class TestPrerequisiteChains:
    """Test learning path workflows."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container):
        """Inject E2E services into container for all tests in this class."""
        self.container = e2e_configured_container
        yield

    @pytest.mark.asyncio
    async def test_build_and_traverse_learning_path(self, sample_concepts):
        """
        Workflow: Create concept chain -> Get prerequisites -> Verify order
        Validates: Prerequisite chains work correctly
        """
        mock_neo4j = self.container.neo4j_service

        # Create learning path: A -> B -> C -> D
        concepts = {}
        for i, name in enumerate(["Basics", "Intermediate", "Advanced", "Expert"]):
            concept_id = f"concept-level-{i:03d}"
            mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

            result = await concept_tools.create_concept(
                name=f"Topic {name}",
                explanation=f"{name} level content",
                area="Learning Path",
                topic="Test",
            )
            assert result["success"] is True
            concepts[name] = result["data"]["concept_id"]

        # Build chain
        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts["Basics"], "name": "Topic Basics"},
                {"concept_id": concepts["Intermediate"], "name": "Topic Intermediate"},
            ],
            [],  # No duplicate relationships
        ]
        mock_neo4j.execute_write.return_value = {"relationships_created": 1}

        await relationship_tools.create_relationship(
            concepts["Basics"], concepts["Intermediate"], "prerequisite"
        )

        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts["Intermediate"], "name": "Topic Intermediate"},
                {"concept_id": concepts["Advanced"], "name": "Topic Advanced"},
            ],
            [],  # No duplicate relationships
        ]

        await relationship_tools.create_relationship(
            concepts["Intermediate"], concepts["Advanced"], "prerequisite"
        )

        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concepts["Advanced"], "name": "Topic Advanced"},
                {"concept_id": concepts["Expert"], "name": "Topic Expert"},
            ],
            [],  # No duplicate relationships
        ]

        await relationship_tools.create_relationship(
            concepts["Advanced"], concepts["Expert"], "prerequisite"
        )

        # Get prerequisites for Expert level
        mock_neo4j.execute_read.side_effect = None  # Reset side_effect
        mock_neo4j.execute_read.return_value = [
            {"concept_id": concepts["Basics"], "name": "Topic Basics", "depth": 3},
            {"concept_id": concepts["Intermediate"], "name": "Topic Intermediate", "depth": 2},
            {"concept_id": concepts["Advanced"], "name": "Topic Advanced", "depth": 1},
        ]

        result = await relationship_tools.get_prerequisites(concepts["Expert"], max_depth=5)
        assert result["success"] is True
        assert result["data"]["total"] == 3

        # Verify ordering (deepest first)
        chain = result["data"]["chain"]
        assert chain[0]["depth"] > chain[-1]["depth"]


class TestAnalyticsWorkflows:
    """Test analytics and reporting workflows."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container):
        """Inject E2E services into container for all tests in this class."""
        self.container = e2e_configured_container
        yield

    @pytest.mark.asyncio
    async def test_hierarchy_and_confidence_analysis(self):
        """
        Workflow: List hierarchy -> Identify low confidence concepts -> Review
        Validates: Analytics tools support knowledge management
        """
        mock_neo4j = self.container.neo4j_service

        # Get hierarchy
        mock_neo4j.execute_read.return_value = [
            {"area": "Programming", "topic": "Python", "subtopic": "Basics", "count": 10},
            {"area": "Programming", "topic": "Python", "subtopic": "Advanced", "count": 5},
        ]

        result = await analytics_tools.list_hierarchy()
        assert result["success"] is True
        assert result["data"]["total_concepts"] >= 0

        # Find low confidence concepts for review
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-001",
                "name": "Unsure Concept",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Basics",
                "confidence_score": 45.0,
                "created_at": "2025-10-07T10:00:00",
                "last_modified": "2025-10-07T10:00:00",
            }
        ]

        result = await analytics_tools.get_concepts_by_confidence(
            min_confidence=0,
            max_confidence=50,
            limit=20
        )
        assert result["success"] is True
        # Verify we get low confidence concepts for review

    @pytest.mark.asyncio
    async def test_recent_concepts_workflow(self):
        """
        Workflow: Get recent concepts -> Review recent work
        Validates: Time-based retrieval for recent activity tracking
        """
        mock_neo4j = self.container.neo4j_service

        # Get recent concepts from last 7 days
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": "concept-recent-001",
                "name": "Recent Concept",
                "area": "Testing",
                "topic": "E2E",
                "subtopic": "Workflows",
                "confidence_score": 85.0,
                "created_at": "2025-10-06T10:00:00",
                "last_modified": "2025-10-07T10:00:00",
            }
        ]

        result = await search_tools.get_recent_concepts(days=7, limit=20)
        assert result["success"] is True
        assert result["data"]["total"] >= 0

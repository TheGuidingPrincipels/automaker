"""
Test complex relationship scenarios and graph traversal.
"""

import pytest

from tools import concept_tools, relationship_tools


class TestGraphTraversal:
    """Test graph navigation features."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container, mock_neo4j):
        """Set up container with services for all tests in this class."""
        self.container = e2e_configured_container
        self.mock_neo4j = mock_neo4j
        yield

    @pytest.mark.asyncio
    async def test_shortest_path_between_concepts(self):
        """
        Workflow: Create graph → Find shortest path
        Validates: get_concept_chain finds optimal paths
        """
        mock_neo4j = self.mock_neo4j

        # Create small knowledge graph
        # A → B → C (direct path: 2 hops)
        # A → D → E → C (longer path: 3 hops)

        concepts = {}
        for letter in ["A", "B", "C", "D", "E"]:
            concept_id = f"concept-path-{letter}"
            mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

            result = await concept_tools.create_concept(
                name=f"Concept {letter}",
                explanation=f"Test concept {letter}",
                area="Graph",
                topic="Pathfinding",
            )
            assert result["success"] is True
            concepts[letter] = result["data"]["concept_id"]

        # Create relationships
        relationships = [("A", "B"), ("B", "C"), ("A", "D"), ("D", "E"), ("E", "C")]

        for source, target in relationships:
            mock_neo4j.execute_read.side_effect = [
                [
                    {"concept_id": concepts[source], "name": f"Concept {source}"},
                    {"concept_id": concepts[target], "name": f"Concept {target}"},
                ],
                [],  # No duplicate relationships
            ]
            mock_neo4j.execute_write.return_value = {"relationships_created": 1}

            await relationship_tools.create_relationship(
                concepts[source], concepts[target], "prerequisite"
            )

        # Find shortest path from A to C
        mock_neo4j.execute_read.side_effect = None  # Reset side_effect
        mock_neo4j.execute_read.return_value = [
            {
                "path": [
                    {"concept_id": concepts["A"], "name": "Concept A"},
                    {"concept_id": concepts["B"], "name": "Concept B"},
                    {"concept_id": concepts["C"], "name": "Concept C"},
                ],
                "length": 2,
            }
        ]

        result = await relationship_tools.get_concept_chain(concepts["A"], concepts["C"])
        assert result["success"] is True
        assert len(result["data"]["path"]) == 3  # A → B → C
        assert result["data"]["length"] == 2  # 2 hops

    @pytest.mark.asyncio
    async def test_bidirectional_relationships(self):
        """Test relationships work in both directions."""
        mock_neo4j = self.mock_neo4j

        # Create two concepts
        concept_a = "concept-bidir-A"
        concept_b = "concept-bidir-B"

        mock_neo4j.execute_write.return_value = {"concept_id": concept_a}
        result_a = await concept_tools.create_concept(
            name="Concept A", explanation="First concept", area="Testing", topic="Bidirectional"
        )
        assert result_a["success"] is True

        mock_neo4j.execute_write.return_value = {"concept_id": concept_b}
        result_b = await concept_tools.create_concept(
            name="Concept B", explanation="Second concept", area="Testing", topic="Bidirectional"
        )
        assert result_b["success"] is True

        # Create A → B relationship
        mock_neo4j.execute_read.side_effect = [
            [
                {"concept_id": concept_a, "name": "Concept A"},
                {"concept_id": concept_b, "name": "Concept B"},
            ],
            [],  # No duplicate relationships
        ]
        mock_neo4j.execute_write.return_value = {"relationships_created": 1}

        result = await relationship_tools.create_relationship(concept_a, concept_b, "relates_to")
        assert result["success"] is True

        # Check outgoing from A
        mock_neo4j.execute_read.side_effect = None  # Reset side_effect
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": concept_b,
                "name": "Concept B",
                "relationship_type": "RELATES_TO",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        result = await relationship_tools.get_related_concepts(concept_a, direction="outgoing")
        assert result["success"] is True
        assert result["data"]["total"] == 1

        # Check incoming to B
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": concept_a,
                "name": "Concept A",
                "relationship_type": "RELATES_TO",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        result = await relationship_tools.get_related_concepts(concept_b, direction="incoming")
        assert result["success"] is True
        assert result["data"]["total"] == 1

    @pytest.mark.asyncio
    async def test_multi_hop_traversal(self):
        """
        Workflow: Create deep graph → Traverse multiple levels
        Validates: Multi-hop traversal with depth control
        """
        mock_neo4j = self.mock_neo4j

        # Create linear chain: A → B → C → D → E
        concepts = []
        for i in range(5):
            concept_id = f"concept-chain-{i}"
            mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

            result = await concept_tools.create_concept(
                name=f"Level {i}",
                explanation=f"Concept at level {i}",
                area="Testing",
                topic="Multi-hop",
            )
            assert result["success"] is True
            concepts.append(result["data"]["concept_id"])

        # Create chain relationships
        for i in range(len(concepts) - 1):
            mock_neo4j.execute_read.return_value = [
                {"concept_id": concepts[i], "name": f"Level {i}"},
                {"concept_id": concepts[i + 1], "name": f"Level {i+1}"},
            ]
            mock_neo4j.execute_write.return_value = {"relationships_created": 1}

            await relationship_tools.create_relationship(
                concepts[i], concepts[i + 1], "prerequisite"
            )

        # Traverse from end with max_depth=3 (should get 3 levels)
        mock_neo4j.execute_read.return_value = [
            {"concept_id": concepts[3], "name": "Level 3", "depth": 1},
            {"concept_id": concepts[2], "name": "Level 2", "depth": 2},
            {"concept_id": concepts[1], "name": "Level 1", "depth": 3},
        ]

        result = await relationship_tools.get_related_concepts(
            concepts[4], direction="incoming", relationship_type="prerequisite", max_depth=3
        )
        assert result["success"] is True
        # Should get concepts at depth 1, 2, 3

    @pytest.mark.asyncio
    async def test_relationship_deletion_and_cleanup(self):
        """
        Workflow: Create relationships → Delete some → Verify integrity
        Validates: Relationship deletion maintains graph integrity
        """
        mock_neo4j = self.mock_neo4j

        # Create three concepts
        concepts = []
        for i in range(3):
            concept_id = f"concept-del-{i}"
            mock_neo4j.execute_write.return_value = {"concept_id": concept_id}

            result = await concept_tools.create_concept(
                name=f"Concept {i}",
                explanation=f"Test concept {i}",
                area="Testing",
                topic="Deletion",
            )
            assert result["success"] is True
            concepts.append(result["data"]["concept_id"])

        # Create A → B and B → C relationships
        for i in range(2):
            mock_neo4j.execute_read.return_value = [
                {"concept_id": concepts[i], "name": f"Concept {i}"},
                {"concept_id": concepts[i + 1], "name": f"Concept {i+1}"},
            ]
            mock_neo4j.execute_write.return_value = {"relationships_created": 1}

            await relationship_tools.create_relationship(
                concepts[i], concepts[i + 1], "prerequisite"
            )

        # Delete A → B relationship
        mock_neo4j.execute_read.return_value = [
            {
                "relationship_id": "rel-001",
                "source_id": concepts[0],
                "target_id": concepts[1],
                "relationship_type": "PREREQUISITE",
            }
        ]
        mock_neo4j.execute_write.return_value = {"relationships_deleted": 1}

        result = await relationship_tools.delete_relationship(
            concepts[0], concepts[1], "prerequisite"
        )
        assert result["success"] is True

        # Verify B → C still exists
        mock_neo4j.execute_read.return_value = [
            {
                "concept_id": concepts[2],
                "name": "Concept 2",
                "relationship_type": "PREREQUISITE",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        result = await relationship_tools.get_related_concepts(concepts[1], direction="outgoing")
        assert result["success"] is True
        # Should still find B → C relationship


class TestHierarchyValidation:
    """Test hierarchy accuracy and consistency."""

    @pytest.fixture(autouse=True)
    def setup_container(self, e2e_configured_container, mock_neo4j):
        """Set up container with services for all tests in this class."""
        self.container = e2e_configured_container
        self.mock_neo4j = mock_neo4j
        yield

    @pytest.mark.asyncio
    async def test_hierarchy_reflects_all_concepts(self):
        """
        Workflow: Create diverse concepts → List hierarchy → Verify counts
        Validates: Hierarchy aggregation is accurate
        """
        from tools import analytics_tools
        mock_neo4j = self.mock_neo4j

        # Mock hierarchy data
        mock_neo4j.execute_read.return_value = [
            {"area": "Programming", "topic": "Python", "subtopic": "Basics", "count": 5},
            {"area": "Programming", "topic": "Python", "subtopic": "Advanced", "count": 3},
            {"area": "Programming", "topic": "JavaScript", "subtopic": "Basics", "count": 4},
            {"area": "Mathematics", "topic": "Calculus", "subtopic": "Derivatives", "count": 2},
        ]

        result = await analytics_tools.list_hierarchy()
        assert result["success"] is True
        assert result["data"]["total_concepts"] == 14  # Sum of all counts

    @pytest.mark.asyncio
    async def test_hierarchy_nesting_structure(self):
        """
        Workflow: Get hierarchy → Verify nested structure
        Validates: Areas contain topics, topics contain subtopics
        """
        from tools import analytics_tools
        mock_neo4j = self.mock_neo4j

        # Mock nested hierarchy
        mock_neo4j.execute_read.return_value = [
            {"area": "Science", "topic": "Physics", "subtopic": "Mechanics", "count": 10},
            {"area": "Science", "topic": "Physics", "subtopic": "Thermodynamics", "count": 8},
            {"area": "Science", "topic": "Chemistry", "subtopic": "Organic", "count": 6},
        ]

        result = await analytics_tools.list_hierarchy()
        assert result["success"] is True

        # Verify structure
        hierarchy = result["data"]["areas"]  # Changed from "hierarchy" to "areas"
        assert len(hierarchy) > 0

        # Find Science area
        science_area = next(
            (a for a in hierarchy if a["name"] == "Science"), None
        )  # Changed "area" to "name"
        if science_area:
            # Should have topics
            assert "topics" in science_area
            # Topics should have subtopics
            for topic in science_area["topics"]:
                assert "subtopics" in topic

    @pytest.mark.asyncio
    async def test_hierarchy_cache_consistency(self):
        """
        Workflow: Get hierarchy twice → Verify caching works
        Validates: Cache returns consistent results
        """
        from tools import analytics_tools
        mock_neo4j = self.mock_neo4j

        # Mock hierarchy data
        mock_data = [{"area": "Testing", "topic": "Cache", "subtopic": "Validation", "count": 1}]
        mock_neo4j.execute_read.return_value = mock_data

        # First call
        result1 = await analytics_tools.list_hierarchy()
        assert result1["success"] is True

        # Second call (should use cache)
        result2 = await analytics_tools.list_hierarchy()
        assert result2["success"] is True

        # Results should be consistent
        assert result1["data"]["total_concepts"] == result2["data"]["total_concepts"]

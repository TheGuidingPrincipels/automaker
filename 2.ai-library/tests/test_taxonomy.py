"""Tests for taxonomy management."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.taxonomy.schema import (
    CategoryProposal,
    CategoryStatus,
    ClassificationResult,
    TaxonomyConfig,
    TaxonomyNode,
)
from src.taxonomy.manager import TaxonomyManager


@pytest.fixture
def sample_taxonomy_yaml():
    """Create a sample taxonomy YAML for testing."""
    return {
        "version": "1.0",
        "classification": {
            "fast_tier_confidence_threshold": 0.75,
            "new_category_confidence_threshold": 0.85,
            "auto_approve_level3_plus": True,
        },
        "categories": {
            "technical": {
                "description": "Technical knowledge",
                "locked": True,
                "children": {
                    "programming": {
                        "description": "Programming languages",
                        "locked": True,
                        "children": {},
                    },
                    "architecture": {
                        "description": "System architecture",
                        "locked": True,
                        "children": {
                            "microservices": {
                                "description": "Microservices patterns",
                                "locked": False,
                                "children": {},
                            }
                        },
                    },
                },
            },
            "domain": {
                "description": "Domain knowledge",
                "locked": True,
                "children": {
                    "business": {
                        "description": "Business processes",
                        "locked": True,
                        "children": {},
                    },
                },
            },
        },
        "proposed_categories": [],
        "evolution": {
            "min_content_for_split": 10,
            "max_items_per_category": 100,
            "similarity_threshold": 0.8,
        },
    }


@pytest.fixture
def temp_taxonomy_file(sample_taxonomy_yaml):
    """Create a temporary taxonomy file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(sample_taxonomy_yaml, f)
        return Path(f.name)


@pytest.fixture
def taxonomy_manager(temp_taxonomy_file):
    """Create a taxonomy manager with loaded config."""
    manager = TaxonomyManager(config_path=temp_taxonomy_file)
    manager.load()
    return manager


class TestTaxonomyNode:
    """Tests for TaxonomyNode model."""

    def test_create_node(self):
        """Test creating a taxonomy node."""
        node = TaxonomyNode(
            name="python",
            description="Python programming language",
            locked=False,
            level=3,
            parent_path="technical/programming",
        )
        assert node.name == "python"
        assert node.full_path == "technical/programming/python"
        assert node.level == 3
        assert node.status == CategoryStatus.ACTIVE

    def test_add_child(self):
        """Test adding a child node."""
        parent = TaxonomyNode(name="programming", level=2)
        child = TaxonomyNode(name="python")

        parent.add_child(child)

        assert "python" in parent.children
        assert child.parent_path == "programming"
        assert child.level == 3

    def test_get_child(self):
        """Test getting a child by name."""
        parent = TaxonomyNode(
            name="programming",
            children={
                "python": TaxonomyNode(name="python"),
                "rust": TaxonomyNode(name="rust"),
            },
        )

        assert parent.get_child("python") is not None
        assert parent.get_child("java") is None


class TestTaxonomyConfig:
    """Tests for TaxonomyConfig model."""

    def test_get_category_by_path(self, taxonomy_manager):
        """Test getting category by full path."""
        config = taxonomy_manager.config

        # Get root level
        tech = config.get_category_by_path("technical")
        assert tech is not None
        assert tech.name == "technical"

        # Get nested
        prog = config.get_category_by_path("technical/programming")
        assert prog is not None
        assert prog.name == "programming"

        # Get deeply nested
        micro = config.get_category_by_path("technical/architecture/microservices")
        assert micro is not None
        assert micro.name == "microservices"

        # Non-existent
        assert config.get_category_by_path("nonexistent") is None
        assert config.get_category_by_path("technical/nonexistent") is None

    def test_validate_path(self, taxonomy_manager):
        """Test path validation."""
        config = taxonomy_manager.config

        assert config.validate_path("technical") is True
        assert config.validate_path("technical/programming") is True
        assert config.validate_path("nonexistent") is False

    def test_get_all_paths(self, taxonomy_manager):
        """Test getting all valid paths."""
        config = taxonomy_manager.config
        paths = config.get_all_paths()

        assert "technical" in paths
        assert "technical/programming" in paths
        assert "technical/architecture" in paths
        assert "technical/architecture/microservices" in paths
        assert "domain" in paths
        assert "domain/business" in paths


class TestTaxonomyManager:
    """Tests for TaxonomyManager."""

    def test_load_taxonomy(self, taxonomy_manager):
        """Test loading taxonomy from YAML."""
        assert taxonomy_manager.config is not None
        assert taxonomy_manager.config.version == "1.0"
        assert "technical" in taxonomy_manager.config.categories

    def test_validate_path(self, taxonomy_manager):
        """Test path validation through manager."""
        assert taxonomy_manager.validate_path("technical") is True
        assert taxonomy_manager.validate_path("technical/programming") is True
        assert taxonomy_manager.validate_path("invalid/path") is False

    def test_get_category(self, taxonomy_manager):
        """Test getting category through manager."""
        cat = taxonomy_manager.get_category("technical/architecture")
        assert cat is not None
        assert cat.description == "System architecture"

    def test_get_all_paths(self, taxonomy_manager):
        """Test getting all paths through manager."""
        paths = taxonomy_manager.get_all_paths()
        assert len(paths) > 0
        assert "technical" in paths

    def test_propose_category(self, taxonomy_manager):
        """Test proposing a new category."""
        proposal = CategoryProposal(
            name="kubernetes",
            description="Kubernetes orchestration patterns",
            parent_path="technical/architecture/microservices",
            confidence=0.9,
        )

        # Should auto-approve since confidence > threshold and Level 3+
        proposed = taxonomy_manager.propose_category(proposal)
        assert proposed.status == "approved"

        # Verify category was added
        cat = taxonomy_manager.get_category(
            "technical/architecture/microservices/kubernetes"
        )
        assert cat is not None
        assert cat.name == "kubernetes"

    def test_propose_category_low_confidence(self, taxonomy_manager):
        """Test proposing a category with low confidence stays pending."""
        proposal = CategoryProposal(
            name="docker",
            description="Docker container patterns",
            parent_path="technical/architecture/microservices",
            confidence=0.5,  # Below threshold
        )

        proposed = taxonomy_manager.propose_category(proposal)
        assert proposed.status == "pending"

        # Should be in pending list
        pending = taxonomy_manager.get_pending_proposals()
        assert len(pending) == 1
        assert pending[0].name == "docker"

    def test_propose_category_invalid_parent(self, taxonomy_manager):
        """Test proposing with invalid parent raises error."""
        proposal = CategoryProposal(
            name="test",
            description="Test category",
            parent_path="nonexistent/path",
            confidence=0.9,
        )

        with pytest.raises(ValueError, match="Parent path not found"):
            taxonomy_manager.propose_category(proposal)

    def test_propose_category_under_level1(self, taxonomy_manager):
        """Test proposing under Level 1 raises error."""
        proposal = CategoryProposal(
            name="test",
            description="Test category",
            parent_path="technical",  # Level 1, not allowed
            confidence=0.9,
        )

        with pytest.raises(ValueError, match="Cannot propose category under Level 1"):
            taxonomy_manager.propose_category(proposal)

    def test_approve_proposal(self, taxonomy_manager):
        """Test manually approving a pending proposal."""
        # First create a pending proposal
        proposal = CategoryProposal(
            name="terraform",
            description="Terraform IaC patterns",
            parent_path="technical/architecture/microservices",
            confidence=0.5,
        )
        taxonomy_manager.propose_category(proposal)

        # Now approve it
        result = taxonomy_manager.approve_proposal(
            "technical/architecture/microservices/terraform",
            review_notes="Approved for DevOps category",
        )
        assert result is True

        # Verify category was created
        cat = taxonomy_manager.get_category(
            "technical/architecture/microservices/terraform"
        )
        assert cat is not None

    def test_reject_proposal(self, taxonomy_manager):
        """Test rejecting a pending proposal."""
        proposal = CategoryProposal(
            name="rejected_cat",
            description="Should be rejected",
            parent_path="technical/architecture/microservices",
            confidence=0.5,
        )
        taxonomy_manager.propose_category(proposal)

        result = taxonomy_manager.reject_proposal(
            "technical/architecture/microservices/rejected_cat",
            reason="Not needed",
        )
        assert result is True

        # Should not be in pending anymore (status changed to rejected)
        pending = taxonomy_manager.get_pending_proposals()
        assert len([p for p in pending if p.name == "rejected_cat"]) == 0

    def test_save_taxonomy(self, taxonomy_manager, temp_taxonomy_file):
        """Test saving taxonomy back to YAML."""
        # Make a change
        proposal = CategoryProposal(
            name="saved_cat",
            description="Category to save",
            parent_path="technical/architecture/microservices",
            confidence=0.9,
        )
        taxonomy_manager.propose_category(proposal)

        # Save
        taxonomy_manager.save()

        # Reload and verify
        new_manager = TaxonomyManager(config_path=temp_taxonomy_file)
        new_manager.load()

        cat = new_manager.get_category(
            "technical/architecture/microservices/saved_cat"
        )
        assert cat is not None

    def test_needs_save(self, taxonomy_manager):
        """Test dirty flag tracking."""
        assert taxonomy_manager.needs_save() is False

        proposal = CategoryProposal(
            name="test",
            description="Test category for dirty flag tracking",
            parent_path="technical/architecture/microservices",
            confidence=0.9,
        )
        taxonomy_manager.propose_category(proposal)

        assert taxonomy_manager.needs_save() is True


class TestClassificationResult:
    """Tests for ClassificationResult model."""

    def test_create_result(self):
        """Test creating a classification result."""
        result = ClassificationResult(
            primary_path="technical/programming",
            primary_confidence=0.85,
            alternatives=[
                ("technical/architecture", 0.6),
                ("domain/business", 0.3),
            ],
            tier_used="fast",
            processing_time_ms=15.5,
        )

        assert result.primary_path == "technical/programming"
        assert result.primary_confidence == 0.85
        assert len(result.alternatives) == 2
        assert result.tier_used == "fast"

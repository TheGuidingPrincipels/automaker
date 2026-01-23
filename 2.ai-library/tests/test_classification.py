"""Tests for classification service."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from src.classification.fast_tier import FastTierClassifier
from src.classification.llm_tier import LLMTierClassifier
from src.classification.service import ClassificationService
from src.taxonomy.centroids import CentroidManager
from src.taxonomy.manager import TaxonomyManager
from src.taxonomy.schema import CategoryProposal, ClassificationResult


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
                        "children": {
                            "python": {
                                "description": "Python language",
                                "locked": False,
                                "children": {},
                            }
                        },
                    },
                    "architecture": {
                        "description": "System architecture",
                        "locked": True,
                        "children": {},
                    },
                },
            },
        },
        "proposed_categories": [],
        "evolution": {},
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


@pytest.fixture
def centroid_manager(taxonomy_manager):
    """Create a centroid manager with mock centroids."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)

        # Add mock centroids
        manager._centroids = {
            "technical": np.array([1.0, 0.0, 0.0]),
            "technical/programming": np.array([0.9, 0.1, 0.0]),
            "technical/programming/python": np.array([0.85, 0.15, 0.0]),
            "technical/architecture": np.array([0.7, 0.3, 0.0]),
        }

        yield manager


class TestFastTierClassifier:
    """Tests for fast tier classifier."""

    def test_classify_with_centroids(self, taxonomy_manager, centroid_manager):
        """Test classification using centroids."""
        classifier = FastTierClassifier(taxonomy_manager, centroid_manager)

        # Query embedding similar to python centroid
        embedding = np.array([0.85, 0.14, 0.01])
        result = classifier.classify(embedding)

        assert result.tier_used == "fast"
        assert result.primary_path == "technical/programming/python"
        assert result.primary_confidence > 0.9

    def test_classify_alternatives(self, taxonomy_manager, centroid_manager):
        """Test classification returns alternatives."""
        classifier = FastTierClassifier(taxonomy_manager, centroid_manager)

        embedding = np.array([0.8, 0.2, 0.0])
        result = classifier.classify(embedding, top_k=3)

        assert len(result.alternatives) == 2  # top_k - 1

    def test_classify_no_centroids(self, taxonomy_manager):
        """Test classification when no centroids available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_centroid_manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)
            classifier = FastTierClassifier(taxonomy_manager, empty_centroid_manager)

            embedding = np.array([1.0, 0.0, 0.0])
            result = classifier.classify(embedding)

            assert result.primary_path == "uncategorized"
            assert result.primary_confidence == 0.0

    def test_is_ready(self, taxonomy_manager, centroid_manager):
        """Test is_ready check."""
        classifier = FastTierClassifier(taxonomy_manager, centroid_manager)
        assert classifier.is_ready() is True

        # Empty centroid manager
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)
            classifier2 = FastTierClassifier(taxonomy_manager, empty_manager)
            assert classifier2.is_ready() is False

    def test_get_confidence_for_path(self, taxonomy_manager, centroid_manager):
        """Test getting confidence for a specific path."""
        classifier = FastTierClassifier(taxonomy_manager, centroid_manager)

        embedding = np.array([0.85, 0.15, 0.0])
        confidence = classifier.get_confidence_for_path(
            embedding, "technical/programming/python"
        )

        assert confidence > 0.99  # Very similar vectors


class TestLLMTierClassifier:
    """Tests for LLM tier classifier."""

    def test_parse_response_valid_json(self, taxonomy_manager):
        """Test parsing valid LLM response."""
        classifier = LLMTierClassifier(taxonomy_manager)

        response = '''```json
{
    "primary_path": "technical/programming/python",
    "confidence": 0.85,
    "alternatives": [
        {"path": "technical/architecture", "confidence": 0.4}
    ],
    "reasoning": "Content discusses Python programming",
    "new_category_proposal": null
}
```'''

        result = classifier._parse_response(response)

        assert result.primary_path == "technical/programming/python"
        assert result.primary_confidence == 0.85
        assert len(result.alternatives) == 1

    def test_parse_response_with_proposal(self, taxonomy_manager):
        """Test parsing response with new category proposal."""
        classifier = LLMTierClassifier(taxonomy_manager)

        response = '''{
    "primary_path": "technical/programming",
    "confidence": 0.6,
    "alternatives": [],
    "reasoning": "Best fit is programming but specific topic not covered",
    "new_category_proposal": {
        "name": "rust",
        "description": "Rust programming language",
        "parent_path": "technical/programming",
        "confidence": 0.9
    }
}'''

        result = classifier._parse_response(response)

        assert result.new_category_proposed is not None
        assert result.new_category_proposed.name == "rust"

    def test_classify_uses_default_sdk_client(self, taxonomy_manager, monkeypatch):
        """Default SDK client should be available for classification."""
        class DummySDKClient:
            last_instance = None

            def __init__(self):
                DummySDKClient.last_instance = self
                self.prompts = []

            def complete(self, prompt: str) -> str:
                self.prompts.append(prompt)
                return '''{
    "primary_path": "technical/architecture",
    "confidence": 0.9,
    "alternatives": [],
    "reasoning": "Architecture content",
    "new_category_proposal": null
}'''

        import src.sdk.client as sdk_client_module

        monkeypatch.setattr(
            sdk_client_module,
            "ClaudeSDKClient",
            DummySDKClient,
            raising=True,
        )

        classifier = LLMTierClassifier(taxonomy_manager)
        result = classifier.classify("System Design", "Designing systems")

        assert result.primary_path == "technical/architecture"
        assert result.tier_used == "llm"
        assert DummySDKClient.last_instance.prompts

    @pytest.mark.asyncio
    async def test_classify_async_uses_default_sdk_client(
        self,
        taxonomy_manager,
        monkeypatch,
    ):
        """Async classification should use default SDK client."""
        class DummySDKClient:
            last_instance = None

            def __init__(self):
                DummySDKClient.last_instance = self
                self.prompts = []

            async def complete_async(self, prompt: str) -> str:
                self.prompts.append(prompt)
                return '''{
    "primary_path": "technical/programming/python",
    "confidence": 0.92,
    "alternatives": [],
    "reasoning": "Python content",
    "new_category_proposal": null
}'''

        import src.sdk.client as sdk_client_module

        monkeypatch.setattr(
            sdk_client_module,
            "ClaudeSDKClient",
            DummySDKClient,
            raising=True,
        )

        classifier = LLMTierClassifier(taxonomy_manager)
        result = await classifier.classify_async("Python Guide", "Learn Python")

        assert result.primary_path == "technical/programming/python"
        assert result.tier_used == "llm"
        assert DummySDKClient.last_instance.prompts

    def test_build_taxonomy_tree(self, taxonomy_manager):
        """Test building taxonomy tree string."""
        classifier = LLMTierClassifier(taxonomy_manager)
        tree = classifier._build_taxonomy_tree()

        assert "technical" in tree
        assert "programming" in tree
        assert "Programming languages" in tree

    @patch("src.classification.llm_tier.LLMTierClassifier.sdk_client")
    def test_classify_mocked(self, mock_client, taxonomy_manager):
        """Test LLM classification with mocked SDK."""
        mock_client.complete.return_value = '''{
    "primary_path": "technical/programming/python",
    "confidence": 0.9,
    "alternatives": [],
    "reasoning": "Python code detected",
    "new_category_proposal": null
}'''

        classifier = LLMTierClassifier(taxonomy_manager)
        classifier._sdk_client = mock_client

        result = classifier.classify("Python Tutorial", "def hello(): print('world')")

        assert result.primary_path == "technical/programming/python"
        assert result.tier_used == "llm"


class TestClassificationService:
    """Tests for the two-tier classification service."""

    def test_classify_fast_tier_sufficient(
        self, taxonomy_manager, centroid_manager
    ):
        """Test classification stays in fast tier when confidence is sufficient."""
        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
            confidence_threshold=0.75,
        )

        # Embedding very similar to python centroid
        embedding = np.array([0.85, 0.15, 0.0])

        result = service.classify(
            title="Python Tutorial",
            content="Learn Python basics",
            embedding=embedding,
        )

        assert result.tier_used == "fast"
        assert result.primary_confidence >= 0.75

    @patch("src.classification.llm_tier.LLMTierClassifier.sdk_client")
    def test_classify_escalates_to_llm(
        self, mock_client, taxonomy_manager, centroid_manager
    ):
        """Test classification escalates to LLM when fast tier confidence is low."""
        mock_client.complete.return_value = '''{
    "primary_path": "technical/architecture",
    "confidence": 0.85,
    "alternatives": [],
    "reasoning": "Architecture content",
    "new_category_proposal": null
}'''

        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
            confidence_threshold=0.99,  # Very high threshold to force LLM
        )
        service.llm_tier._sdk_client = mock_client

        # Embedding that will have low confidence
        embedding = np.array([0.5, 0.3, 0.2])

        result = service.classify(
            title="System Design",
            content="Designing distributed systems",
            embedding=embedding,
        )

        assert result.tier_used == "llm"

    def test_classify_force_llm(self, taxonomy_manager, centroid_manager):
        """Test forcing LLM tier."""
        with patch.object(LLMTierClassifier, "sdk_client") as mock_client:
            mock_client.complete.return_value = '''{
    "primary_path": "technical/programming",
    "confidence": 0.8,
    "alternatives": [],
    "reasoning": "Test",
    "new_category_proposal": null
}'''

            service = ClassificationService(
                taxonomy_manager=taxonomy_manager,
                centroid_manager=centroid_manager,
            )
            service.llm_tier._sdk_client = mock_client

            embedding = np.array([0.85, 0.15, 0.0])

            result = service.classify(
                title="Test",
                content="Test content",
                embedding=embedding,
                force_llm=True,
            )

            assert result.tier_used == "llm"

    def test_classify_computes_embedding_when_missing(
        self,
        taxonomy_manager,
        centroid_manager,
        monkeypatch,
    ):
        """Classification computes embedding when one is not provided."""
        class DummyEmbeddingService:
            def __init__(self):
                self.calls = []

            def embed(self, text: str) -> list[float]:
                self.calls.append(text)
                return [0.85, 0.15, 0.0]

        dummy_service = DummyEmbeddingService()

        import src.vector.embeddings as embeddings_module

        monkeypatch.setattr(
            embeddings_module,
            "EmbeddingService",
            lambda: dummy_service,
            raising=True,
        )

        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
            confidence_threshold=0.75,
        )

        result = service.classify(
            title="Python Tutorial",
            content="Learn Python basics",
            embedding=None,
        )

        assert dummy_service.calls
        assert "Python Tutorial" in dummy_service.calls[0]
        assert result.tier_used == "fast"

    @pytest.mark.asyncio
    async def test_classify_async_computes_embedding_when_missing(
        self,
        taxonomy_manager,
        centroid_manager,
        monkeypatch,
    ):
        """Async classification computes embedding when one is not provided."""
        class DummyEmbeddingService:
            def __init__(self):
                self.calls = []

            async def embed_async(self, text: str) -> list[float]:
                self.calls.append(text)
                return [0.85, 0.15, 0.0]

            def embed(self, text: str) -> list[float]:
                self.calls.append(text)
                return [0.85, 0.15, 0.0]

        dummy_service = DummyEmbeddingService()

        import src.vector.embeddings as embeddings_module

        monkeypatch.setattr(
            embeddings_module,
            "EmbeddingService",
            lambda: dummy_service,
            raising=True,
        )

        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
            confidence_threshold=0.75,
        )

        result = await service.classify_async(
            title="Python Tutorial",
            content="Learn Python basics",
            embedding=None,
        )

        assert dummy_service.calls
        assert "Python Tutorial" in dummy_service.calls[0]
        assert result.tier_used == "fast"

    def test_validate_path(self, taxonomy_manager, centroid_manager):
        """Test path validation through service."""
        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
        )

        assert service.validate_path("technical/programming") is True
        assert service.validate_path("invalid/path") is False

    def test_get_classification_stats(self, taxonomy_manager, centroid_manager):
        """Test getting classification statistics."""
        service = ClassificationService(
            taxonomy_manager=taxonomy_manager,
            centroid_manager=centroid_manager,
        )

        stats = service.get_classification_stats()

        assert "fast_tier_ready" in stats
        assert "centroid_count" in stats
        assert "confidence_threshold" in stats
        assert stats["fast_tier_ready"] is True
        assert stats["centroid_count"] == 4


class TestCentroidManager:
    """Tests for centroid manager."""

    def test_find_nearest_categories(self, taxonomy_manager):
        """Test finding nearest categories to an embedding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)

            manager._centroids = {
                "cat1": np.array([1.0, 0.0, 0.0]),
                "cat2": np.array([0.0, 1.0, 0.0]),
                "cat3": np.array([0.0, 0.0, 1.0]),
            }

            query = np.array([0.9, 0.1, 0.0])
            results = manager.find_nearest_categories(query, top_k=2)

            assert len(results) == 2
            assert results[0][0] == "cat1"  # Most similar
            assert results[0][1] > results[1][1]  # Scores descending

    def test_save_and_load_centroids(self, taxonomy_manager):
        """Test saving and loading centroids."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)

            manager._centroids = {
                "test1": np.array([1.0, 2.0, 3.0]),
                "test2": np.array([4.0, 5.0, 6.0]),
            }

            manager.save_centroids()

            # Create new manager and load
            manager2 = CentroidManager(taxonomy_manager, cache_dir=tmpdir)
            count = manager2.load_centroids()

            assert count == 2
            assert "test1" in manager2._centroids
            np.testing.assert_array_almost_equal(
                manager2._centroids["test1"], [1.0, 2.0, 3.0]
            )

    def test_incremental_update(self, taxonomy_manager):
        """Test incremental centroid update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)

            # First item
            manager.update_centroid_incremental(
                "test", np.array([1.0, 0.0, 0.0]), 1
            )
            np.testing.assert_array_almost_equal(
                manager._centroids["test"], [1.0, 0.0, 0.0]
            )

            # Second item
            manager.update_centroid_incremental(
                "test", np.array([0.0, 1.0, 0.0]), 2
            )
            # Running average: [1,0,0] + ([0,1,0] - [1,0,0])/2 = [0.5, 0.5, 0]
            np.testing.assert_array_almost_equal(
                manager._centroids["test"], [0.5, 0.5, 0.0]
            )

    @pytest.mark.asyncio
    async def test_compute_centroids_async(self, taxonomy_manager):
        """Async centroid computation should use vector store results."""
        class DummyVectorStore:
            async def search_by_taxonomy(self, taxonomy_path, limit=1000):
                class DummyRecord:
                    def __init__(self, vector):
                        self.vector = vector

                if taxonomy_path == "technical":
                    return [DummyRecord([1.0, 0.0, 0.0])]
                return []

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CentroidManager(taxonomy_manager, cache_dir=tmpdir)

            computed = await manager.compute_centroids_async(
                DummyVectorStore(),
                min_samples=1,
            )

            assert computed >= 1
            assert manager.get_centroid("technical") is not None

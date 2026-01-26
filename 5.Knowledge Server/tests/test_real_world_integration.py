"""
Real-world integration test for EmbeddingService with ChromaDB.

This test simulates actual usage patterns with concept storage and semantic search.
"""

import shutil
import tempfile
import time

import numpy as np
import pytest
import pytest_asyncio

from services.chromadb_service import ChromaDbService
from services.embedding_service import EmbeddingService


@pytest_asyncio.fixture
async def embedding_service():
    """Initialize embedding service."""
    service = EmbeddingService()
    await service.initialize()
    return service


@pytest.fixture
def chroma_service():
    """Create temporary ChromaDB instance."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_real_world_")

    try:
        service = ChromaDbService(persist_directory=temp_dir, collection_name="concepts")
        service.connect()
        yield service
        service.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# Sample concept data from different domains
SAMPLE_CONCEPTS = [
    {
        "id": "py_001",
        "explanation": "Python for loops iterate over sequences like lists, tuples, and strings. "
                "They execute a code block for each element in the sequence. "
                "Syntax: for item in sequence: code_block",
        "metadata": {"area": "Programming", "topic": "Python", "difficulty": "beginner"}
    },
    {
        "id": "py_002",
        "explanation": "Python list comprehensions provide concise syntax for creating lists. "
                "They combine for loops and conditional logic in a single line. "
                "Example: [x*2 for x in range(10) if x % 2 == 0]",
        "metadata": {"area": "Programming", "topic": "Python", "difficulty": "intermediate"}
    },
    {
        "id": "js_001",
        "explanation": "JavaScript async/await syntax simplifies asynchronous programming. "
                "It allows writing asynchronous code that looks synchronous. "
                "Functions marked async return promises automatically.",
        "metadata": {"area": "Programming", "topic": "JavaScript", "difficulty": "intermediate"}
    },
    {
        "id": "stoic_001",
        "explanation": "The Stoic dichotomy of control teaches that some things are within our control "
                "(our thoughts, actions, and responses) while others are not (external events, "
                "other people's opinions). Focus energy on what you can control.",
        "metadata": {"area": "Philosophy", "topic": "Stoicism", "difficulty": "beginner"}
    },
    {
        "id": "stoic_002",
        "explanation": "Stoic negative visualization (premeditatio malorum) involves imagining worst-case "
                "scenarios to reduce anxiety and increase gratitude. By contemplating loss, "
                "we appreciate what we have and prepare mentally for challenges.",
        "metadata": {"area": "Philosophy", "topic": "Stoicism", "difficulty": "advanced"}
    },
    {
        "id": "ml_001",
        "explanation": "Neural networks are composed of layers of interconnected nodes (neurons). "
                "Each connection has a weight that's adjusted during training. "
                "Networks learn patterns through backpropagation and gradient descent.",
        "metadata": {"area": "Technology", "topic": "Machine Learning", "difficulty": "advanced"}
    },
    {
        "id": "db_001",
        "explanation": "Database indexes improve query performance by creating data structures "
                "that allow fast lookups. They work like book indexes, pointing to data locations. "
                "Trade-off: faster reads but slower writes and more storage.",
        "metadata": {"area": "Technology", "topic": "Databases", "difficulty": "intermediate"}
    },
    {
        "id": "health_001",
        "explanation": "High-intensity interval training (HIIT) alternates short bursts of intense exercise "
                "with recovery periods. Benefits include improved cardiovascular fitness, "
                "fat burning, and time efficiency compared to steady-state cardio.",
        "metadata": {"area": "Health", "topic": "Fitness", "difficulty": "beginner"}
    },
    {
        "id": "health_002",
        "explanation": "Sleep cycles consist of REM and non-REM stages, each lasting 90 minutes. "
                "Deep sleep is crucial for physical recovery and memory consolidation. "
                "Most adults need 7-9 hours of quality sleep per night.",
        "metadata": {"area": "Health", "topic": "Sleep", "difficulty": "beginner"}
    },
    {
        "id": "finance_001",
        "explanation": "Compound interest is interest calculated on initial principal plus accumulated interest. "
                "Einstein reportedly called it the eighth wonder of the world. "
                "Formula: A = P(1 + r/n)^(nt) where P=principal, r=rate, n=compounds per year, t=time.",
        "metadata": {"area": "Finance", "topic": "Investing", "difficulty": "beginner"}
    }
]


class TestRealWorldIntegration:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_store_and_search_concepts(self, embedding_service, chroma_service):
        """Test storing concepts and performing semantic search."""
        # Generate embeddings for all concepts
        texts = [c["explanation"] for c in SAMPLE_CONCEPTS]
        embeddings = embedding_service.generate_batch(texts)

        # Store in ChromaDB
        collection = chroma_service.get_collection()
        collection.add(
            ids=[c["id"] for c in SAMPLE_CONCEPTS],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in SAMPLE_CONCEPTS],
        )

        # Verify all stored
        assert collection.count() == 10

        # Test 1: Search for Python iteration concepts
        query1 = "How to loop through items in Python?"
        query_emb1 = embedding_service.generate_embedding(query1)
        results1 = collection.query(query_embeddings=[query_emb1], n_results=3)

        # Should find Python for loops
        assert any("py_001" in id for id in results1["ids"][0])
        print(f"Query: '{query1}'")
        print(f"Top result: {results1['ids'][0][0]}")

        # Test 2: Search for Stoic philosophy
        query2 = "What can I control in life according to ancient philosophy?"
        query_emb2 = embedding_service.generate_embedding(query2)
        results2 = collection.query(
            query_embeddings=[query_emb2], n_results=2, where={"area": "Philosophy"}
        )

        # Should find Stoic dichotomy of control
        assert any("stoic_001" in id for id in results2["ids"][0])
        print(f"Query: '{query2}'")
        print(f"Top result: {results2['ids'][0][0]}")

        # Test 3: Search for health concepts
        query3 = "Improving physical fitness efficiently"
        query_emb3 = embedding_service.generate_embedding(query3)
        results3 = collection.query(
            query_embeddings=[query_emb3], n_results=2, where={"area": "Health"}
        )

        # Should find HIIT or sleep
        health_ids = [id for sublist in results3["ids"] for id in sublist]
        assert any(id.startswith("health_") for id in health_ids)

    @pytest.mark.asyncio
    async def test_cross_domain_similarity(self, embedding_service):
        """Test semantic similarity across different domains."""
        # Generate embeddings for programming concepts
        prog_texts = [
            "Python for loops iterate over sequences",
            "JavaScript promises handle async operations",
            "Database indexes speed up queries",
        ]

        # Generate embeddings for philosophy concepts
        phil_texts = [
            "Stoic dichotomy of control philosophy",
            "Existentialist freedom and responsibility",
            "Buddhist mindfulness meditation",
        ]

        prog_embs = embedding_service.generate_batch(prog_texts)
        phil_embs = embedding_service.generate_batch(phil_texts)

        # Within-domain similarity should be higher
        prog_sim = np.dot(prog_embs[0], prog_embs[1])  # Python vs JavaScript
        cross_sim = np.dot(prog_embs[0], phil_embs[0])  # Python vs Stoicism

        assert (
            prog_sim > cross_sim
        ), f"Within-domain similarity ({prog_sim:.3f}) should exceed cross-domain ({cross_sim:.3f})"

        print(f"Within-domain similarity: {prog_sim:.3f}")
        print(f"Cross-domain similarity: {cross_sim:.3f}")

    @pytest.mark.asyncio
    async def test_concept_update_workflow(self, embedding_service, chroma_service):
        """Test updating concept text and embeddings."""
        collection = chroma_service.get_collection()

        # Initial concept
        concept_id = "test_update"
        original_text = "Python uses dynamic typing and automatic memory management"
        original_emb = embedding_service.generate_embedding(original_text)

        collection.add(
            ids=[concept_id],
            documents=[original_text],
            embeddings=[original_emb],
            metadatas=[{"area": "Programming", "version": 1}],
        )

        # Update concept with more detail
        updated_text = (
            "Python uses dynamic typing and automatic memory management with garbage collection. "
            "It supports multiple programming paradigms including procedural, object-oriented, "
            "and functional programming styles."
        )
        updated_emb = embedding_service.generate_embedding(updated_text)

        collection.update(
            ids=[concept_id],
            documents=[updated_text],
            embeddings=[updated_emb],
            metadatas=[{"area": "Programming", "version": 2}],
        )

        # Verify update
        result = collection.get(ids=[concept_id])
        assert "garbage collection" in result["documents"][0]
        assert result["metadatas"][0]["version"] == 2

        # Embedding should have changed
        result_with_emb = collection.get(ids=[concept_id], include=["embeddings"])
        similarity = np.dot(original_emb, result_with_emb["embeddings"][0])
        assert similarity > 0.7, "Updated embedding should still be related but different"

    @pytest.mark.asyncio
    async def test_batch_performance_real_world(self, embedding_service):
        """Test performance with realistic batch sizes."""
        # Simulate adding 100 concepts at once
        concepts = [
            f"This is concept number {i} about various programming topics including "
            f"algorithms, data structures, design patterns, and best practices. "
            f"It covers fundamental concepts essential for software development."
            for i in range(100)
        ]

        # Measure batch processing time
        start = time.time()
        embeddings = embedding_service.generate_batch(concepts)
        elapsed = time.time() - start

        assert len(embeddings) == 100
        assert elapsed < 3.0, f"Batch of 100 took {elapsed:.2f}s (target: <3s)"

        # Verify all are valid embeddings
        for emb in embeddings:
            assert len(emb) == 384
            norm = np.linalg.norm(emb)
            assert abs(norm - 1.0) < 0.01

        print(f"Batch processing: 100 concepts in {elapsed:.2f}s ({elapsed*10:.1f}ms per concept)")

    @pytest.mark.asyncio
    async def test_metadata_filtering_scenarios(self, embedding_service, chroma_service):
        """Test various metadata filtering scenarios."""
        # Add sample concepts
        texts = [c["explanation"] for c in SAMPLE_CONCEPTS]
        embeddings = embedding_service.generate_batch(texts)

        collection = chroma_service.get_collection()
        collection.add(
            ids=[c["id"] for c in SAMPLE_CONCEPTS],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in SAMPLE_CONCEPTS],
        )

        # Scenario 1: Filter by area
        query_emb = embedding_service.generate_embedding("learning and education")
        results = collection.query(
            query_embeddings=[query_emb], n_results=5, where={"area": "Programming"}
        )

        for metadata in results["metadatas"][0]:
            assert metadata["area"] == "Programming"

        # Scenario 2: Filter by difficulty
        results_beginner = collection.query(
            query_embeddings=[query_emb], n_results=10, where={"difficulty": "beginner"}
        )

        for metadata in results_beginner["metadatas"][0]:
            assert metadata["difficulty"] == "beginner"

        # Scenario 3: Combine filters (Programming AND intermediate)
        results_combined = collection.query(
            query_embeddings=[query_emb],
            n_results=5,
            where={"$and": [{"area": "Programming"}, {"difficulty": "intermediate"}]},
        )

        for metadata in results_combined["metadatas"][0]:
            assert metadata["area"] == "Programming"
            assert metadata["difficulty"] == "intermediate"

    @pytest.mark.asyncio
    async def test_semantic_search_accuracy(self, embedding_service, chroma_service):
        """Test accuracy of semantic search results."""
        # Add concepts
        texts = [c["explanation"] for c in SAMPLE_CONCEPTS]
        embeddings = embedding_service.generate_batch(texts)

        collection = chroma_service.get_collection()
        collection.add(
            ids=[c["id"] for c in SAMPLE_CONCEPTS],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in SAMPLE_CONCEPTS],
        )

        # Test queries with expected results
        test_cases = [
            {
                "query": "iterating over collections in Python",
                "expected_contains": ["py_001", "py_002"],
                "description": "Should find Python iteration concepts",
            },
            {
                "query": "What I can and cannot control",
                "expected_contains": ["stoic_001"],
                "description": "Should find Stoic dichotomy of control",
            },
            {
                "query": "asynchronous programming patterns",
                "expected_contains": ["js_001"],
                "description": "Should find async/await",
            },
            {
                "query": "speeding up database queries",
                "expected_contains": ["db_001"],
                "description": "Should find database indexes",
            },
        ]

        for test_case in test_cases:
            query_emb = embedding_service.generate_embedding(test_case["query"])
            results = collection.query(query_embeddings=[query_emb], n_results=3)

            top_ids = results["ids"][0]

            # Check if at least one expected ID is in top results
            found = any(exp_id in top_ids for exp_id in test_case["expected_contains"])
            assert (
                found
            ), f"Failed: {test_case['description']}. Query: '{test_case['query']}', Top results: {top_ids}"

            print(f"✓ {test_case['description']}")
            print(f"  Query: '{test_case['query']}'")
            print(f"  Top result: {top_ids[0]}")


class TestPerformanceMetrics:
    """Detailed performance testing."""

    @pytest.mark.asyncio
    async def test_detailed_performance_metrics(self, embedding_service):
        """Collect detailed performance metrics."""
        # Single embedding performance
        text = "Test concept for performance measurement"
        warmup = 5
        iterations = 50

        # Warmup
        for _ in range(warmup):
            embedding_service.generate_embedding(text)

        # Measure
        times = []
        for _ in range(iterations):
            start = time.time()
            embedding_service.generate_embedding(text)
            times.append(time.time() - start)

        avg_ms = (sum(times) / len(times)) * 1000
        min_ms = min(times) * 1000
        max_ms = max(times) * 1000

        print("\nSingle Embedding Performance:")
        print(f"  Average: {avg_ms:.2f}ms")
        print(f"  Min: {min_ms:.2f}ms")
        print(f"  Max: {max_ms:.2f}ms")

        # Batch performance at different sizes
        batch_sizes = [10, 50, 100]
        for batch_size in batch_sizes:
            texts = [f"concept {i}" for i in range(batch_size)]

            # Warmup
            embedding_service.generate_batch(texts[:5])

            # Measure
            start = time.time()
            embedding_service.generate_batch(texts)
            elapsed = time.time() - start

            per_item_ms = (elapsed / batch_size) * 1000

            print(f"\nBatch Performance (size={batch_size}):")
            print(f"  Total: {elapsed*1000:.0f}ms")
            print(f"  Per item: {per_item_ms:.2f}ms")

            # Batch should be more efficient
            if batch_size >= 10:
                assert (
                    per_item_ms < avg_ms
                ), f"Batch processing should be more efficient (batch: {per_item_ms:.2f}ms vs single: {avg_ms:.2f}ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

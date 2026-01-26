"""
Integration tests for EmbeddingService with ChromaDB.

Tests the integration between EmbeddingService and ChromaDB,
verifying end-to-end embedding generation and semantic search.
"""

import shutil
import tempfile

import numpy as np
import pytest
import pytest_asyncio

from services.chromadb_service import ChromaDbService
from services.embedding_service import EmbeddingService


@pytest_asyncio.fixture
async def embedding_service():
    """Create and initialize embedding service."""
    service = EmbeddingService()
    await service.initialize()
    yield service


@pytest.fixture
def chroma_service():
    """Create ChromaDB service with temporary directory."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_embed_test_")

    try:
        service = ChromaDbService(persist_directory=temp_dir, collection_name="test_embeddings")
        service.connect()
        yield service
        service.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class TestEmbeddingServiceWithChromaDB:
    """Test integration between EmbeddingService and ChromaDB."""

    @pytest.mark.asyncio
    async def test_add_concepts_with_real_embeddings(self, embedding_service, chroma_service):
        """Test adding concepts to ChromaDB with real embeddings."""
        # Generate embeddings
        concepts = [
            {
                "id": "concept_001",
                "explanation": "Python for loops iterate over sequences",
                "metadata": {"area": "Programming", "topic": "Python"}
            },
            {
                "id": "concept_002",
                "explanation": "JavaScript async/await handles asynchronous operations",
                "metadata": {"area": "Programming", "topic": "JavaScript"}
            },
            {
                "id": "concept_003",
                "explanation": "The Stoic dichotomy of control",
                "metadata": {"area": "Philosophy", "topic": "Stoicism"}
            }
        ]

        # Generate embeddings
        texts = [c["explanation"] for c in concepts]
        embeddings = embedding_service.generate_batch(texts)

        # Add to ChromaDB
        collection = chroma_service.get_collection()
        collection.add(
            ids=[c["id"] for c in concepts],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in concepts],
        )

        # Verify all concepts stored
        assert collection.count() == 3

        # Verify embeddings are correct dimension
        result = collection.get(ids=["concept_001"], include=["embeddings"])
        assert len(result["embeddings"][0]) == 384

    @pytest.mark.asyncio
    async def test_semantic_search_with_real_embeddings(self, embedding_service, chroma_service):
        """Test semantic search using real embeddings."""
        # Add concepts
        concepts = [
            "Python for loops iterate over sequences",
            "For loops in Python allow iteration",
            "JavaScript async/await handles promises",
            "The Stoic philosophy teaches virtue",
            "Machine learning trains models on data",
        ]

        embeddings = embedding_service.generate_batch(concepts)

        collection = chroma_service.get_collection()
        collection.add(
            ids=[f"concept_{i:03d}" for i in range(len(concepts))],
            documents=concepts,
            embeddings=embeddings,
            metadatas=[{"index": i} for i in range(len(concepts))],
        )

        # Search for similar concepts
        query = "iteration in Python programming"
        query_embedding = embedding_service.generate_embedding(query)

        results = collection.query(query_embeddings=[query_embedding], n_results=3)

        # Should find Python loop concepts first
        assert len(results["ids"][0]) == 3

        # Top results should be Python-related
        top_docs = results["documents"][0]
        assert any("Python" in doc for doc in top_docs[:2])

    @pytest.mark.asyncio
    async def test_embedding_similarity_accuracy(self, embedding_service):
        """Test that embeddings produce accurate similarity scores."""
        # Similar concepts
        text1 = "Python for loops iterate over lists"
        text2 = "For loops in Python allow iteration over collections"

        # Unrelated concept
        text3 = "The Stoic dichotomy of control philosophy"

        emb1 = embedding_service.generate_embedding(text1)
        emb2 = embedding_service.generate_embedding(text2)
        emb3 = embedding_service.generate_embedding(text3)

        # Calculate cosine similarities
        sim_12 = np.dot(emb1, emb2)  # Similar concepts
        sim_13 = np.dot(emb1, emb3)  # Unrelated concepts

        # Similar concepts should have higher similarity
        assert sim_12 > sim_13
        assert sim_12 > 0.7  # High similarity
        assert sim_13 < 0.5  # Low similarity

    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, embedding_service, chroma_service):
        """Test batch processing performance with ChromaDB."""
        import time

        # Create 50 concepts
        concepts = [f"This is concept number {i} about various topics" for i in range(50)]

        # Time batch embedding generation
        start = time.time()
        embeddings = embedding_service.generate_batch(concepts)
        embed_time = time.time() - start

        # Should process batch quickly (< 2 seconds for 50 concepts)
        assert embed_time < 2.0, f"Batch embedding took {embed_time:.2f}s"

        # Add to ChromaDB
        collection = chroma_service.get_collection()
        start = time.time()
        collection.add(
            ids=[f"concept_{i:03d}" for i in range(len(concepts))],
            documents=concepts,
            embeddings=embeddings,
        )
        add_time = time.time() - start

        # Verify all added
        assert collection.count() == 50

        # Total time should be reasonable
        total_time = embed_time + add_time
        assert total_time < 5.0, f"Total time: {total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_update_concept_embedding(self, embedding_service, chroma_service):
        """Test updating concept with new embedding."""
        concept_id = "concept_update_001"
        original_text = "Original concept explanation"
        updated_text = "Updated concept explanation with new information"

        # Add original
        original_embedding = embedding_service.generate_embedding(original_text)
        collection = chroma_service.get_collection()
        collection.add(ids=[concept_id], documents=[original_text], embeddings=[original_embedding])

        # Update with new text and embedding
        updated_embedding = embedding_service.generate_embedding(updated_text)
        collection.update(
            ids=[concept_id], documents=[updated_text], embeddings=[updated_embedding]
        )

        # Verify update
        result = collection.get(ids=[concept_id])
        assert result["documents"][0] == updated_text

        # Verify embedding changed
        result_with_emb = collection.get(ids=[concept_id], include=["embeddings"])
        assert not np.allclose(result_with_emb["embeddings"][0], original_embedding)

    @pytest.mark.asyncio
    async def test_metadata_filtering_with_embeddings(self, embedding_service, chroma_service):
        """Test filtering by metadata while using semantic search."""
        # Add concepts with different areas
        programming_concepts = ["Python for loops", "JavaScript promises", "Java inheritance"]
        philosophy_concepts = ["Stoic dichotomy of control", "Platonic forms", "Aristotelian logic"]

        all_concepts = programming_concepts + philosophy_concepts
        embeddings = embedding_service.generate_batch(all_concepts)

        collection = chroma_service.get_collection()
        collection.add(
            ids=[f"concept_{i:03d}" for i in range(len(all_concepts))],
            documents=all_concepts,
            embeddings=embeddings,
            metadatas=[{"area": "Programming"} for _ in programming_concepts]
            + [{"area": "Philosophy"} for _ in philosophy_concepts],
        )

        # Search only in Programming area
        query = "control flow and iteration"
        query_embedding = embedding_service.generate_embedding(query)

        results = collection.query(
            query_embeddings=[query_embedding], n_results=3, where={"area": "Programming"}
        )

        # Should only return programming concepts
        assert len(results["ids"][0]) <= 3
        for metadata in results["metadatas"][0]:
            assert metadata["area"] == "Programming"


class TestEmbeddingDimensions:
    """Test embedding dimensions and consistency."""

    @pytest.mark.asyncio
    async def test_embedding_dimensions_match_chromadb(self, embedding_service):
        """Test that embedding dimensions are consistent."""
        text = "Test concept for dimension verification"
        embedding = embedding_service.generate_embedding(text)

        # Should be 384 dimensions for all-MiniLM-L6-v2
        assert len(embedding) == 384
        assert embedding_service.get_embedding_dimension() == 384

    @pytest.mark.asyncio
    async def test_batch_embeddings_consistent_dimensions(self, embedding_service):
        """Test that batch embeddings have consistent dimensions."""
        texts = [f"concept {i}" for i in range(20)]
        embeddings = embedding_service.generate_batch(texts)

        # All embeddings should have same dimension
        dimensions = [len(emb) for emb in embeddings]
        assert all(dim == 384 for dim in dimensions)


class TestEmbeddingNormalization:
    """Test embedding normalization for ChromaDB."""

    @pytest.mark.asyncio
    async def test_normalized_embeddings_for_cosine_similarity(self, embedding_service):
        """Test that embeddings are normalized for cosine similarity."""
        texts = ["concept 1", "concept 2", "concept 3"]
        embeddings = embedding_service.generate_batch(texts)

        # All should be unit vectors
        for embedding in embeddings:
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01, f"Norm: {norm}"

    @pytest.mark.asyncio
    async def test_cosine_similarity_with_normalized_embeddings(self, embedding_service):
        """Test cosine similarity calculation with normalized embeddings."""
        text1 = "Python programming language"
        text2 = "Python coding"

        emb1 = embedding_service.generate_embedding(text1)
        emb2 = embedding_service.generate_embedding(text2)

        # With normalized vectors, dot product = cosine similarity
        similarity = np.dot(emb1, emb2)

        # Should be between -1 and 1
        assert -1.0 <= similarity <= 1.0

        # Similar texts should have positive similarity
        assert similarity > 0.5


class TestErrorHandlingIntegration:
    """Test error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_chromadb_with_unavailable_embedding_service(self, chroma_service):
        """Test handling when embedding service is unavailable."""
        # Create service but don't initialize
        embedding_service = EmbeddingService()

        # Try to generate embeddings
        embeddings = embedding_service.generate_batch(["text 1", "text 2"])

        # Should return zero vectors
        assert all(all(x == 0.0 for x in emb) for emb in embeddings)

        # Can still add to ChromaDB (though not useful)
        collection = chroma_service.get_collection()
        collection.add(
            ids=["concept_001", "concept_002"],
            documents=["text 1", "text 2"],
            embeddings=embeddings,
        )

        assert collection.count() == 2


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    @pytest.mark.asyncio
    async def test_full_concept_lifecycle(self, embedding_service, chroma_service):
        """Test complete concept lifecycle: create, search, update, delete."""
        collection = chroma_service.get_collection()

        # 1. Create concepts
        concepts = [
            {
                "id": "python_loops",
                "explanation": "Python for loops iterate over sequences like lists and strings",
                "metadata": {"area": "Programming", "topic": "Python", "difficulty": "beginner"}
            },
            {
                "id": "js_promises",
                "explanation": "JavaScript promises handle asynchronous operations and callbacks",
                "metadata": {"area": "Programming", "topic": "JavaScript", "difficulty": "intermediate"}
            }
        ]

        texts = [c["explanation"] for c in concepts]
        embeddings = embedding_service.generate_batch(texts)

        collection.add(
            ids=[c["id"] for c in concepts],
            documents=texts,
            embeddings=embeddings,
            metadatas=[c["metadata"] for c in concepts],
        )

        # 2. Search for similar concepts
        query = "iteration in programming"
        query_emb = embedding_service.generate_embedding(query)
        results = collection.query(query_embeddings=[query_emb], n_results=1)

        assert "python_loops" in results["ids"][0][0]

        # 3. Update concept
        updated_text = (
            "Python for loops iterate over sequences like lists, strings, and dictionaries"
        )
        updated_emb = embedding_service.generate_embedding(updated_text)

        collection.update(ids=["python_loops"], documents=[updated_text], embeddings=[updated_emb])

        # 4. Verify update
        result = collection.get(ids=["python_loops"])
        assert "dictionaries" in result["documents"][0]

        # 5. Delete concept
        collection.delete(ids=["python_loops"])
        assert collection.count() == 1

    @pytest.mark.asyncio
    async def test_multi_domain_concept_storage(self, embedding_service, chroma_service):
        """Test storing concepts from multiple knowledge domains."""
        concepts = {
            "Programming": [
                "Python list comprehensions create lists using concise syntax",
                "Recursion solves problems by breaking them into smaller sub-problems",
            ],
            "Philosophy": [
                "Stoic philosophy teaches focusing on what we can control",
                "Existentialism emphasizes individual freedom and choice",
            ],
            "Health": [
                "Regular exercise improves cardiovascular health",
                "Balanced nutrition provides essential vitamins and minerals",
            ],
        }

        # Flatten and track
        all_texts = []
        all_metadata = []
        for area, texts in concepts.items():
            for text in texts:
                all_texts.append(text)
                all_metadata.append({"area": area})

        # Generate embeddings
        embeddings = embedding_service.generate_batch(all_texts)

        # Add to ChromaDB
        collection = chroma_service.get_collection()
        collection.add(
            ids=[f"concept_{i:03d}" for i in range(len(all_texts))],
            documents=all_texts,
            embeddings=embeddings,
            metadatas=all_metadata,
        )

        # Verify all stored
        assert collection.count() == 6

        # Test area-specific search
        query = "improving fitness and health"
        query_emb = embedding_service.generate_embedding(query)

        results = collection.query(
            query_embeddings=[query_emb], n_results=2, where={"area": "Health"}
        )

        # Should return health-related concepts
        assert all(meta["area"] == "Health" for meta in results["metadatas"][0])

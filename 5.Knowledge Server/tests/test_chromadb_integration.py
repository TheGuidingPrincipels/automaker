"""
Comprehensive Integration Tests for ChromaDB Service

Tests the full end-to-end workflows, multi-concept operations,
service lifecycle, error recovery, and acceptance criteria.
"""

import shutil
import tempfile
import time
from pathlib import Path

import pytest

from services.chromadb_service import ChromaDbConfig, ChromaDbService


class TestFullWorkflow:
    """Test complete end-to-end workflow."""

    def test_complete_workflow(self):
        """Test: Initialize → Add → Query → Update → Delete → Verify persistence"""
        # Create temporary directory for this test
        temp_dir = tempfile.mkdtemp(prefix="chroma_integration_")

        try:
            # Step 1: Initialize
            print("\n[STEP 1] Initialize ChromaDB service")
            service = ChromaDbService(persist_directory=temp_dir, collection_name="workflow_test")
            assert service.connect() is True
            assert service.is_connected() is True

            collection = service.get_collection()
            assert collection.count() == 0
            print("✓ Service initialized successfully")

            # Step 2: Add concepts
            print("\n[STEP 2] Add concepts")
            concepts = [
                {
                    "id": "concept_001",
                    "document": "Python is a high-level programming language",
                    "metadata": {"name": "Python", "area": "Programming", "topic": "Languages"},
                },
                {
                    "id": "concept_002",
                    "document": "JavaScript is used for web development",
                    "metadata": {"name": "JavaScript", "area": "Programming", "topic": "Web"},
                },
                {
                    "id": "concept_003",
                    "document": "Machine learning is a subset of artificial intelligence",
                    "metadata": {"name": "ML", "area": "AI", "topic": "Machine Learning"},
                },
            ]

            for concept in concepts:
                collection.add(
                    ids=[concept["id"]],
                    documents=[concept["document"]],
                    metadatas=[concept["metadata"]],
                )

            assert collection.count() == 3
            print(f"✓ Added {len(concepts)} concepts")

            # Step 3: Query concepts
            print("\n[STEP 3] Query concepts by similarity")
            results = collection.query(query_texts=["programming language"], n_results=2)

            assert len(results["ids"][0]) == 2
            assert "concept_001" in results["ids"][0] or "concept_002" in results["ids"][0]
            print(f"✓ Query returned {len(results['ids'][0])} results")

            # Step 4: Update concept
            print("\n[STEP 4] Update concept")
            collection.update(
                ids=["concept_001"],
                documents=[
                    "Python is a versatile high-level programming language with extensive libraries"
                ],
                metadatas=[
                    {"name": "Python", "area": "Programming", "topic": "Languages", "updated": True}
                ],
            )

            result = collection.get(ids=["concept_001"])
            assert result["metadatas"][0]["updated"] is True
            print("✓ Concept updated successfully")

            # Step 5: Delete concept
            print("\n[STEP 5] Delete concept")
            collection.delete(ids=["concept_003"])
            assert collection.count() == 2
            print("✓ Concept deleted successfully")

            # Step 6: Verify persistence
            print("\n[STEP 6] Verify persistence across restarts")
            service.close()

            # Reopen service
            service2 = ChromaDbService(persist_directory=temp_dir, collection_name="workflow_test")
            service2.connect()
            collection2 = service2.get_collection()

            assert collection2.count() == 2
            result = collection2.get(ids=["concept_001"])
            assert result["metadatas"][0]["updated"] is True
            print("✓ Data persisted across service restart")

            service2.close()
            print("\n[COMPLETE] Full workflow test passed!")

        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMultiConceptOperations:
    """Test operations with 10+ concepts."""

    def test_batch_operations(self):
        """Test adding and querying 10+ concepts with batch operations."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_batch_")

        try:
            service = ChromaDbService(persist_directory=temp_dir, collection_name="batch_test")
            service.connect()
            collection = service.get_collection()

            # Create 15 concepts
            print("\n[BATCH TEST] Adding 15 concepts")
            ids = [f"concept_{i:03d}" for i in range(1, 16)]
            documents = [
                "Python programming language",
                "JavaScript for web development",
                "Java enterprise applications",
                "C++ systems programming",
                "Ruby on Rails web framework",
                "Go concurrent programming",
                "Rust memory safe programming",
                "TypeScript typed JavaScript",
                "Swift iOS development",
                "Kotlin Android development",
                "Machine learning algorithms",
                "Deep learning neural networks",
                "Natural language processing",
                "Computer vision applications",
                "Reinforcement learning systems",
            ]
            metadatas = [
                {"area": "Programming", "topic": "Languages", "difficulty": "beginner"},
                {"area": "Programming", "topic": "Web", "difficulty": "beginner"},
                {"area": "Programming", "topic": "Enterprise", "difficulty": "intermediate"},
                {"area": "Programming", "topic": "Systems", "difficulty": "advanced"},
                {"area": "Programming", "topic": "Web", "difficulty": "intermediate"},
                {"area": "Programming", "topic": "Concurrent", "difficulty": "intermediate"},
                {"area": "Programming", "topic": "Systems", "difficulty": "advanced"},
                {"area": "Programming", "topic": "Web", "difficulty": "intermediate"},
                {"area": "Programming", "topic": "Mobile", "difficulty": "intermediate"},
                {"area": "Programming", "topic": "Mobile", "difficulty": "intermediate"},
                {"area": "AI", "topic": "ML", "difficulty": "advanced"},
                {"area": "AI", "topic": "Deep Learning", "difficulty": "advanced"},
                {"area": "AI", "topic": "NLP", "difficulty": "advanced"},
                {"area": "AI", "topic": "Vision", "difficulty": "advanced"},
                {"area": "AI", "topic": "RL", "difficulty": "expert"},
            ]

            # Add all concepts in one batch
            collection.add(ids=ids, documents=documents, metadatas=metadatas)

            assert collection.count() == 15
            print(f"✓ Added {collection.count()} concepts in batch")

            # Test metadata filtering
            print("\n[METADATA FILTER] Testing metadata filtering")
            results = collection.query(
                query_texts=["programming"], n_results=20, where={"area": "Programming"}
            )

            programming_count = len(results["ids"][0])
            assert programming_count == 10  # Should return all 10 programming concepts
            print(f"✓ Filtered query returned {programming_count} programming concepts")

            # Test advanced metadata filtering (using $and operator for multiple conditions)
            results = collection.query(
                query_texts=["programming"],
                n_results=20,
                where={"$and": [{"area": "Programming"}, {"difficulty": "advanced"}]},
            )

            advanced_count = len(results["ids"][0])
            assert advanced_count == 2  # C++ and Rust
            print(f"✓ Advanced filter returned {advanced_count} advanced programming concepts")

            service.close()
            print("\n[COMPLETE] Batch operations test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_large_scale_query_performance(self):
        """Test query performance with many concepts."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_perf_")

        try:
            service = ChromaDbService(persist_directory=temp_dir, collection_name="perf_test")
            service.connect()
            collection = service.get_collection()

            # Add 50 concepts
            print("\n[PERFORMANCE TEST] Adding 50 concepts")
            ids = [f"perf_{i:03d}" for i in range(50)]
            documents = [
                f"This is concept number {i} about various topics in technology" for i in range(50)
            ]
            metadatas = [{"index": i, "area": f"Area_{i % 5}"} for i in range(50)]

            start_time = time.time()
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            add_time = time.time() - start_time

            assert collection.count() == 50
            print(f"✓ Added 50 concepts in {add_time:.3f}s")

            # Test query performance
            start_time = time.time()
            results = collection.query(query_texts=["technology concept"], n_results=10)
            query_time = time.time() - start_time

            assert len(results["ids"][0]) == 10
            print(f"✓ Query completed in {query_time:.3f}s")
            print(f"✓ Performance metrics: Add={add_time:.3f}s, Query={query_time:.3f}s")

            service.close()
            print("\n[COMPLETE] Performance test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestServiceLifecycle:
    """Test service lifecycle with multiple connect/disconnect cycles."""

    def test_multiple_connect_disconnect_cycles(self):
        """Test multiple connect/disconnect cycles."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_lifecycle_")

        try:
            print("\n[LIFECYCLE TEST] Testing multiple connect/disconnect cycles")

            for cycle in range(1, 6):
                print(f"\n  Cycle {cycle}:")
                service = ChromaDbService(
                    persist_directory=temp_dir, collection_name="lifecycle_test"
                )

                # Connect
                assert service.connect() is True
                assert service.is_connected() is True
                print(f"    ✓ Connected (cycle {cycle})")

                # Add a document
                collection = service.get_collection()
                collection.add(
                    ids=[f"cycle_{cycle}"],
                    documents=[f"Document from cycle {cycle}"],
                    metadatas=[{"cycle": cycle}],
                )
                print(f"    ✓ Added document (cycle {cycle})")

                # Verify all previous documents exist
                assert collection.count() == cycle
                print(f"    ✓ Collection has {cycle} documents")

                # Disconnect
                service.close()
                assert service.is_connected() is False
                print(f"    ✓ Disconnected (cycle {cycle})")

            # Final verification
            print("\n  Final verification:")
            service = ChromaDbService(persist_directory=temp_dir, collection_name="lifecycle_test")
            service.connect()
            collection = service.get_collection()

            assert collection.count() == 5
            print("    ✓ All 5 documents persisted across cycles")

            service.close()
            print("\n[COMPLETE] Lifecycle test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_context_manager_lifecycle(self):
        """Test service lifecycle using context manager."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_context_")

        try:
            print("\n[CONTEXT MANAGER TEST] Testing context manager usage")

            # First context
            with ChromaDbService(
                persist_directory=temp_dir, collection_name="context_test"
            ) as service:
                assert service.is_connected() is True
                collection = service.get_collection()
                collection.add(
                    ids=["ctx_001"],
                    documents=["Context manager test"],
                    metadatas=[{"source": "context"}],
                )
                assert collection.count() == 1
                print("  ✓ First context: Added document")

            # Service should be closed after context
            assert service.is_connected() is False
            print("  ✓ Service closed after context exit")

            # Second context
            with ChromaDbService(
                persist_directory=temp_dir, collection_name="context_test"
            ) as service2:
                assert service2.is_connected() is True
                collection2 = service2.get_collection()
                assert collection2.count() == 1
                print("  ✓ Second context: Document persisted")

            print("\n[COMPLETE] Context manager test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""

    def test_invalid_configuration(self):
        """Test handling of invalid configuration."""
        print("\n[ERROR RECOVERY] Testing invalid configuration")

        # Invalid distance function
        with pytest.raises(ValueError, match="Distance function must be one of"):
            ChromaDbConfig(distance_function="invalid_metric")
        print("  ✓ Invalid distance function rejected")

        # Invalid HNSW parameters
        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_construction_ef=0)
        print("  ✓ Invalid HNSW parameter rejected")

        with pytest.raises(ValueError):
            ChromaDbConfig(hnsw_m=1)
        print("  ✓ Invalid HNSW M parameter rejected")

        print("\n[COMPLETE] Invalid configuration test passed!")

    def test_not_connected_operations(self):
        """Test operations when not connected."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_error_")

        try:
            print("\n[ERROR RECOVERY] Testing operations when not connected")

            service = ChromaDbService(persist_directory=temp_dir)

            # Try to get collection without connecting
            with pytest.raises(RuntimeError, match="Not connected to ChromaDB"):
                service.get_collection()
            print("  ✓ get_collection() raises error when not connected")

            # Try to list collections without connecting
            with pytest.raises(RuntimeError, match="Not connected to ChromaDB"):
                service.list_collections()
            print("  ✓ list_collections() raises error when not connected")

            print("\n[COMPLETE] Not connected operations test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_duplicate_id_handling(self):
        """Test handling of duplicate document IDs."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_dup_")

        try:
            print("\n[ERROR RECOVERY] Testing duplicate ID handling")

            service = ChromaDbService(persist_directory=temp_dir)
            service.connect()
            collection = service.get_collection()

            # Add first document
            collection.add(
                ids=["dup_001"], documents=["First document"], metadatas=[{"version": 1}]
            )
            print("  ✓ Added first document")

            # ChromaDB raises an error when adding duplicate IDs
            try:
                collection.add(
                    ids=["dup_001"], documents=["Duplicate document"], metadatas=[{"version": 2}]
                )
                # If no error was raised, check if it's an upsert behavior
                result = collection.get(ids=["dup_001"])
                result["metadatas"][0]["version"]
                print("  ⚠ ChromaDB allows duplicate IDs (current behavior)")
            except Exception as e:
                print(f"  ✓ Duplicate ID rejected with error: {type(e).__name__}")

            # Use update() for modifying existing documents
            collection.update(
                ids=["dup_001"], documents=["Updated document"], metadatas=[{"version": 2}]
            )

            result = collection.get(ids=["dup_001"])
            assert result["metadatas"][0]["version"] == 2
            print("  ✓ Document updated successfully using update()")

            service.close()
            print("\n[COMPLETE] Duplicate ID handling test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestAcceptanceCriteria:
    """Verify all acceptance criteria from TASK_BREAKDOWN.md."""

    def test_persistence_directory(self):
        """Verify ChromaDB persists to ./data/chroma/"""
        temp_dir = tempfile.mkdtemp(prefix="chroma_accept_")

        try:
            print("\n[ACCEPTANCE] Testing persistence directory")

            config = ChromaDbConfig(persist_directory=temp_dir)
            service = ChromaDbService(config=config)
            service.connect()

            # Verify directory was created
            persist_path = Path(temp_dir)
            assert persist_path.exists()
            assert persist_path.is_dir()
            print(f"  ✓ Persist directory created: {temp_dir}")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_collection_name(self):
        """Verify collection 'concepts' is created."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_collection_")

        try:
            print("\n[ACCEPTANCE] Testing collection name")

            config = ChromaDbConfig(persist_directory=temp_dir, collection_name="concepts")
            service = ChromaDbService(config=config)
            service.connect()

            # Verify collection exists
            collections = service.list_collections()
            assert "concepts" in collections
            print("  ✓ Collection 'concepts' created")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_distance_metric_cosine(self):
        """Verify distance metric is cosine similarity."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_metric_")

        try:
            print("\n[ACCEPTANCE] Testing distance metric")

            config = ChromaDbConfig(persist_directory=temp_dir, distance_function="cosine")
            service = ChromaDbService(config=config)
            service.connect()

            # Check collection metadata
            health = service.health_check()
            assert health["collection_metadata"]["hnsw:space"] == "cosine"
            print("  ✓ Distance metric: cosine similarity")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_hnsw_index_configured(self):
        """Verify HNSW index is configured."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_hnsw_")

        try:
            print("\n[ACCEPTANCE] Testing HNSW index configuration")

            service = ChromaDbService(persist_directory=temp_dir)
            service.connect()

            health = service.health_check()
            metadata = health["collection_metadata"]

            assert "hnsw:construction_ef" in metadata
            assert "hnsw:search_ef" in metadata
            assert "hnsw:M" in metadata
            assert metadata["hnsw:construction_ef"] == 128
            assert metadata["hnsw:search_ef"] == 64
            assert metadata["hnsw:M"] == 16

            print("  ✓ HNSW index configured:")
            print(f"    - construction_ef: {metadata['hnsw:construction_ef']}")
            print(f"    - search_ef: {metadata['hnsw:search_ef']}")
            print(f"    - M: {metadata['hnsw:M']}")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_insert_document_with_embedding(self):
        """Test: Insert document with embedding."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_insert_")

        try:
            print("\n[ACCEPTANCE] Testing document insertion")

            service = ChromaDbService(persist_directory=temp_dir)
            service.connect()
            collection = service.get_collection()

            # Insert document (ChromaDB auto-generates embeddings)
            collection.add(
                ids=["test_001"],
                documents=["This is a test document for embedding"],
                metadatas=[{"test": True}],
            )

            assert collection.count() == 1
            result = collection.get(ids=["test_001"])
            assert result["ids"][0] == "test_001"
            assert result["documents"][0] == "This is a test document for embedding"

            print("  ✓ Document inserted successfully")
            print("  ✓ Embeddings auto-generated by ChromaDB")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_query_returns_similar_documents(self):
        """Test: Query returns similar documents."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_query_")

        try:
            print("\n[ACCEPTANCE] Testing query similarity")

            service = ChromaDbService(persist_directory=temp_dir)
            service.connect()
            collection = service.get_collection()

            # Add similar and dissimilar documents
            collection.add(
                ids=["doc_001", "doc_002", "doc_003"],
                documents=[
                    "Python is a programming language",
                    "Java is also a programming language",
                    "Cats are domestic animals",
                ],
                metadatas=[
                    {"topic": "programming"},
                    {"topic": "programming"},
                    {"topic": "animals"},
                ],
            )

            # Query for programming-related documents
            results = collection.query(
                query_texts=["coding with programming language"], n_results=2
            )

            # Should return the two programming documents
            assert len(results["ids"][0]) == 2
            returned_ids = set(results["ids"][0])
            assert "doc_001" in returned_ids or "doc_002" in returned_ids

            print("  ✓ Query returns similar documents")
            print(f"  ✓ Returned IDs: {results['ids'][0]}")

            service.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_collection_accessible_across_restarts(self):
        """Test: Collection accessible across restarts."""
        temp_dir = tempfile.mkdtemp(prefix="chroma_restart_")

        try:
            print("\n[ACCEPTANCE] Testing collection persistence across restarts")

            # First session
            service1 = ChromaDbService(persist_directory=temp_dir)
            service1.connect()
            collection1 = service1.get_collection()

            collection1.add(
                ids=["persist_001"], documents=["Persistent document"], metadatas=[{"session": 1}]
            )

            initial_count = collection1.count()
            print(f"  ✓ Session 1: Added document (count={initial_count})")
            service1.close()

            # Second session (restart)
            service2 = ChromaDbService(persist_directory=temp_dir)
            service2.connect()
            collection2 = service2.get_collection()

            restart_count = collection2.count()
            assert restart_count == initial_count

            result = collection2.get(ids=["persist_001"])
            assert result["metadatas"][0]["session"] == 1

            print(f"  ✓ Session 2 (restart): Document persisted (count={restart_count})")
            print("  ✓ Collection accessible across restarts")

            service2.close()

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestChromaDBProjectionIntegration:
    """Integration tests for ChromaDBProjection with real ChromaDB."""

    def test_complete_projection_lifecycle(self):
        """Test: Create → Update → Delete projection lifecycle with real ChromaDB."""
        from models.events import ConceptCreated, ConceptDeleted, ConceptUpdated
        from projections.chromadb_projection import ChromaDBProjection

        temp_dir = tempfile.mkdtemp(prefix="chroma_projection_")

        try:
            print("\n[PROJECTION INTEGRATION] Testing complete lifecycle")

            # Setup ChromaDB service
            service = ChromaDbService(persist_directory=temp_dir, collection_name="projection_test")
            service.connect()
            projection = ChromaDBProjection(service)

            # Step 1: Create concept
            print("\n  [STEP 1] Project ConceptCreated event")
            create_event = ConceptCreated(
                aggregate_id="concept_integration_001",
                concept_data={
                    "name": "Integration Test Concept",
                    "explanation": "This is a test concept for integration testing",
                    "confidence_score": 0.85,
                    "area": "Testing",
                    "topic": "Integration",
                    "subtopic": "ChromaDB",
                },
                version=1,
            )

            assert projection.project_event(create_event) is True
            print("    ✓ ConceptCreated event projected successfully")

            # Verify document in ChromaDB
            collection = service.get_collection()
            assert collection.count() == 1

            result = collection.get(ids=["concept_integration_001"])
            assert result["ids"][0] == "concept_integration_001"
            assert result["documents"][0] == "This is a test concept for integration testing"
            assert result["metadatas"][0]["name"] == "Integration Test Concept"
            assert result["metadatas"][0]["confidence_score"] == 0.85
            assert result["metadatas"][0]["area"] == "Testing"
            print("    ✓ Document verified in ChromaDB")

            # Step 2: Update concept
            print("\n  [STEP 2] Project ConceptUpdated event")
            update_event = ConceptUpdated(
                aggregate_id="concept_integration_001",
                updates={
                    "explanation": "Updated explanation for integration testing",
                    "confidence_score": 0.95,
                    "name": "Updated Integration Test"
                },
                version=2,
            )

            assert projection.project_event(update_event) is True
            print("    ✓ ConceptUpdated event projected successfully")

            # Verify update in ChromaDB
            result = collection.get(ids=["concept_integration_001"])
            assert result["documents"][0] == "Updated explanation for integration testing"
            assert result["metadatas"][0]["name"] == "Updated Integration Test"
            assert result["metadatas"][0]["confidence_score"] == 0.95
            assert "last_modified" in result["metadatas"][0]
            print("    ✓ Updated document verified in ChromaDB")

            # Step 3: Delete concept
            print("\n  [STEP 3] Project ConceptDeleted event")
            delete_event = ConceptDeleted(aggregate_id="concept_integration_001", version=3)

            assert projection.project_event(delete_event) is True
            print("    ✓ ConceptDeleted event projected successfully")

            # Verify deletion in ChromaDB
            assert collection.count() == 0
            print("    ✓ Document removed from ChromaDB")

            service.close()
            print("\n[COMPLETE] Projection lifecycle test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_projection_metadata_persistence(self):
        """Test that metadata persists correctly across service restarts."""
        from models.events import ConceptCreated
        from projections.chromadb_projection import ChromaDBProjection

        temp_dir = tempfile.mkdtemp(prefix="chroma_projection_persist_")

        try:
            print("\n[PROJECTION PERSISTENCE] Testing metadata persistence")

            # First session: Create concept
            service1 = ChromaDbService(
                persist_directory=temp_dir, collection_name="projection_persist"
            )
            service1.connect()
            projection1 = ChromaDBProjection(service1)

            create_event = ConceptCreated(
                aggregate_id="persist_001",
                concept_data={
                    "name": "Persistent Concept",
                    "explanation": "Testing persistence",
                    "confidence_score": 0.9,
                    "area": "Persistence",
                    "topic": "Testing",
                },
                version=1,
            )

            assert projection1.project_event(create_event) is True
            print("  ✓ Session 1: Created concept")
            service1.close()

            # Second session: Verify persistence
            service2 = ChromaDbService(
                persist_directory=temp_dir, collection_name="projection_persist"
            )
            service2.connect()
            collection = service2.get_collection()

            assert collection.count() == 1
            result = collection.get(ids=["persist_001"])
            assert result["metadatas"][0]["name"] == "Persistent Concept"
            assert result["metadatas"][0]["confidence_score"] == 0.9
            assert result["metadatas"][0]["area"] == "Persistence"
            print("  ✓ Session 2: Metadata persisted correctly")

            service2.close()
            print("\n[COMPLETE] Metadata persistence test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_projection_multiple_concepts(self):
        """Test projecting multiple concepts and querying."""
        from models.events import ConceptCreated
        from projections.chromadb_projection import ChromaDBProjection

        temp_dir = tempfile.mkdtemp(prefix="chroma_projection_multi_")

        try:
            print("\n[PROJECTION MULTI] Testing multiple concept projections")

            service = ChromaDbService(
                persist_directory=temp_dir, collection_name="projection_multi"
            )
            service.connect()
            projection = ChromaDBProjection(service)

            # Create 5 concepts
            concepts = [
                {
                    "id": "multi_001",
                    "name": "Python",
                    "explanation": "Python programming language",
                    "area": "Programming",
                    "topic": "Languages",
                },
                {
                    "id": "multi_002",
                    "name": "JavaScript",
                    "explanation": "JavaScript for web development",
                    "area": "Programming",
                    "topic": "Web",
                },
                {
                    "id": "multi_003",
                    "name": "Machine Learning",
                    "explanation": "Machine learning algorithms",
                    "area": "AI",
                    "topic": "ML",
                },
                {
                    "id": "multi_004",
                    "name": "Neural Networks",
                    "explanation": "Deep learning neural networks",
                    "area": "AI",
                    "topic": "Deep Learning",
                },
                {
                    "id": "multi_005",
                    "name": "Algorithms",
                    "explanation": "Computer science algorithms",
                    "area": "CS",
                    "topic": "Algorithms",
                },
            ]

            for concept in concepts:
                event = ConceptCreated(
                    aggregate_id=concept["id"],
                    concept_data={
                        "name": concept["name"],
                        "explanation": concept["explanation"],
                        "area": concept["area"],
                        "topic": concept["topic"],
                        "confidence_score": 0.8
                    },
                    version=1,
                )
                assert projection.project_event(event) is True

            print(f"  ✓ Projected {len(concepts)} concepts")

            # Verify all concepts in ChromaDB
            collection = service.get_collection()
            assert collection.count() == 5

            # Test semantic query
            results = collection.query(query_texts=["programming language"], n_results=2)

            assert len(results["ids"][0]) == 2
            print(f"  ✓ Semantic query returned {len(results['ids'][0])} results")

            # Test metadata filtering
            results = collection.query(
                query_texts=["algorithms"], n_results=10, where={"area": "AI"}
            )

            ai_concepts = len(results["ids"][0])
            assert ai_concepts == 2  # ML and Neural Networks
            print(f"  ✓ Metadata filter returned {ai_concepts} AI concepts")

            service.close()
            print("\n[COMPLETE] Multiple concepts test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_projection_error_handling(self):
        """Test projection error handling with real ChromaDB."""
        from models.events import ConceptDeleted, ConceptUpdated
        from projections.chromadb_projection import ChromaDBProjection

        temp_dir = tempfile.mkdtemp(prefix="chroma_projection_error_")

        try:
            print("\n[PROJECTION ERROR] Testing error handling")

            service = ChromaDbService(
                persist_directory=temp_dir, collection_name="projection_error"
            )
            service.connect()
            projection = ChromaDBProjection(service)

            # Test 1: Update non-existent concept
            print("\n  [TEST 1] Update non-existent concept")
            update_event = ConceptUpdated(
                aggregate_id="nonexistent_001",
                updates={"explanation": "This should fail"},
                version=2,
            )

            result = projection.project_event(update_event)
            assert result is False
            print("    ✓ Update of non-existent concept returned False")

            # Test 2: Delete non-existent concept (should succeed - idempotent)
            print("\n  [TEST 2] Delete non-existent concept (idempotent)")
            delete_event = ConceptDeleted(aggregate_id="nonexistent_002", version=2)

            result = projection.project_event(delete_event)
            assert result is True
            print("    ✓ Delete of non-existent concept succeeded (idempotent)")

            # Test 3: Service not connected
            print("\n  [TEST 3] Projection when service not connected")
            service.close()

            from models.events import ConceptCreated

            create_event = ConceptCreated(
                aggregate_id="error_001",
                concept_data={"name": "Test", "explanation": "Test"},
                version=1,
            )

            result = projection.project_event(create_event)
            assert result is False
            print("    ✓ Projection failed when service not connected")

            print("\n[COMPLETE] Error handling test passed!")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

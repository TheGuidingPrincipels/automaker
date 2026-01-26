#!/usr/bin/env python3
"""
ChromaDB Initialization Script

Initializes ChromaDB persistent storage and creates the concepts collection.
This script should be run once to set up the vector database.

Usage:
    python scripts/init_chromadb.py
"""

import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.chromadb_service import ChromaDbConfig, ChromaDbService


def main():
    """Initialize ChromaDB with concepts collection."""
    print("=" * 60)
    print("ChromaDB Initialization Script")
    print("=" * 60)
    print()

    # Create config from environment
    config = ChromaDbConfig(
        persist_directory=Config.CHROMA_PERSIST_DIRECTORY,
        collection_name="concepts",
    )

    print(f"📁 Persist Directory: {config.persist_directory}")
    print(f"📦 Collection Name: {config.collection_name}")
    print(f"📏 Distance Function: {config.distance_function}")
    print("🔧 HNSW Parameters:")
    print(f"   - construction_ef: {config.hnsw_construction_ef}")
    print(f"   - search_ef: {config.hnsw_search_ef}")
    print(f"   - M: {config.hnsw_m}")
    print()

    # Initialize service
    print("🔌 Connecting to ChromaDB...")
    service = ChromaDbService(config=config)

    if not service.connect():
        print("❌ Failed to connect to ChromaDB")
        return 1

    print("✅ Connected successfully!")
    print()

    # Verify collection
    print("🔍 Verifying collection...")
    health = service.health_check()

    if health["status"] == "healthy":
        print(f"✅ Collection '{health['collection_name']}' is healthy")
        print(f"   - Document count: {health['collection_count']}")
        print(f"   - Metadata: {health['collection_metadata']}")
    else:
        print(f"❌ Collection health check failed: {health.get('error', 'Unknown error')}")
        return 1

    print()

    # Test persistence by closing and reopening
    print("🔄 Testing persistence (close and reopen)...")
    service.close()
    print("   - Closed connection")

    service2 = ChromaDbService(config=config)
    if not service2.connect():
        print("❌ Failed to reconnect to ChromaDB")
        return 1

    print("   - Reconnected successfully")

    # Verify collection still exists
    collections = service2.list_collections()
    if config.collection_name in collections:
        print("✅ Collection persisted across restarts")
    else:
        print("❌ Collection not found after restart")
        return 1

    print()

    # Add a test document (if collection is empty)
    collection = service2.get_collection()
    if collection.count() == 0:
        print("📝 Adding test document...")
        collection.add(
            ids=["test_concept_001"],
            documents=["This is a test concept for ChromaDB initialization"],
            metadatas=[{
                "name": "Test Concept",
                "area": "Testing",
                "topic": "Initialization",
                "confidence_score": 100
            }]
        )
        print("   - Test document added")
        print()

        # Query test
        print("🔎 Testing query...")
        results = collection.query(query_texts=["test concept"], n_results=1)
        if results and results["ids"] and results["ids"][0]:
            print(f"   - Query successful! Found: {results['ids'][0][0]}")
        else:
            print("   - Query returned no results")

    service2.close()
    print()

    print("=" * 60)
    print("✅ ChromaDB initialization complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run tests: pytest tests/test_chromadb_service.py -v")
    print(
        "2. Verify collection: python -c \"import chromadb; client = chromadb.PersistentClient('./data/chroma'); print(client.list_collections())\""
    )
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

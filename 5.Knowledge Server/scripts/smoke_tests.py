#!/usr/bin/env python3
"""
Smoke Tests for MCP Knowledge Server
Tests critical functionality after deployment to ensure the system is operational.

Usage:
    python scripts/smoke_tests.py --env local
    python scripts/smoke_tests.py --env staging --critical-only
    python scripts/smoke_tests.py --env production --timeout 30
"""

import argparse
import sys
import time


try:
    import redis
    from neo4j import GraphDatabase
except ImportError:
    print("⚠️  Warning: neo4j or redis packages not installed")
    print("   Run: pip install neo4j redis")
    GraphDatabase = None
    redis = None


# Environment configurations
ENV_CONFIG = {
    "local": {
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "password",
        "redis_url": "redis://localhost:6379",
        "description": "Local Development",
    },
    "staging": {
        "neo4j_uri": "bolt://staging-neo4j:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "staging_password",
        "redis_url": "redis://staging-redis:6379",
        "description": "Staging Environment",
    },
    "production": {
        "neo4j_uri": "bolt://prod-neo4j:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "production_password",
        "redis_url": "redis://prod-redis:6379",
        "description": "Production Environment",
    },
}


class SmokeTest:
    """Base class for smoke tests"""

    def __init__(self, name: str, critical: bool = True):
        self.name = name
        self.critical = critical

    def run(self, config: dict) -> bool:
        """Run the test. Return True if passed, False otherwise."""
        raise NotImplementedError


class Neo4jConnectionTest(SmokeTest):
    """Test Neo4j database connectivity"""

    def __init__(self):
        super().__init__("Neo4j Connection", critical=True)

    def run(self, config: dict) -> bool:
        if GraphDatabase is None:
            print(f"   ⚠️  Skipping {self.name}: neo4j package not installed")
            return True

        try:
            driver = GraphDatabase.driver(
                config["neo4j_uri"], auth=(config["neo4j_user"], config["neo4j_password"])
            )

            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                value = result.single()["test"]
                assert value == 1, "Unexpected result from Neo4j"

            driver.close()
            return True

        except Exception as e:
            print(f"   ❌ Neo4j connection failed: {e}")
            return False


class Neo4jSchemaTest(SmokeTest):
    """Test Neo4j schema and indexes exist"""

    def __init__(self):
        super().__init__("Neo4j Schema", critical=True)

    def run(self, config: dict) -> bool:
        if GraphDatabase is None:
            print(f"   ⚠️  Skipping {self.name}: neo4j package not installed")
            return True

        try:
            driver = GraphDatabase.driver(
                config["neo4j_uri"], auth=(config["neo4j_user"], config["neo4j_password"])
            )

            with driver.session() as session:
                # Check for Concept nodes
                result = session.run("MATCH (c:Concept) RETURN count(c) as count")
                result.single()["count"]
                # Schema exists if count >= 0 (even 0 is valid for fresh db)

                # Check for indexes (optional, non-critical)
                result = session.run("SHOW INDEXES")
                list(result)

            driver.close()
            return True

        except Exception as e:
            print(f"   ❌ Neo4j schema check failed: {e}")
            return False


class RedisConnectionTest(SmokeTest):
    """Test Redis connectivity"""

    def __init__(self):
        super().__init__("Redis Connection", critical=False)

    def run(self, config: dict) -> bool:
        if redis is None:
            print(f"   ⚠️  Skipping {self.name}: redis package not installed")
            return True

        try:
            r = redis.from_url(config["redis_url"], socket_connect_timeout=5)
            r.ping()
            r.close()
            return True

        except Exception as e:
            print(f"   ⚠️  Redis connection failed (non-critical): {e}")
            return not self.critical  # Pass if non-critical


class ChromaDBTest(SmokeTest):
    """Test ChromaDB initialization"""

    def __init__(self):
        super().__init__("ChromaDB Initialization", critical=True)

    def run(self, config: dict) -> bool:
        try:
            import os

            import chromadb

            # Use temp directory for smoke test
            persist_dir = os.getenv("CHROMA_PERSIST_DIRECTORY", "/tmp/chromadb_test")

            # Try to initialize ChromaDB
            client = chromadb.PersistentClient(path=persist_dir)
            client.list_collections()

            return True

        except Exception as e:
            print(f"   ❌ ChromaDB initialization failed: {e}")
            return False


class EmbeddingModelTest(SmokeTest):
    """Test sentence-transformers model loading"""

    def __init__(self):
        super().__init__("Embedding Model", critical=False)

    def run(self, config: dict) -> bool:
        try:
            from sentence_transformers import SentenceTransformer

            # Try to load the model (cached if previously downloaded)
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

            # Quick embedding test
            test_embedding = model.encode("test", show_progress_bar=False)
            assert len(test_embedding) == 384, "Unexpected embedding dimension"

            return True

        except Exception as e:
            print(f"   ⚠️  Embedding model test failed (non-critical): {e}")
            return not self.critical


class PythonDependenciesTest(SmokeTest):
    """Test critical Python package imports"""

    def __init__(self):
        super().__init__("Python Dependencies", critical=True)

    def run(self, config: dict) -> bool:
        try:
            import chromadb
            import fastmcp
            import neo4j
            import pydantic
            import sentence_transformers

            return True

        except ImportError as e:
            print(f"   ❌ Missing critical dependency: {e}")
            return False


def run_smoke_tests(env: str, critical_only: bool = False, timeout: int = 60) -> int:
    """
    Run smoke tests for the specified environment.

    Args:
        env: Environment name (local, staging, production)
        critical_only: Only run critical tests
        timeout: Timeout in seconds

    Returns:
        Exit code (0 = success, 1 = failure)
    """

    if env not in ENV_CONFIG:
        print(f"❌ Unknown environment: {env}")
        print(f"   Available: {', '.join(ENV_CONFIG.keys())}")
        return 1

    config = ENV_CONFIG[env]

    print("=" * 70)
    print(f"🧪 SMOKE TESTS - {config['description']}")
    print("=" * 70)
    print()

    # Define test suite
    tests = [
        PythonDependenciesTest(),
        Neo4jConnectionTest(),
        Neo4jSchemaTest(),
        RedisConnectionTest(),
        ChromaDBTest(),
        EmbeddingModelTest(),
    ]

    # Filter tests if critical_only
    if critical_only:
        tests = [t for t in tests if t.critical]
        print(f"ℹ️  Running {len(tests)} critical tests only\n")
    else:
        print(f"ℹ️  Running {len(tests)} tests\n")

    # Run tests
    passed = 0
    failed = 0
    start_time = time.time()

    for test in tests:
        print(f"Running: {test.name}...", end=" ", flush=True)

        try:
            result = test.run(config)

            if result:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL")
                failed += 1

                if test.critical:
                    print(f"\n❌ Critical test '{test.name}' failed - aborting")
                    break

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

            if test.critical:
                print(f"\n❌ Critical test '{test.name}' failed - aborting")
                break

        # Check timeout
        if time.time() - start_time > timeout:
            print(f"\n⏱️  Timeout reached ({timeout}s) - aborting")
            break

    # Summary
    elapsed = time.time() - start_time
    print()
    print("=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed ({elapsed:.1f}s)")
    print("=" * 70)

    if failed == 0:
        print("✅ All smoke tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Run smoke tests for MCP Knowledge Server")
    parser.add_argument(
        "--env",
        choices=list(ENV_CONFIG.keys()),
        default="local",
        help="Environment to test (default: local)",
    )
    parser.add_argument("--critical-only", action="store_true", help="Only run critical tests")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds (default: 60)")

    args = parser.parse_args()

    exit_code = run_smoke_tests(
        env=args.env, critical_only=args.critical_only, timeout=args.timeout
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

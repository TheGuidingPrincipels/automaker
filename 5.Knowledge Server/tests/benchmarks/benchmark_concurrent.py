"""
Concurrency benchmarks for MCP Knowledge Management Server.

Tests 5, 10, 20 parallel operations measuring throughput and checking
for race conditions or deadlocks.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services
import sys


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import Config
from projections.chromadb_projection import ChromaDBProjection
from projections.neo4j_projection import Neo4jProjection
from services.chromadb_service import ChromaDbService
from services.compensation import CompensationManager
from services.embedding_cache import EmbeddingCache
from services.embedding_service import EmbeddingConfig, EmbeddingService
from services.event_store import EventStore
from services.neo4j_service import Neo4jService
from services.outbox import Outbox
from services.repository import DualStorageRepository
from tools import analytics_tools, concept_tools, relationship_tools, search_tools


class ConcurrencyBenchmark:
    """Tests concurrent operations and throughput"""

    def __init__(self):
        self.results = {}
        self.repository = None

    async def setup(self):
        """Initialize services"""
        logger.info("Setting up concurrency benchmark environment...")

        # Initialize services
        event_store = EventStore()
        outbox = Outbox()

        neo4j_service = Neo4jService(
            uri=Config.NEO4J_URI, user=Config.NEO4J_USER, password=Config.NEO4J_PASSWORD
        )

        chromadb_service = ChromaDbService(
            persist_directory=Config.CHROMA_PERSIST_DIRECTORY, collection_name="concepts"
        )

        embedding_config = EmbeddingConfig(model_name=Config.EMBEDDING_MODEL)
        embedding_service = EmbeddingService(config=embedding_config)
        embedding_cache = EmbeddingCache(db_path=Config.EVENT_STORE_PATH)

        neo4j_projection = Neo4jProjection(neo4j_service)
        chromadb_projection = ChromaDBProjection(chromadb_service)

        compensation_manager = CompensationManager(
            neo4j_service=neo4j_service,
            chromadb_service=chromadb_service,
            db_path=Config.EVENT_STORE_PATH,
        )

        self.repository = DualStorageRepository(
            event_store=event_store,
            outbox=outbox,
            neo4j_projection=neo4j_projection,
            chromadb_projection=chromadb_projection,
            embedding_service=embedding_service,
            embedding_cache=embedding_cache,
            compensation_manager=compensation_manager,
        )

        # Inject into tools
        concept_tools.repository = self.repository
        search_tools.chromadb_service = chromadb_service
        search_tools.neo4j_service = neo4j_service
        search_tools.embedding_service = embedding_service
        relationship_tools.neo4j_service = neo4j_service
        relationship_tools.event_store = event_store
        relationship_tools.outbox = outbox
        analytics_tools.neo4j_service = neo4j_service

        logger.info("✅ Services initialized")

    async def benchmark_concurrent_creates(self, parallel_count: int):
        """Benchmark concurrent concept creation"""
        logger.info(f"Testing {parallel_count} parallel concept creations...")

        async def create_concept_task(index: int):
            """Single concept creation task"""
            return await concept_tools.create_concept(
                name=f"Concurrent Test Concept {index}",
                explanation=f"Test concept created during {parallel_count}x concurrency test",
                area="Testing",
                topic="Concurrency",
            )

        start_time = time.perf_counter()

        # Run parallel operations
        tasks = [create_concept_task(i) for i in range(parallel_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Check for errors
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception) or not isinstance(r, dict))

        throughput = parallel_count / (duration_ms / 1000) if duration_ms > 0 else 0

        result = {
            "test": "concurrent_creates",
            "parallel_count": parallel_count,
            "total_operations": parallel_count,
            "successful": successful,
            "errors": errors,
            "duration_ms": duration_ms,
            "throughput_ops_per_sec": throughput,
            "avg_latency_ms": duration_ms / parallel_count if parallel_count > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ {parallel_count}x creates: {successful}/{parallel_count} successful, "
            f"{throughput:.2f} ops/sec"
        )

        return result

    async def benchmark_concurrent_reads(self, parallel_count: int):
        """Benchmark concurrent concept reads"""
        logger.info(f"Testing {parallel_count} parallel concept reads...")

        # Create a test concept first
        create_result = await concept_tools.create_concept(
            name="Read Test Concept", explanation="Concept for read concurrency testing"
        )

        if not create_result.get("success"):
            logger.error("Failed to create test concept for reads")
            return None

        concept_id = create_result["concept_id"]

        async def read_concept_task():
            """Single concept read task"""
            return await concept_tools.get_concept(concept_id=concept_id)

        start_time = time.perf_counter()

        # Run parallel operations
        tasks = [read_concept_task() for _ in range(parallel_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Check for errors
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception) or not isinstance(r, dict))

        throughput = parallel_count / (duration_ms / 1000) if duration_ms > 0 else 0

        result = {
            "test": "concurrent_reads",
            "parallel_count": parallel_count,
            "total_operations": parallel_count,
            "successful": successful,
            "errors": errors,
            "duration_ms": duration_ms,
            "throughput_ops_per_sec": throughput,
            "avg_latency_ms": duration_ms / parallel_count if parallel_count > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ {parallel_count}x reads: {successful}/{parallel_count} successful, "
            f"{throughput:.2f} ops/sec"
        )

        return result

    async def benchmark_concurrent_searches(self, parallel_count: int):
        """Benchmark concurrent semantic searches"""
        logger.info(f"Testing {parallel_count} parallel semantic searches...")

        queries = [
            "Python programming",
            "JavaScript basics",
            "Data structures",
            "Machine learning",
            "Web development",
        ]

        async def search_task(index: int):
            """Single search task"""
            query = queries[index % len(queries)]
            return await search_tools.search_concepts_semantic(query=query, limit=10)

        start_time = time.perf_counter()

        # Run parallel operations
        tasks = [search_task(i) for i in range(parallel_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Check for errors
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception) or not isinstance(r, dict))

        throughput = parallel_count / (duration_ms / 1000) if duration_ms > 0 else 0

        result = {
            "test": "concurrent_searches",
            "parallel_count": parallel_count,
            "total_operations": parallel_count,
            "successful": successful,
            "errors": errors,
            "duration_ms": duration_ms,
            "throughput_ops_per_sec": throughput,
            "avg_latency_ms": duration_ms / parallel_count if parallel_count > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ {parallel_count}x searches: {successful}/{parallel_count} successful, "
            f"{throughput:.2f} ops/sec"
        )

        return result

    async def benchmark_mixed_operations(self, parallel_count: int):
        """Benchmark mixed concurrent operations (creates, reads, searches)"""
        logger.info(f"Testing {parallel_count} parallel mixed operations...")

        # Create a test concept for reads
        create_result = await concept_tools.create_concept(
            name="Mixed Test Concept", explanation="Concept for mixed operation testing"
        )
        concept_id = create_result.get("concept_id") if create_result.get("success") else None

        async def mixed_task(index: int):
            """Mixed operation task"""
            operation_type = index % 3

            if operation_type == 0:
                # Create
                return await concept_tools.create_concept(
                    name=f"Mixed Concept {index}", explanation="Test concept for mixed operations"
                )
            elif operation_type == 1 and concept_id:
                # Read
                return await concept_tools.get_concept(concept_id=concept_id)
            else:
                # Search
                return await search_tools.search_concepts_semantic(query="test concept", limit=5)

        start_time = time.perf_counter()

        # Run parallel operations
        tasks = [mixed_task(i) for i in range(parallel_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000

        # Check for errors
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        errors = sum(1 for r in results if isinstance(r, Exception) or not isinstance(r, dict))

        throughput = parallel_count / (duration_ms / 1000) if duration_ms > 0 else 0

        result = {
            "test": "mixed_operations",
            "parallel_count": parallel_count,
            "total_operations": parallel_count,
            "successful": successful,
            "errors": errors,
            "duration_ms": duration_ms,
            "throughput_ops_per_sec": throughput,
            "avg_latency_ms": duration_ms / parallel_count if parallel_count > 0 else 0,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(
            f"✅ {parallel_count}x mixed: {successful}/{parallel_count} successful, "
            f"{throughput:.2f} ops/sec"
        )

        return result

    async def run_all_concurrency_tests(self):
        """Run all concurrency tests at 5, 10, 20 parallel levels"""
        logger.info("Starting concurrency test suite...")

        parallel_levels = [5, 10, 20]

        for level in parallel_levels:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing at {level}x parallelism")
            logger.info(f"{'='*60}")

            # Concurrent creates
            result = await self.benchmark_concurrent_creates(level)
            self.results[f"concurrent_creates_{level}x"] = result

            # Small delay between tests
            await asyncio.sleep(1)

            # Concurrent reads
            result = await self.benchmark_concurrent_reads(level)
            self.results[f"concurrent_reads_{level}x"] = result

            await asyncio.sleep(1)

            # Concurrent searches
            result = await self.benchmark_concurrent_searches(level)
            self.results[f"concurrent_searches_{level}x"] = result

            await asyncio.sleep(1)

            # Mixed operations
            result = await self.benchmark_mixed_operations(level)
            self.results[f"mixed_operations_{level}x"] = result

            await asyncio.sleep(2)

        logger.info(f"\n✅ Completed {len(self.results)} concurrency tests")

    def save_results(self, output_file: str = "concurrent_results.json"):
        """Save concurrency results to JSON file"""
        output_path = Path(__file__).parent / output_file

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"✅ Results saved to {output_path}")


async def main():
    """Main entry point for concurrency benchmarks"""
    benchmark = ConcurrencyBenchmark()

    try:
        await benchmark.setup()
        await benchmark.run_all_concurrency_tests()
        benchmark.save_results()

        print("\n" + "=" * 80)
        print("CONCURRENCY BENCHMARK SUMMARY")
        print("=" * 80)

        for test_name, result in benchmark.results.items():
            print(f"\n{test_name}:")
            print(f"  Parallel: {result['parallel_count']}x")
            print(f"  Success: {result['successful']}/{result['total_operations']}")
            print(f"  Throughput: {result['throughput_ops_per_sec']:.2f} ops/sec")
            print(f"  Avg Latency: {result['avg_latency_ms']:.2f}ms")

        print("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Concurrency benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

"""
Individual tool benchmarks for MCP Knowledge Management Server.

Measures P50, P95, P99 response times for each of the 14 MCP tools
with 100+ iterations using realistic data sizes.
"""

import asyncio
import json
import logging
import statistics
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
from services.event_store import EventStore
from services.outbox import Outbox
from services.neo4j_service import Neo4jService
from services.chromadb_service import ChromaDbService
from services.embedding_service import EmbeddingService, EmbeddingConfig
from services.embedding_cache import EmbeddingCache
from services.repository import DualStorageRepository
from services.compensation import CompensationManager
from services.container import ServiceContainer, set_container
from projections.neo4j_projection import Neo4jProjection
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


class BenchmarkRunner:
    """Runs performance benchmarks for MCP tools"""

    def __init__(self):
        self.results = {}
        self.test_concept_ids = []
        self.repository = None

    async def setup(self):
        """Initialize services and test data"""
        logger.info("Setting up benchmark environment...")

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

        # Configure ServiceContainer
        container = ServiceContainer()
        container.event_store = event_store
        container.outbox = outbox
        container.neo4j_service = neo4j_service
        container.chromadb_service = chromadb_service
        container.embedding_service = embedding_service
        container.repository = self.repository
        container.confidence_runtime = None  # Benchmarks don't need confidence scoring
        set_container(container)

        logger.info("✅ Services initialized")

        # Create test data
        await self._create_test_data()

    async def _create_test_data(self):
        """Create test concepts for benchmarking"""
        logger.info("Creating test data...")

        test_concepts = [
            {
                "name": "Python Basics",
                "explanation": "Introduction to Python programming",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Fundamentals",
            },
            {
                "name": "Variables",
                "explanation": "Storing and managing data in memory",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Data Types",
            },
            {
                "name": "Functions",
                "explanation": "Reusable blocks of code",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Functions",
            },
            {
                "name": "Loops",
                "explanation": "Iterating over sequences",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "Control Flow",
            },
            {
                "name": "Classes",
                "explanation": "Object-oriented programming",
                "area": "Programming",
                "topic": "Python",
                "subtopic": "OOP",
            },
        ]

        for concept in test_concepts:
            result = await concept_tools.create_concept(**concept)
            if result.get("success"):
                self.test_concept_ids.append(result["data"]["concept_id"])

        # Create relationships
        if len(self.test_concept_ids) >= 2:
            await relationship_tools.create_relationship(
                source_id=self.test_concept_ids[0],
                target_id=self.test_concept_ids[1],
                relationship_type="prerequisite",
            )

        logger.info(f"✅ Created {len(self.test_concept_ids)} test concepts")

    async def benchmark_tool(self, tool_func, name: str, iterations: int = 100, **kwargs):
        """Benchmark a single tool with multiple iterations"""
        logger.info(f"Benchmarking {name}...")

        times = []

        for i in range(iterations):
            start = time.perf_counter()
            try:
                await tool_func(**kwargs)
                end = time.perf_counter()
                times.append((end - start) * 1000)  # Convert to milliseconds
            except Exception as e:
                logger.error(f"Error in {name} iteration {i}: {e}")

        if not times:
            logger.error(f"No successful iterations for {name}")
            return None

        # Calculate percentiles
        p50 = statistics.median(times)
        p95 = statistics.quantiles(times, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(times, n=100)[98]  # 99th percentile

        result = {
            "tool": name,
            "iterations": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "timestamp": datetime.now().isoformat(),
        }

        self.results[name] = result
        logger.info(f"✅ {name}: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")

        return result

    async def run_all_benchmarks(self):
        """Run benchmarks for all 14 tools"""
        logger.info("Starting benchmark suite...")

        if not self.test_concept_ids:
            logger.error("No test data available")
            return

        concept_id = self.test_concept_ids[0]

        # 1. create_concept
        await self.benchmark_tool(
            concept_tools.create_concept,
            "create_concept",
            name="Test Concept",
            explanation="This is a test concept for benchmarking purposes",
        )

        # 2. get_concept
        await self.benchmark_tool(concept_tools.get_concept, "get_concept", concept_id=concept_id)

        # 3. update_concept
        await self.benchmark_tool(
            concept_tools.update_concept, "update_concept", concept_id=concept_id
        )

        # 4. delete_concept (create fresh concepts for each iteration)
        async def delete_with_create():
            result = await concept_tools.create_concept(
                name="Temp Concept", explanation="Temporary concept for delete benchmark"
            )
            if result.get("success"):
                await concept_tools.delete_concept(result["data"]["concept_id"])

        times = []
        for _i in range(100):
            start = time.perf_counter()
            await delete_with_create()
            end = time.perf_counter()
            times.append((end - start) * 1000)

        self.results["delete_concept"] = {
            "tool": "delete_concept",
            "iterations": len(times),
            "min_ms": min(times),
            "max_ms": max(times),
            "mean_ms": statistics.mean(times),
            "median_ms": statistics.median(times),
            "p95_ms": statistics.quantiles(times, n=20)[18],
            "p99_ms": statistics.quantiles(times, n=100)[98],
            "timestamp": datetime.now().isoformat(),
        }
        logger.info("✅ delete_concept benchmarked")

        # 5. search_concepts_semantic
        await self.benchmark_tool(
            search_tools.search_concepts_semantic,
            "search_concepts_semantic",
            query="Python programming basics",
            limit=10,
        )

        # 6. search_concepts_exact
        await self.benchmark_tool(
            search_tools.search_concepts_exact,
            "search_concepts_exact",
            area="Programming",
            limit=20,
        )

        # 7. get_recent_concepts
        await self.benchmark_tool(
            search_tools.get_recent_concepts, "get_recent_concepts", days=7, limit=20
        )

        # 8. create_relationship
        if len(self.test_concept_ids) >= 2:

            async def create_rel_benchmark():
                # Create new temp concepts for relationship
                c1 = await concept_tools.create_concept(
                    name="Temp Source", explanation="Temp source concept"
                )
                c2 = await concept_tools.create_concept(
                    name="Temp Target", explanation="Temp target concept"
                )
                if c1.get("success") and c2.get("success"):
                    await relationship_tools.create_relationship(
                        source_id=c1["data"]["concept_id"],
                        target_id=c2["data"]["concept_id"],
                        relationship_type="relates_to"
                    )

            times = []
            for _i in range(50):  # Fewer iterations due to DB load
                start = time.perf_counter()
                await create_rel_benchmark()
                end = time.perf_counter()
                times.append((end - start) * 1000)

            self.results["create_relationship"] = {
                "tool": "create_relationship",
                "iterations": len(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "p95_ms": statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times),
                "p99_ms": max(times),
                "timestamp": datetime.now().isoformat(),
            }
            logger.info("✅ create_relationship benchmarked")

        # 9. delete_relationship
        if len(self.test_concept_ids) >= 2:
            await self.benchmark_tool(
                relationship_tools.delete_relationship,
                "delete_relationship",
                iterations=50,
                source_id=self.test_concept_ids[0],
                target_id=self.test_concept_ids[1],
                relationship_type="prerequisite",
            )

        # 10. get_related_concepts
        await self.benchmark_tool(
            relationship_tools.get_related_concepts,
            "get_related_concepts",
            concept_id=concept_id,
            max_depth=2,
        )

        # 11. get_prerequisites
        await self.benchmark_tool(
            relationship_tools.get_prerequisites,
            "get_prerequisites",
            concept_id=concept_id,
            max_depth=5,
        )

        # 12. get_concept_chain
        if len(self.test_concept_ids) >= 2:
            await self.benchmark_tool(
                relationship_tools.get_concept_chain,
                "get_concept_chain",
                start_id=self.test_concept_ids[0],
                end_id=self.test_concept_ids[1],
            )

        # 13. list_hierarchy
        await self.benchmark_tool(
            analytics_tools.list_hierarchy,
            "list_hierarchy",
            iterations=50,  # Fewer iterations for expensive operation
        )

        # 14. get_concepts_by_confidence
        await self.benchmark_tool(
            analytics_tools.get_concepts_by_confidence,
            "get_concepts_by_confidence",
            min_confidence=50.0,
            max_confidence=100.0
        )

        logger.info(f"✅ Benchmarked {len(self.results)} tools")

    def save_results(self, output_file: str = "benchmark_results.json"):
        """Save benchmark results to JSON file"""
        output_path = Path(__file__).parent / output_file

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"✅ Results saved to {output_path}")


async def main():
    """Main entry point for benchmarks"""
    runner = BenchmarkRunner()

    try:
        await runner.setup()
        await runner.run_all_benchmarks()
        runner.save_results()

        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        for tool_name, result in runner.results.items():
            print(f"\n{tool_name}:")
            print(f"  Iterations: {result['iterations']}")
            print(f"  P50: {result['median_ms']:.2f}ms")
            print(f"  P95: {result['p95_ms']:.2f}ms")
            print(f"  P99: {result['p99_ms']:.2f}ms")

        print("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

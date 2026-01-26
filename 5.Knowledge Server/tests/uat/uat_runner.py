#!/usr/bin/env python3
"""
UAT Test Runner for MCP Knowledge Server
Automated execution of all UAT test scenarios with detailed reporting.
"""

import asyncio
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Initialize services
from services.neo4j_service import Neo4jService
from services.chromadb_service import ChromaDbService
from services.embedding_service import EmbeddingService
from services.event_store import EventStore
from services.outbox import Outbox
from services.embedding_cache import EmbeddingCache
from services.repository import DualStorageRepository
from services.container import ServiceContainer, set_container
from projections.neo4j_projection import Neo4jProjection
from projections.chromadb_projection import ChromaDBProjection

from tools.concept_tools import (
    create_concept,
    delete_concept,
    get_concept,
    update_concept,
)
from tools.relationship_tools import (
    create_relationship,
)
from tools.analytics_tools import (
    list_hierarchy,
    get_concepts_by_confidence,
)


class UATRunner:
    """Automated UAT test execution and reporting."""

    def __init__(self, test_data_path: str, verbose: bool = False):
        self.test_data_path = Path(test_data_path)
        self.verbose = verbose
        self.results: list[dict[str, Any]] = []
        self.created_concept_ids: dict[str, str] = {}
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.services_initialized = False

    async def initialize_services(self):
        """Initialize all required services."""
        self.log("Initializing services...")

        try:
            # Load configuration
            from config import Config

            # Initialize Neo4j
            neo4j_service = Neo4jService(
                uri=Config.NEO4J_URI, user=Config.NEO4J_USER, password=Config.NEO4J_PASSWORD
            )
            if not neo4j_service.connect():
                raise Exception("Failed to connect to Neo4j")
            self.log("Neo4j connected successfully")

            # Initialize ChromaDB
            chromadb_service = ChromaDbService(
                persist_directory=Config.CHROMA_PERSIST_DIRECTORY, collection_name="concepts"
            )
            chromadb_service.connect()
            self.log("ChromaDB connected successfully")

            # Initialize Embedding Service
            embedding_service = EmbeddingService()
            await embedding_service.initialize()
            self.log("Embedding service initialized successfully")

            # Initialize EventStore and Outbox
            event_store = EventStore(db_path=Config.EVENT_STORE_PATH)
            outbox = Outbox(db_path=Config.EVENT_STORE_PATH)
            self.log("Event store and outbox initialized")

            # Initialize Embedding Cache
            embedding_cache = EmbeddingCache(db_path=Config.EVENT_STORE_PATH)
            self.log("Embedding cache initialized")

            # Create projections
            neo4j_projection = Neo4jProjection(neo4j_service)
            chromadb_projection = ChromaDBProjection(chromadb_service)
            self.log("Projections created")

            # Initialize Repository
            repository = DualStorageRepository(
                event_store=event_store,
                outbox=outbox,
                neo4j_projection=neo4j_projection,
                chromadb_projection=chromadb_projection,
                embedding_service=embedding_service,
                embedding_cache=embedding_cache,
            )
            self.log("Repository initialized")

            # Configure ServiceContainer
            container = ServiceContainer()
            container.event_store = event_store
            container.outbox = outbox
            container.neo4j_service = neo4j_service
            container.chromadb_service = chromadb_service
            container.embedding_service = embedding_service
            container.repository = repository
            container.confidence_runtime = None  # UAT tests don't need confidence scoring
            set_container(container)
            self.log("ServiceContainer configured")

            self.services_initialized = True
            self.log("All services initialized successfully")

        except Exception as e:
            self.log(f"Failed to initialize services: {e!s}", "ERROR")
            raise

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def log_verbose(self, message: str):
        """Log verbose message if verbose mode enabled."""
        if self.verbose:
            self.log(message, "DEBUG")

    async def load_test_data(self) -> dict[str, Any]:
        """Load test data from JSON file."""
        self.log("Loading test data...")
        with open(self.test_data_path) as f:
            data = json.load(f)
        self.log(
            f"Loaded {len(data.get('concepts', []))} concepts and {len(data.get('relationships', []))} relationships"
        )
        return data

    def record_result(
        self,
        scenario: str,
        test_name: str,
        passed: bool,
        duration: float,
        details: str | None = None,
        error: str | None = None,
    ):
        """Record test result."""
        result = {
            "scenario": scenario,
            "test_name": test_name,
            "passed": passed,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now().isoformat(),
            "details": details,
            "error": error,
        }
        self.results.append(result)

        status = "✅ PASS" if passed else "❌ FAIL"
        self.log(
            f"{status} {scenario} - {test_name} ({duration*1000:.0f}ms)",
            "INFO" if passed else "ERROR",
        )

        if error and not self.verbose:
            self.log(f"  Error: {error}", "ERROR")

    async def scenario_1_knowledge_base_creation(self, test_data: dict[str, Any]) -> bool:
        """Scenario 1: Knowledge Base Creation."""
        self.log("\n=== Scenario 1: Knowledge Base Creation ===")
        scenario_passed = True

        # Create foundational concepts
        test_concepts = [
            "Python Programming",
            "Object-Oriented Programming",
            "Functions",
            "Variables",
            "Data Structures",
        ]

        for concept_name in test_concepts:
            concept_data = next(
                (c for c in test_data["concepts"] if c["name"] == concept_name), None
            )
            if not concept_data:
                self.log(f"Concept '{concept_name}' not found in test data", "ERROR")
                scenario_passed = False
                continue

            start = time.time()
            try:
                result = await create_concept(
                    name=concept_data["name"],
                    explanation=concept_data["description"],
                    subtopic=concept_data.get("subtopic"),
                )
                duration = time.time() - start

                if result.get("success"):
                    self.created_concept_ids[concept_data["name"]] = result["data"]["concept_id"]
                    self.record_result(
                        "Scenario 1",
                        f"Create concept: {concept_name}",
                        True,
                        duration,
                        f"Created with ID: {result['data']['concept_id']}",
                    )
                else:
                    self.record_result(
                        "Scenario 1",
                        f"Create concept: {concept_name}",
                        False,
                        duration,
                        error=result.get("error"),
                    )
                    scenario_passed = False
            except Exception as e:
                duration = time.time() - start
                self.record_result(
                    "Scenario 1",
                    f"Create concept: {concept_name}",
                    False,
                    duration,
                    error=str(e),
                )
                scenario_passed = False

        # Build relationships
        relationship_tests = [
            ("Variables", "Functions", "prerequisite"),
            ("Functions", "Object-Oriented Programming", "prerequisite"),
        ]

        for from_name, to_name, rel_type in relationship_tests:
            start = time.time()
            try:
                from_id = self.created_concept_ids.get(from_name)
                to_id = self.created_concept_ids.get(to_name)

                if not from_id or not to_id:
                    self.log(
                        f"Missing concept IDs for relationship {from_name} -> {to_name}", "ERROR"
                    )
                    scenario_passed = False
                    continue

                result = await create_relationship(
                    source_id=from_id,
                    target_id=to_id,
                    relationship_type=rel_type,
                )
                duration = time.time() - start

                if result.get("success"):
                    self.record_result(
                        "Scenario 1",
                        f"Create relationship: {from_name} -> {to_name}",
                        True,
                        duration,
                    )
                else:
                    self.record_result(
                        "Scenario 1",
                        f"Create relationship: {from_name} -> {to_name}",
                        False,
                        duration,
                        error=result.get("error"),
                    )
                    scenario_passed = False
            except Exception as e:
                duration = time.time() - start
                self.record_result(
                    "Scenario 1",
                    f"Create relationship: {from_name} -> {to_name}",
                    False,
                    duration,
                    error=str(e),
                )
                scenario_passed = False

        # Validate structure - get hierarchy
        start = time.time()
        try:
            result = await list_hierarchy()
            duration = time.time() - start

            if result.get("success"):
                hierarchy = result.get("hierarchy", [])
                self.record_result(
                    "Scenario 1",
                    "Validate hierarchy",
                    True,
                    duration,
                    f"Found {len(hierarchy)} hierarchy entries",
                )
            else:
                self.record_result(
                    "Scenario 1",
                    "Validate hierarchy",
                    False,
                    duration,
                    error=result.get("error"),
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result(
                "Scenario 1",
                "Validate hierarchy",
                False,
                duration,
                error=str(e),
            )
            scenario_passed = False

        return scenario_passed

    async def scenario_2_crud_operations(self) -> bool:
        """Scenario 2: CRUD Operations."""
        self.log("\n=== Scenario 2: CRUD Operations ===")
        scenario_passed = True
        temp_concept_id = None

        # CREATE
        start = time.time()
        try:
            result = await create_concept(
                name="Machine Learning",
                explanation="AI subset enabling systems to learn from experience",
                subtopic="Data Science",
            )
            duration = time.time() - start

            if result.get("success"):
                temp_concept_id = result["data"]["concept_id"]
                self.created_concept_ids["Machine Learning"] = temp_concept_id
                self.record_result(
                    "Scenario 2", "CREATE concept", True, duration, f"ID: {temp_concept_id}"
                )
            else:
                self.record_result(
                    "Scenario 2", "CREATE concept", False, duration, error=result.get("error")
                )
                scenario_passed = False
                return scenario_passed
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 2", "CREATE concept", False, duration, error=str(e))
            scenario_passed = False
            return scenario_passed

        # READ
        start = time.time()
        try:
            result = await get_concept(concept_id=temp_concept_id)
            duration = time.time() - start

            if result.get("success"):
                concept = result.get("concept", {})
                self.record_result(
                    "Scenario 2",
                    "READ concept",
                    True,
                    duration,
                    f"Retrieved: {concept.get('name')}",
                )
            else:
                self.record_result(
                    "Scenario 2", "READ concept", False, duration, error=result.get("error")
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 2", "READ concept", False, duration, error=str(e))
            scenario_passed = False

        # UPDATE
        start = time.time()
        try:
            result = await update_concept(
                concept_id=temp_concept_id,
                explanation="Updated: Machine learning is a method of data analysis",
            )
            duration = time.time() - start

            if result.get("success"):
                self.record_result("Scenario 2", "UPDATE concept", True, duration)
            else:
                self.record_result(
                    "Scenario 2", "UPDATE concept", False, duration, error=result.get("error")
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 2", "UPDATE concept", False, duration, error=str(e))
            scenario_passed = False

        # DELETE
        start = time.time()
        try:
            result = await delete_concept(concept_id=temp_concept_id)
            duration = time.time() - start

            if result.get("success"):
                self.record_result("Scenario 2", "DELETE concept", True, duration)
                # Remove from tracking
                if "Machine Learning" in self.created_concept_ids:
                    del self.created_concept_ids["Machine Learning"]
            else:
                self.record_result(
                    "Scenario 2", "DELETE concept", False, duration, error=result.get("error")
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 2", "DELETE concept", False, duration, error=str(e))
            scenario_passed = False

        return scenario_passed

    async def scenario_3_search_operations(self) -> bool:
        """Scenario 3: Search Operations."""
        self.log("\n=== Scenario 3: Search Operations ===")
        scenario_passed = True

        # Semantic search tests
        search_queries = [
            ("programming concepts", "semantic search for programming"),
            ("data structures", "semantic search for data structures"),
        ]

        for query, test_name in search_queries:
            start = time.time()
            try:
                result = await search_concepts_semantic(query=query, limit=5)
                duration = time.time() - start

                if result.get("success"):
                    results_count = len(result.get("results", []))
                    self.record_result(
                        "Scenario 3",
                        test_name,
                        True,
                        duration,
                        f"Found {results_count} results",
                    )
                else:
                    self.record_result(
                        "Scenario 3", test_name, False, duration, error=result.get("error")
                    )
                    scenario_passed = False
            except Exception as e:
                duration = time.time() - start
                self.record_result("Scenario 3", test_name, False, duration, error=str(e))
                scenario_passed = False

        # Exact search test
        start = time.time()
        try:
            result = await search_concepts_exact(name="Python", limit=5)
            duration = time.time() - start

            if result.get("success"):
                results_count = len(result.get("results", []))
                self.record_result(
                    "Scenario 3",
                    "Exact search by name",
                    True,
                    duration,
                    f"Found {results_count} results",
                )
            else:
                self.record_result(
                    "Scenario 3", "Exact search by name", False, duration, error=result.get("error")
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 3", "Exact search by name", False, duration, error=str(e))
            scenario_passed = False

        # Recent concepts test
        start = time.time()
        try:
            result = await get_recent_concepts(limit=10)
            duration = time.time() - start

            if result.get("success"):
                results_count = len(result.get("results", []))
                self.record_result(
                    "Scenario 3",
                    "Get recent concepts",
                    True,
                    duration,
                    f"Found {results_count} recent concepts",
                )
            else:
                self.record_result(
                    "Scenario 3", "Get recent concepts", False, duration, error=result.get("error")
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result("Scenario 3", "Get recent concepts", False, duration, error=str(e))
            scenario_passed = False

        return scenario_passed

    async def scenario_4_batch_operations(self, test_data: dict[str, Any]) -> bool:
        """Scenario 4: Batch Operations (Performance Test)."""
        self.log("\n=== Scenario 4: Batch Operations ===")
        scenario_passed = True

        # Create multiple concepts quickly
        batch_size = 20
        concepts_to_create = test_data["concepts"][:batch_size]

        self.log(f"Creating {batch_size} concepts in batch...")
        batch_start = time.time()
        success_count = 0
        fail_count = 0

        for concept_data in concepts_to_create:
            # Skip if already created
            if concept_data["name"] in self.created_concept_ids:
                continue

            try:
                result = await create_concept(
                    name=concept_data["name"],
                    explanation=concept_data["description"],
                    subtopic=concept_data.get("subtopic"),
                )

                if result.get("success"):
                    self.created_concept_ids[concept_data["name"]] = result["data"]["concept_id"]
                    success_count += 1
                else:
                    fail_count += 1
                    self.log_verbose(
                        f"Failed to create {concept_data['name']}: {result.get('error')}"
                    )
            except Exception as e:
                fail_count += 1
                self.log_verbose(f"Exception creating {concept_data['name']}: {e!s}")

        batch_duration = time.time() - batch_start

        passed = fail_count == 0
        self.record_result(
            "Scenario 4",
            f"Batch create {batch_size} concepts",
            passed,
            batch_duration,
            f"Success: {success_count}, Failed: {fail_count}, Avg: {batch_duration/batch_size*1000:.0f}ms/concept",
        )
        scenario_passed = scenario_passed and passed

        # Batch search test
        self.log("Performing batch searches...")
        search_start = time.time()
        search_count = 10
        search_success = 0

        for i in range(search_count):
            try:
                result = await search_concepts_semantic(query="programming", limit=5)
                if result.get("success"):
                    search_success += 1
            except Exception as e:
                self.log_verbose(f"Search {i+1} failed: {e!s}")

        search_duration = time.time() - search_start
        passed = search_success == search_count
        self.record_result(
            "Scenario 4",
            f"Batch {search_count} searches",
            passed,
            search_duration,
            f"Success: {search_success}/{search_count}, Avg: {search_duration/search_count*1000:.0f}ms/search",
        )
        scenario_passed = scenario_passed and passed

        return scenario_passed

    async def scenario_5_error_handling(self) -> bool:
        """Scenario 5: Error Handling."""
        self.log("\n=== Scenario 5: Error Handling ===")
        scenario_passed = True

        # Test 1: Create with missing required field
        start = time.time()
        try:
            result = await create_concept(
                name="",  # Empty name should fail
                explanation="Test description",
            )
            duration = time.time() - start

            # Should fail with validation error
            if not result.get("success") and "error" in result:
                self.record_result(
                    "Scenario 5",
                    "Validation error handling",
                    True,
                    duration,
                    "Correctly rejected empty name",
                )
            else:
                self.record_result(
                    "Scenario 5",
                    "Validation error handling",
                    False,
                    duration,
                    error="Should have failed validation",
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            # Exception is acceptable for validation errors
            self.record_result(
                "Scenario 5",
                "Validation error handling",
                True,
                duration,
                f"Validation exception raised: {type(e).__name__}",
            )

        # Test 2: Get non-existent concept
        start = time.time()
        try:
            result = await get_concept(concept_id="non-existent-id-12345")
            duration = time.time() - start

            if not result.get("success") and "not_found" in result.get("error_type", ""):
                self.record_result(
                    "Scenario 5",
                    "Not found error handling",
                    True,
                    duration,
                    "Correctly returned not found error",
                )
            else:
                self.record_result(
                    "Scenario 5",
                    "Not found error handling",
                    False,
                    duration,
                    error=f"Unexpected result: {result}",
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result(
                "Scenario 5",
                "Not found error handling",
                False,
                duration,
                error=str(e),
            )
            scenario_passed = False

        # Test 3: Update non-existent concept
        start = time.time()
        try:
            result = await update_concept(
                concept_id="non-existent-id-67890",
                explanation="Updated description",
            )
            duration = time.time() - start

            if not result.get("success"):
                self.record_result(
                    "Scenario 5",
                    "Update non-existent concept",
                    True,
                    duration,
                    "Correctly failed to update non-existent concept",
                )
            else:
                self.record_result(
                    "Scenario 5",
                    "Update non-existent concept",
                    False,
                    duration,
                    error="Should have failed",
                )
                scenario_passed = False
        except Exception as e:
            duration = time.time() - start
            self.record_result(
                "Scenario 5",
                "Update non-existent concept",
                True,
                duration,
                f"Exception raised: {type(e).__name__}",
            )

        return scenario_passed

    def generate_summary(self) -> dict[str, Any]:
        """Generate test execution summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0

        scenarios = {}
        for result in self.results:
            scenario = result["scenario"]
            if scenario not in scenarios:
                scenarios[scenario] = {"total": 0, "passed": 0, "failed": 0}
            scenarios[scenario]["total"] += 1
            if result["passed"]:
                scenarios[scenario]["passed"] += 1
            else:
                scenarios[scenario]["failed"] += 1

        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": round(pass_rate, 2),
                "total_duration_seconds": round(total_duration, 2),
                "execution_time": datetime.now().isoformat(),
            },
            "scenarios": scenarios,
            "results": self.results,
        }

    async def run_all_scenarios(self) -> bool:
        """Run all UAT scenarios."""
        self.start_time = time.time()

        try:
            # Initialize services first
            await self.initialize_services()

            # Load test data
            test_data = await self.load_test_data()

            # Run scenarios
            scenario_results = []

            scenario_results.append(await self.scenario_1_knowledge_base_creation(test_data))
            scenario_results.append(await self.scenario_2_crud_operations())
            scenario_results.append(await self.scenario_3_search_operations())
            scenario_results.append(await self.scenario_4_batch_operations(test_data))
            scenario_results.append(await self.scenario_5_error_handling())

            self.end_time = time.time()

            # Generate summary
            summary = self.generate_summary()

            # Print summary
            self.log("\n" + "=" * 60)
            self.log("UAT TEST EXECUTION SUMMARY")
            self.log("=" * 60)
            self.log(f"Total Tests: {summary['summary']['total_tests']}")
            self.log(f"Passed: {summary['summary']['passed']} ✅")
            self.log(f"Failed: {summary['summary']['failed']} ❌")
            self.log(f"Pass Rate: {summary['summary']['pass_rate']}%")
            self.log(f"Duration: {summary['summary']['total_duration_seconds']}s")
            self.log("=" * 60)

            # Scenario breakdown
            self.log("\nScenario Breakdown:")
            for scenario, stats in summary["scenarios"].items():
                pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                status = "✅" if stats["failed"] == 0 else "⚠️"
                self.log(
                    f"  {status} {scenario}: {stats['passed']}/{stats['total']} ({pass_rate:.0f}%)"
                )

            # Save results
            results_file = Path(__file__).parent / "uat_results.json"
            with open(results_file, "w") as f:
                json.dump(summary, f, indent=2)
            self.log(f"\nResults saved to: {results_file}")

            # Return overall success
            all_passed = all(scenario_results)
            if all_passed:
                self.log("\n🎉 ALL UAT SCENARIOS PASSED! 🎉", "INFO")
            else:
                self.log("\n⚠️  Some UAT scenarios failed. Review results above.", "ERROR")

            return all_passed

        except Exception as e:
            self.log(f"Fatal error during UAT execution: {e!s}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
            return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run UAT tests for MCP Knowledge Server")
    parser.add_argument(
        "--test-data",
        default=str(Path(__file__).parent / "test_data.json"),
        help="Path to test data JSON file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    runner = UATRunner(test_data_path=args.test_data, verbose=args.verbose)
    success = await runner.run_all_scenarios()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
MCP Knowledge Server - Tool Verification Script

This script tests all 16 tools to verify they work correctly after the service
connection fixes.

Usage:
    python test_all_tools.py

Requirements:
    - Neo4j running (docker-compose up -d)
    - .env file configured
    - MCP server initialized
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

# Import the initialize function and tool modules
import mcp_server


# Get the actual function from FastMCP tool wrapper
def get_tool_function(tool_wrapper):
    """Extract the underlying function from FastMCP tool wrapper"""
    if hasattr(tool_wrapper, "fn"):
        return tool_wrapper.fn
    return tool_wrapper


class ToolTester:
    """Test harness for MCP tools"""

    def __init__(self):
        self.results: list[dict[str, Any]] = []
        self.test_concept_ids: list[str] = []

    async def run_all_tests(self):
        """Run all tool tests"""
        print("=" * 80)
        print("MCP Knowledge Server - Tool Verification")
        print("=" * 80)
        print(f"Started: {datetime.now().isoformat()}")
        print()

        # Initialize server
        print("Initializing server...")
        try:
            await mcp_server.initialize()
            print("✅ Server initialized successfully\n")
        except Exception as e:
            print(f"❌ Server initialization failed: {e}")
            print("\nPlease ensure:")
            print("  1. Neo4j is running (docker-compose up -d)")
            print("  2. .env file is configured")
            print("  3. All services are accessible")
            return False

        # Test each tool
        await self.test_ping()
        await self.test_get_server_stats()

        # Create test concepts
        await self.test_create_concept()

        # Test concept operations (only if we have test concepts)
        if self.test_concept_ids:
            await self.test_get_concept()
            await self.test_update_concept()
            await self.test_search_concepts_semantic()
            await self.test_search_concepts_exact()
            await self.test_get_recent_concepts()

            # Create second concept for relationship tests
            await self.test_create_second_concept()

            # Test relationship operations
            if len(self.test_concept_ids) >= 2:
                await self.test_create_relationship()
                await self.test_get_related_concepts()
                await self.test_get_prerequisites()
                await self.test_get_concept_chain()
                await self.test_delete_relationship()

            # Test analytics
            await self.test_list_hierarchy()
            await self.test_get_concepts_by_confidence()

            # Cleanup
            await self.test_delete_concept()

        # Print summary
        self.print_summary()

        return all(r["passed"] for r in self.results)

    async def test_ping(self):
        """Test ping tool"""
        print("Testing: ping")
        try:
            ping_fn = get_tool_function(mcp_server.ping)
            result = await ping_fn()
            passed = result.get("status") == "ok"
            self.results.append({"tool": "ping", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: {result}")
        except Exception as e:
            self.results.append({"tool": "ping", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_server_stats(self):
        """Test get_server_stats tool"""
        print("Testing: get_server_stats")
        try:
            get_server_stats_fn = get_tool_function(mcp_server.get_server_stats)
            result = await get_server_stats_fn()
            passed = result.get("success") is True
            self.results.append({"tool": "get_server_stats", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: {result}")
        except Exception as e:
            self.results.append({"tool": "get_server_stats", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_create_concept(self):
        """Test create_concept tool"""
        print("Testing: create_concept")
        try:
            create_concept_fn = get_tool_function(mcp_server.create_concept)
            result = await create_concept_fn(
                name="Test Concept",
                explanation="A test concept for verification created by test_all_tools.py",
                area="Testing",
                topic="Verification"
            )
            passed = result.get("success") is True
            if passed and "concept_id" in result.get("data", {}):
                self.test_concept_ids.append(result["data"]["concept_id"])
            self.results.append({
                "tool": "create_concept",
                "passed": passed,
                "result": result
            })
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Created concept {result.get('data', {}).get('concept_id', 'N/A')}")
        except Exception as e:
            self.results.append({"tool": "create_concept", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_create_second_concept(self):
        """Create second concept for relationship tests"""
        print("Testing: create_concept (second)")
        try:
            create_concept_fn = get_tool_function(mcp_server.create_concept)
            result = await create_concept_fn(
                name="Related Test Concept",
                explanation="A related test concept for relationship testing",
                area="Testing",
                topic="Verification"
            )
            if result.get("success") and "concept_id" in result.get("data", {}):
                self.test_concept_ids.append(result["data"]["concept_id"])
                print(f"  ✅ Created second concept: {result['data']['concept_id']}")
            else:
                print("  ❌ Failed to create second concept")
        except Exception as e:
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_concept(self):
        """Test get_concept tool"""
        print("Testing: get_concept")
        try:
            get_concept_fn = get_tool_function(mcp_server.get_concept)
            result = await get_concept_fn(concept_id=self.test_concept_ids[0], include_history=True)
            passed = result.get("success") is True
            self.results.append({"tool": "get_concept", "passed": passed, "result": result})
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Retrieved concept {self.test_concept_ids[0]}"
            )
        except Exception as e:
            self.results.append({"tool": "get_concept", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_update_concept(self):
        """Test update_concept tool"""
        print("Testing: update_concept")
        try:
            update_concept_fn = get_tool_function(mcp_server.update_concept)
            result = await update_concept_fn(
                concept_id=self.test_concept_ids[0],
                confidence_score=95.0,
                explanation="Updated by test script"
            )
            passed = result.get("success") is True
            self.results.append({
                "tool": "update_concept",
                "passed": passed,
                "result": result
            })
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Updated concept confidence to 95.0")
        except Exception as e:
            self.results.append({"tool": "update_concept", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_search_concepts_semantic(self):
        """Test search_concepts_semantic tool"""
        print("Testing: search_concepts_semantic")
        try:
            search_concepts_semantic_fn = get_tool_function(mcp_server.search_concepts_semantic)
            result = await search_concepts_semantic_fn(query="test concept verification", limit=10)
            passed = result.get("success") is True
            self.results.append(
                {"tool": "search_concepts_semantic", "passed": passed, "result": result}
            )
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Found {result.get('total', 0)} concepts"
            )
        except Exception as e:
            self.results.append(
                {"tool": "search_concepts_semantic", "passed": False, "error": str(e)}
            )
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_search_concepts_exact(self):
        """Test search_concepts_exact tool"""
        print("Testing: search_concepts_exact")
        try:
            search_concepts_exact_fn = get_tool_function(mcp_server.search_concepts_exact)
            result = await search_concepts_exact_fn(name="Test Concept")
            passed = result.get("success") is True
            self.results.append(
                {"tool": "search_concepts_exact", "passed": passed, "result": result}
            )
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Found {result.get('total', 0)} concepts"
            )
        except Exception as e:
            self.results.append({"tool": "search_concepts_exact", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_recent_concepts(self):
        """Test get_recent_concepts tool"""
        print("Testing: get_recent_concepts")
        try:
            get_recent_concepts_fn = get_tool_function(mcp_server.get_recent_concepts)
            result = await get_recent_concepts_fn(limit=10)
            passed = result.get("success") is True
            self.results.append({"tool": "get_recent_concepts", "passed": passed, "result": result})
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Retrieved {result.get('total', 0)} recent concepts"
            )
        except Exception as e:
            self.results.append({"tool": "get_recent_concepts", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_create_relationship(self):
        """Test create_relationship tool"""
        print("Testing: create_relationship")
        try:
            create_relationship_fn = get_tool_function(mcp_server.create_relationship)
            result = await create_relationship_fn(
                source_id=self.test_concept_ids[0],
                target_id=self.test_concept_ids[1],
                relationship_type="prerequisite",
                notes="Test relationship",
            )
            passed = result.get("success") is True
            self.results.append({"tool": "create_relationship", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Created relationship")
        except Exception as e:
            self.results.append({"tool": "create_relationship", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_related_concepts(self):
        """Test get_related_concepts tool"""
        print("Testing: get_related_concepts")
        try:
            get_related_concepts_fn = get_tool_function(mcp_server.get_related_concepts)
            result = await get_related_concepts_fn(concept_id=self.test_concept_ids[0])
            passed = result.get("success") is True
            self.results.append(
                {"tool": "get_related_concepts", "passed": passed, "result": result}
            )
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Found {result.get('total', 0)} related concepts"
            )
        except Exception as e:
            self.results.append({"tool": "get_related_concepts", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_prerequisites(self):
        """Test get_prerequisites tool"""
        print("Testing: get_prerequisites")
        try:
            get_prerequisites_fn = get_tool_function(mcp_server.get_prerequisites)
            result = await get_prerequisites_fn(concept_id=self.test_concept_ids[1])
            passed = result.get("success") is True
            self.results.append({"tool": "get_prerequisites", "passed": passed, "result": result})
            print(
                f"  {'✅ PASS' if passed else '❌ FAIL'}: Found {result.get('total', 0)} prerequisites"
            )
        except Exception as e:
            self.results.append({"tool": "get_prerequisites", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_concept_chain(self):
        """Test get_concept_chain tool"""
        print("Testing: get_concept_chain")
        try:
            get_concept_chain_fn = get_tool_function(mcp_server.get_concept_chain)
            result = await get_concept_chain_fn(
                start_id=self.test_concept_ids[0], end_id=self.test_concept_ids[1]
            )
            passed = result.get("success") is True
            self.results.append({"tool": "get_concept_chain", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Retrieved concept chain")
        except Exception as e:
            self.results.append({"tool": "get_concept_chain", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_list_hierarchy(self):
        """Test list_hierarchy tool"""
        print("Testing: list_hierarchy")
        try:
            list_hierarchy_fn = get_tool_function(mcp_server.list_hierarchy)
            result = await list_hierarchy_fn()
            passed = result.get("success") is True
            self.results.append({"tool": "list_hierarchy", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Retrieved hierarchy")
        except Exception as e:
            self.results.append({"tool": "list_hierarchy", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_get_concepts_by_confidence(self):
        """Test get_concepts_by_confidence tool"""
        print("Testing: get_concepts_by_confidence")
        try:
            get_concepts_by_confidence_fn = get_tool_function(mcp_server.get_concepts_by_confidence)
            result = await get_concepts_by_confidence_fn(
                min_confidence=80.0,
                max_confidence=100.0,
                limit=20
            )
            passed = result.get("success") is True
            self.results.append({
                "tool": "get_concepts_by_confidence",
                "passed": passed,
                "result": result
            })
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Found {result.get('total', 0)} concepts")
        except Exception as e:
            self.results.append({"tool": "get_concepts_by_confidence", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_delete_relationship(self):
        """Test delete_relationship tool"""
        print("Testing: delete_relationship")
        try:
            delete_relationship_fn = get_tool_function(mcp_server.delete_relationship)
            result = await delete_relationship_fn(
                source_id=self.test_concept_ids[0],
                target_id=self.test_concept_ids[1],
                relationship_type="prerequisite",
            )
            passed = result.get("success") is True
            self.results.append({"tool": "delete_relationship", "passed": passed, "result": result})
            print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Deleted relationship")
        except Exception as e:
            self.results.append({"tool": "delete_relationship", "passed": False, "error": str(e)})
            print(f"  ❌ EXCEPTION: {e}")
        print()

    async def test_delete_concept(self):
        """Test delete_concept tool"""
        print("Testing: delete_concept (cleanup)")
        for concept_id in self.test_concept_ids:
            try:
                delete_concept_fn = get_tool_function(mcp_server.delete_concept)
                result = await delete_concept_fn(concept_id=concept_id)
                passed = result.get("success") is True
                self.results.append({"tool": "delete_concept", "passed": passed, "result": result})
                print(f"  {'✅ PASS' if passed else '❌ FAIL'}: Deleted concept {concept_id}")
            except Exception as e:
                self.results.append({"tool": "delete_concept", "passed": False, "error": str(e)})
                print(f"  ❌ EXCEPTION: {e}")
        print()

    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 80)
        print("Test Summary")
        print("=" * 80)

        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

        print(f"Total Tests: {total_count}")
        print(f"Passed: {passed_count}")
        print(f"Failed: {total_count - passed_count}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print()

        if pass_rate == 100:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")
            print("\nFailed Tests:")
            for r in self.results:
                if not r["passed"]:
                    error = r.get("error", r.get("result", {}).get("error", "Unknown error"))
                    print(f"  - {r['tool']}: {error}")

        print()
        print(f"Completed: {datetime.now().isoformat()}")
        print("=" * 80)


async def main():
    """Main entry point"""
    tester = ToolTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Quick verification script to test null pointer concerns.
Tests if tools crash when services are None.
"""

import asyncio
import sys


# Test 1: Can we import tools when services are None?
print("=" * 60)
print("TEST 1: Import tools module")
print("=" * 60)

try:
    from tools import concept_tools

    print("✅ concept_tools imported successfully")
    print(f"   repository = {concept_tools.repository}")
    print(f"   confidence_service = {concept_tools.confidence_service}")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Try calling create_concept with None services
print("\n" + "=" * 60)
print("TEST 2: Call create_concept with None repository")
print("=" * 60)


async def test_create_concept_with_none():
    try:
        result = await concept_tools.create_concept(
            name="Test Concept", explanation="Testing null pointer"
        )
        print("✅ Function returned (didn't crash)")
        print(f"   Result: {result}")

        if not result.get("success"):
            error = result.get("error", "unknown")
            message = result.get("message", "")
            print(f"   ✓ Got error response: {error} - {message}")
            if "not initialized" in message.lower() or "unavailable" in message.lower():
                print("   ✓ Error message mentions initialization (good!)")
            else:
                print("   ⚠ Error message doesn't mention initialization")
        else:
            print("   ⚠ Function succeeded despite None repository (unexpected!)")

    except AttributeError as e:
        print(f"❌ CRASH with AttributeError: {e}")
        print("   This confirms NULL POINTER issue!")
        return False
    except Exception as e:
        print(f"❌ CRASH with {type(e).__name__}: {e}")
        return False

    return True


# Test 3: Check search tools
print("\n" + "=" * 60)
print("TEST 3: Call search_concepts_semantic with None services")
print("=" * 60)

from tools import search_tools


async def test_search_with_none():
    try:
        result = await search_tools.search_concepts_semantic(query="test query", limit=5)
        print("✅ Function returned (didn't crash)")
        print(f"   Result: {result}")
    except AttributeError as e:
        print(f"❌ CRASH with AttributeError: {e}")
        print("   This confirms NULL POINTER issue!")
        return False
    except Exception as e:
        print(f"❌ CRASH with {type(e).__name__}: {e}")
        return False

    return True


# Test 4: Check if FastMCP has protections
print("\n" + "=" * 60)
print("TEST 4: Check FastMCP initialization")
print("=" * 60)

try:
    from mcp_server import event_store, outbox, repository

    print("✅ mcp_server module imported")
    print(f"   repository at import time: {repository}")
    print(f"   event_store at import time: {event_store}")
    print(f"   outbox at import time: {outbox}")

    if repository is None:
        print("   ✓ Services are None at module import (expected)")
    else:
        print("   ⚠ Repository is NOT None at import (unexpected)")

except Exception as e:
    print(f"❌ Failed to import mcp_server: {e}")

# Run async tests
print("\n" + "=" * 60)
print("RUNNING ASYNC TESTS")
print("=" * 60)


async def main():
    test1_passed = await test_create_concept_with_none()
    test2_passed = await test_search_with_none()

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if not test1_passed:
        print("❌ create_concept CRASHES with None repository")
        print("   Issue C001-C002 CONFIRMED")
    else:
        print("✅ create_concept handles None repository gracefully")
        print("   Issue C001-C002 NOT CONFIRMED (or has protections)")

    if not test2_passed:
        print("❌ search_concepts_semantic CRASHES with None services")
        print("   Issue C006-C007 CONFIRMED")
    else:
        print("✅ search_concepts_semantic handles None services gracefully")
        print("   Issue C006-C007 NOT CONFIRMED (or has protections)")

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)

    if not test1_passed or not test2_passed:
        print("⚠️  NULL POINTER ISSUES ARE REAL!")
        print("   Code lacks defensive null checks")
        print("   Tools crash when services are None")
    else:
        print("✅ Tools handle None services gracefully")
        print("   Either:")
        print("   - Framework provides protections")
        print("   - Error handling catches AttributeError")
        print("   - Code has implicit safety mechanisms")
        print("\n   However, explicit null checks would still be better practice!")


asyncio.run(main())

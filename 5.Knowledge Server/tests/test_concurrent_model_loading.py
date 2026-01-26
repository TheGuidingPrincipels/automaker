"""
Test concurrent model loading to identify race conditions and resource issues.
"""

import asyncio

import pytest

from services.embedding_service import EmbeddingService


class TestConcurrentModelLoading:
    """Test concurrent model loading behavior."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_sequential_initialization(self):
        """Test sequential initialization (baseline)."""
        services = []

        for i in range(5):
            service = EmbeddingService()
            result = await service.initialize()
            assert result is True, f"Service {i} failed to initialize"
            services.append(service)

        # All should be available
        assert all(s.is_available() for s in services)

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_concurrent_initialization_with_delay(self):
        """Test concurrent initialization with small delays."""
        services = [EmbeddingService() for _ in range(3)]

        async def init_with_delay(svc, delay):
            await asyncio.sleep(delay)
            return await svc.initialize()

        # Stagger the initializations
        results = await asyncio.gather(*[init_with_delay(services[i], i * 0.1) for i in range(3)])

        print(f"Results: {results}")
        assert all(results), f"Some services failed: {results}"

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_identify_race_condition(self):
        """Identify the exact race condition."""
        import logging

        logging.basicConfig(level=logging.DEBUG)

        services = [EmbeddingService() for _ in range(2)]

        # Try concurrent init
        results = await asyncio.gather(*[s.initialize() for s in services], return_exceptions=True)

        print(f"Results: {results}")
        print(f"Service 0 available: {services[0].is_available()}")
        print(f"Service 1 available: {services[1].is_available()}")

        # At least document the behavior
        success_count = sum(1 for r in results if r is True)
        print(f"Success count: {success_count}/2")

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_resource_exhaustion_check(self):
        """Check if resource exhaustion occurs."""
        import os

        import psutil

        process = psutil.Process(os.getpid())

        initial_mem = process.memory_info().rss / 1024 / 1024  # MB

        # Try to create many services concurrently
        services = [EmbeddingService() for _ in range(10)]

        results = await asyncio.gather(*[s.initialize() for s in services], return_exceptions=True)

        final_mem = process.memory_info().rss / 1024 / 1024  # MB

        print(
            f"Memory: {initial_mem:.1f} MB -> {final_mem:.1f} MB (delta: {final_mem - initial_mem:.1f} MB)"
        )
        print(f"Success: {sum(1 for r in results if r is True)}/10")
        print(f"Failures: {sum(1 for r in results if r is not True)}/10")

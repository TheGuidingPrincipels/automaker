"""
Session stage handlers for Short-Term Memory MCP.

This module provides handlers for different session stages (RESEARCH, AIM, SHOOT, SKIN).
Currently implements SHOOT stage with research cache integration.
"""

import logging
from typing import Dict, List

from .database import Database
from .tools_impl import check_research_cache_impl, trigger_research_impl, update_research_cache_impl

logger = logging.getLogger(__name__)


async def shoot_stage_handler(concepts: List[str], db: Database) -> List[Dict]:
    """
    SHOOT stage: Research concepts (with caching)

    For each concept:
    1. Check research cache
    2. If cached: Use cached explanation (cache hit)
    3. If not cached: Trigger research, update cache (cache miss)
    4. Store results in session storage

    Args:
        concepts: List of concept names to research
        db: Database instance

    Returns:
        List of research results with cache status

    Example:
        >>> results = await shoot_stage_handler(["python asyncio", "react hooks"], db)
        >>> results[0]
        {
            "concept": "python asyncio",
            "explanation": "Async programming in Python...",
            "source_urls": [...],
            "status": "cache_hit",
            "cache_age_seconds": 120
        }
    """
    results = []
    cache_hits = 0
    cache_misses = 0

    for concept in concepts:
        # Check cache first
        cache_result = await check_research_cache_impl(concept, db)

        if cache_result["cached"]:
            # Cache hit - use cached explanation
            logger.info(f"Cache HIT: {concept} (age: {cache_result['cache_age_seconds']}s)")
            cache_hits += 1

            entry = cache_result["entry"]
            results.append(
                {
                    "concept": concept,
                    "explanation": entry["explanation"],
                    "source_urls": entry["source_urls"],
                    "status": "cache_hit",
                    "cache_age_seconds": cache_result["cache_age_seconds"],
                }
            )
        else:
            # Cache miss - trigger research
            logger.info(f"Cache MISS: {concept} - triggering research")
            cache_misses += 1

            # Trigger research (Context7 placeholder)
            research = await trigger_research_impl(concept, "", db)

            # Update cache with results
            await update_research_cache_impl(
                concept_name=concept,
                explanation=research["explanation"],
                source_urls=research["source_urls"],
                db=db,
            )

            results.append(
                {
                    "concept": concept,
                    "explanation": research["explanation"],
                    "source_urls": research["source_urls"],
                    "status": "cache_miss",
                }
            )

    # Log cache statistics
    total = len(concepts)
    hit_rate = (cache_hits / total * 100) if total > 0 else 0
    logger.info(
        f"Cache statistics: {cache_hits} hits, {cache_misses} misses ({hit_rate:.1f}% hit rate)"
    )

    return results

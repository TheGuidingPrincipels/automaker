"""
Projections package for event sourcing read models.

This package contains projection classes that transform events from the event store
into specialized read models (Neo4j graph, ChromaDB vectors, etc.).
"""

from projections.neo4j_projection import Neo4jProjection


__all__ = ["Neo4jProjection"]

"""
Confidence Scoring System

Provides data access, validation, and calculation services for automated
confidence scoring of knowledge concepts.

Modules:
- models: Pydantic data models for type safety
- data_access: Neo4j queries for confidence inputs
- validation: Input validation and bounds checking
- cache_manager: Two-tier Redis cache for confidence scores
- understanding_calculator: Understanding score calculation
- retention_calculator: Retention (temporal) score calculation
- composite_calculator: Weighted combination of understanding and retention
"""

__version__ = "0.1.0"

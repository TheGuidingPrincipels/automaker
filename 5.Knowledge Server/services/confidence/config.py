"""Cache configuration for Redis-based confidence scoring cache.

This module provides backward-compatible classes that proxy to the
centralized config system (config.get_settings()).

For new code, prefer using:
    from config import get_settings
    settings = get_settings()
    redis_host = settings.redis.host
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional


logger = logging.getLogger(__name__)


def _get_settings():
    """Lazy import to avoid circular dependencies."""
    from config import get_settings
    return get_settings()


@dataclass
class CacheConfig:
    """Redis cache configuration with security and performance settings.

    This class proxies to the centralized config system for backward compatibility.
    """

    # These will be populated from centralized config in __post_init__
    REDIS_HOST: str = field(default="localhost")
    REDIS_PORT: int = field(default=6379)
    REDIS_DB: int = field(default=0)
    REDIS_PASSWORD: str = field(default="")

    # TTL values (seconds)
    SCORE_CACHE_TTL: int = 3600  # 1 hour
    CALC_CACHE_TTL: int = 86400  # 24 hours

    # Key prefixes
    SCORE_KEY_PREFIX: str = "confidence:score:"
    CALC_RELATIONSHIP_PREFIX: str = "confidence:calc:relationships:"
    CALC_REVIEW_PREFIX: str = "confidence:calc:review:"

    # Performance settings
    MAX_CACHE_KEYS: int = 10000
    CONNECTION_POOL_SIZE: int = 10
    SOCKET_TIMEOUT: int = 5  # seconds

    # Security settings
    ENVIRONMENT: str = field(default="development")
    REDIS_SSL: bool = field(default=False)
    REDIS_SSL_CERT_REQS: str = field(default="required")

    def __post_init__(self):
        """Load values from centralized config and coerce types."""
        try:
            settings = _get_settings()

            # Redis connection settings from centralized config
            self.REDIS_HOST = settings.redis.host
            self.REDIS_PORT = settings.redis.port
            self.REDIS_DB = settings.redis.db
            self.REDIS_PASSWORD = settings.redis.password or ""
            self.REDIS_SSL = settings.redis.ssl
            self.REDIS_SSL_CERT_REQS = settings.redis.ssl_cert_reqs
            self.SOCKET_TIMEOUT = settings.redis.socket_timeout
            self.CONNECTION_POOL_SIZE = settings.redis.connection_pool_size

            # Environment from centralized config
            self.ENVIRONMENT = settings.environment

            # Confidence cache settings from centralized config
            self.SCORE_CACHE_TTL = settings.confidence.score_cache_ttl
            self.CALC_CACHE_TTL = settings.confidence.calc_cache_ttl
            self.SCORE_KEY_PREFIX = settings.confidence.score_key_prefix
            self.CALC_RELATIONSHIP_PREFIX = settings.confidence.calc_relationship_prefix
            self.CALC_REVIEW_PREFIX = settings.confidence.calc_review_prefix
            self.MAX_CACHE_KEYS = settings.confidence.max_cache_keys

        except Exception as e:
            logger.warning(f"Could not load centralized config, using defaults: {e}")

        # Ensure proper types for potentially string-based env values
        try:
            self.REDIS_PORT = int(self.REDIS_PORT)
        except (TypeError, ValueError):
            self.REDIS_PORT = 6379
        try:
            self.REDIS_DB = int(self.REDIS_DB)
        except (TypeError, ValueError):
            self.REDIS_DB = 0

        # Normalize boolean env inputs for SSL
        if isinstance(self.REDIS_SSL, str):
            self.REDIS_SSL = self.REDIS_SSL.lower() in {"1", "true", "yes"}

    def validate_security(self):
        """
        Validate security requirements based on environment.

        Raises:
            ValueError: If production requirements not met
        """
        if self.ENVIRONMENT == "production":
            if not self.REDIS_PASSWORD:
                raise ValueError(
                    "Redis authentication required in production. "
                    "Set REDIS_PASSWORD environment variable."
                )
            if not self.REDIS_SSL:
                logger.warning(
                    "Redis TLS/SSL not enabled in production. "
                    "Set REDIS_SSL=true for secure connections."
                )


@dataclass
class ConfidenceConfig:
    """Configuration values for confidence scoring components.

    This class proxies to the centralized config system for backward compatibility.
    """

    # Understanding score weights
    RELATIONSHIP_WEIGHT: float = 0.40
    EXPLANATION_WEIGHT: float = 0.30
    METADATA_WEIGHT: float = 0.30

    # Retention parameters
    DEFAULT_TAU_DAYS: int = field(default=7)
    MAX_TAU_DAYS: int = field(default=90)
    TAU_MULTIPLIER: float = field(default=1.5)

    # Composite weights
    UNDERSTANDING_WEIGHT: float = field(default=0.60)
    RETENTION_WEIGHT: float = field(default=0.40)

    # Relationship density parameters
    MAX_RELATIONSHIPS: int = field(default=20)

    # Pending recalculation retry settings
    MAX_RECALC_RETRIES: int = field(default=5)
    RECALC_RETRY_DELAY_SECONDS: int = field(default=2)
    RECALC_BATCH_SIZE: int = field(default=10)

    def __post_init__(self):
        """Load values from centralized config."""
        try:
            settings = _get_settings()
            conf = settings.confidence

            self.RELATIONSHIP_WEIGHT = conf.relationship_weight
            self.EXPLANATION_WEIGHT = conf.explanation_weight
            self.METADATA_WEIGHT = conf.metadata_weight
            self.DEFAULT_TAU_DAYS = conf.default_tau_days
            self.MAX_TAU_DAYS = conf.max_tau_days
            self.TAU_MULTIPLIER = conf.tau_multiplier
            self.UNDERSTANDING_WEIGHT = conf.understanding_weight
            self.RETENTION_WEIGHT = conf.retention_weight
            self.MAX_RELATIONSHIPS = conf.max_relationships

            # Pending recalculation retry settings
            self.MAX_RECALC_RETRIES = conf.max_recalc_retries
            self.RECALC_RETRY_DELAY_SECONDS = conf.recalc_retry_delay_seconds
            self.RECALC_BATCH_SIZE = conf.recalc_batch_size

        except Exception as e:
            logger.warning(f"Could not load centralized config, using defaults: {e}")

    def validate_weights(self) -> None:
        """Ensure weights remain within safe bounds."""
        if not 0.0 <= self.UNDERSTANDING_WEIGHT <= 1.0:
            raise ValueError("UNDERSTANDING_WEIGHT must be between 0.0 and 1.0")
        if not 0.0 <= self.RETENTION_WEIGHT <= 1.0:
            raise ValueError("RETENTION_WEIGHT must be between 0.0 and 1.0")

        total = (
            self.UNDERSTANDING_WEIGHT
            + self.RELATIONSHIP_WEIGHT
            + self.EXPLANATION_WEIGHT
            + self.METADATA_WEIGHT
        )
        if total <= 0:
            raise ValueError("Weight totals must be positive")

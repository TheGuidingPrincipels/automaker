"""Centralized configuration using Pydantic BaseSettings.

All environment variables are loaded here once. Services receive
config via constructor injection or import the singleton.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate project root once - used for absolute .env path
# This ensures .env is found regardless of the current working directory
_PROJECT_ROOT = Path(__file__).parent.parent
_ENV_FILE_PATH = str(_PROJECT_ROOT / ".env")


class Neo4jSettings(BaseSettings):
    """Neo4j database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_",
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: str = Field(default="")
    database: str = Field(default="neo4j")
    min_pool_size: int = Field(default=2, ge=1, le=100)
    max_pool_size: int = Field(default=10, ge=1, le=100)
    max_connection_lifetime: int = Field(default=3600, ge=60)
    connection_timeout: int = Field(default=30, ge=1)
    max_transaction_retry_time: int = Field(default=30, ge=1)


class ChromaDbSettings(BaseSettings):
    """ChromaDB vector store configuration."""

    model_config = SettingsConfigDict(
        env_prefix="CHROMA_",
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    persist_directory: str = Field(default="./data/chroma")
    collection_name: str = Field(default="concepts")
    distance_function: str = Field(default="cosine")
    hnsw_construction_ef: int = Field(default=128, ge=1, le=512)
    hnsw_search_ef: int = Field(default=64, ge=1, le=512)
    hnsw_m: int = Field(default=16, ge=2, le=64)

    @field_validator("distance_function")
    @classmethod
    def validate_distance(cls, v: str) -> str:
        allowed = ["cosine", "l2", "ip"]
        if v not in allowed:
            raise ValueError(f"Must be one of {allowed}")
        return v

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{1,61}[a-zA-Z0-9]$", v):
            raise ValueError(
                "Collection name must be 3-63 chars, start/end with alphanumeric, "
                "and contain only [a-zA-Z0-9._-]"
            )
        return v


class EmbeddingSettings(BaseSettings):
    """Embedding model configuration."""

    model_config = SettingsConfigDict(
        env_prefix="EMBEDDING_",
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    model: str = Field(default="all-MiniLM-L6-v2")
    backend: str = Field(default="sentence-transformers")  # "mistral" or "sentence-transformers"
    cache_dir: str = Field(default="./data/embeddings")
    device: str = Field(default="cpu")
    batch_size: int = Field(default=32, ge=1)
    normalize: bool = Field(default=True)
    max_text_length: int = Field(default=8000)  # Mistral supports up to 8192 tokens


class RedisSettings(BaseSettings):
    """Redis cache configuration for confidence scoring."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    ssl: bool = Field(default=False)
    ssl_cert_reqs: str = Field(default="required")
    socket_timeout: int = Field(default=5)
    connection_pool_size: int = Field(default=10)


class ConfidenceSettings(BaseSettings):
    """Confidence scoring weights and parameters."""

    model_config = SettingsConfigDict(
        env_prefix="CONFIDENCE_",
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Understanding score weights
    relationship_weight: float = Field(default=0.40, ge=0, le=1)
    explanation_weight: float = Field(default=0.30, ge=0, le=1)
    metadata_weight: float = Field(default=0.30, ge=0, le=1)

    # Composite weights
    understanding_weight: float = Field(default=0.60, ge=0, le=1)
    retention_weight: float = Field(default=0.40, ge=0, le=1)

    # Retention parameters
    default_tau_days: int = Field(default=7, ge=1)
    max_tau_days: int = Field(default=90, ge=1)
    tau_multiplier: float = Field(default=1.5, gt=0)

    # Relationship density parameters
    max_relationships: int = Field(
        default=20,
        ge=1,
        description="Maximum relationships for density score calculation. "
        "Concepts with this many or more relationships score 1.0 for density."
    )

    # Cache settings
    score_cache_ttl: int = Field(default=3600)  # 1 hour
    calc_cache_ttl: int = Field(default=86400)  # 24 hours

    # Key prefixes (not typically overridden via env)
    score_key_prefix: str = Field(default="confidence:score:")
    calc_relationship_prefix: str = Field(default="confidence:calc:relationships:")
    calc_review_prefix: str = Field(default="confidence:calc:review:")
    max_cache_keys: int = Field(default=10000)

    # Pending recalculation retry settings
    max_recalc_retries: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum retry attempts from the pending queue before escalating "
        "to dead letter. Total processing attempts = 1 (initial) + max_recalc_retries."
    )
    recalc_retry_delay_seconds: int = Field(
        default=2,
        ge=1,
        le=60,
        description="Base delay in seconds for retry backoff calculation"
    )
    recalc_batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum pending recalculations processed per cycle"
    )


class AppSettings(BaseSettings):
    """Main application configuration with nested settings."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    server_name: str = Field(default="knowledge-server", validation_alias="MCP_SERVER_NAME")
    environment: str = Field(default="development", validation_alias="ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Data paths
    event_store_path: str = Field(default="./data/events.db", validation_alias="EVENT_STORE_PATH")

    # Performance
    max_batch_size: int = Field(default=50, validation_alias="MAX_BATCH_SIZE")
    cache_ttl_seconds: int = Field(default=300, validation_alias="CACHE_TTL_SECONDS")

    # Nested settings - instantiated via default_factory
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    chromadb: ChromaDbSettings = Field(default_factory=ChromaDbSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    confidence: ConfidenceSettings = Field(default_factory=ConfidenceSettings)

    @model_validator(mode="after")
    def resolve_paths(self) -> "AppSettings":
        """Convert relative paths to absolute based on project root."""
        project_root = Path(__file__).parent.parent

        if not Path(self.event_store_path).is_absolute():
            object.__setattr__(self, "event_store_path", str(project_root / self.event_store_path))

        if not Path(self.chromadb.persist_directory).is_absolute():
            object.__setattr__(
                self.chromadb,
                "persist_directory",
                str(project_root / self.chromadb.persist_directory),
            )

        if not Path(self.embedding.cache_dir).is_absolute():
            object.__setattr__(
                self.embedding,
                "cache_dir",
                str(project_root / self.embedding.cache_dir),
            )

        return self

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate_production(self) -> None:
        """Validate settings for production. Raises ValueError if insecure."""
        if not self.is_production():
            return

        errors = []

        if not self.neo4j.password or self.neo4j.password == "password":
            errors.append("NEO4J_PASSWORD: Must be set to a secure value in production")

        if self.redis.password is None:
            errors.append("REDIS_PASSWORD: Redis authentication required in production")

        if not Path(self.chromadb.persist_directory).is_absolute():
            errors.append("CHROMA_PERSIST_DIRECTORY: Must be absolute path in production")

        if errors:
            raise ValueError("Production validation failed:\n- " + "\n- ".join(errors))


# Module-level singleton - instantiated once on first import
_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """Get the settings singleton. Creates on first call."""
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def reset_settings() -> None:
    """Reset settings singleton (for testing only)."""
    global _settings
    _settings = None

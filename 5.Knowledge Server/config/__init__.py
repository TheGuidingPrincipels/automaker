"""Configuration package - provides both new and legacy interfaces.

New code should use:
    from config import get_settings
    settings = get_settings()
    print(settings.neo4j.uri)

Legacy code continues to work:
    from config import Config
    print(Config.NEO4J_URI)
"""

from config.settings import (
    AppSettings,
    ChromaDbSettings,
    ConfidenceSettings,
    EmbeddingSettings,
    Neo4jSettings,
    RedisSettings,
    get_settings,
    reset_settings,
)

__all__ = [
    "AppSettings",
    "Neo4jSettings",
    "ChromaDbSettings",
    "EmbeddingSettings",
    "RedisSettings",
    "ConfidenceSettings",
    "get_settings",
    "reset_settings",
    "Config",  # Legacy shim
]


class _LegacyConfigShim:
    """Backward-compatible shim that proxies to new settings.

    Allows existing code using Config.NEO4J_URI to continue working
    while we migrate to the new pattern.

    DEPRECATED: Use get_settings() instead.
    """

    @property
    def MCP_SERVER_NAME(self) -> str:
        return get_settings().server_name

    @property
    def LOG_LEVEL(self) -> str:
        return get_settings().log_level

    @property
    def NEO4J_URI(self) -> str:
        return get_settings().neo4j.uri

    @property
    def NEO4J_USER(self) -> str:
        return get_settings().neo4j.user

    @property
    def NEO4J_PASSWORD(self) -> str:
        return get_settings().neo4j.password

    @property
    def CHROMA_PERSIST_DIRECTORY(self) -> str:
        return get_settings().chromadb.persist_directory

    @property
    def EMBEDDING_MODEL(self) -> str:
        return get_settings().embedding.model

    @property
    def EMBEDDING_BACKEND(self) -> str:
        return get_settings().embedding.backend

    @property
    def EMBEDDING_CACHE_DIR(self) -> str:
        return get_settings().embedding.cache_dir

    @property
    def EVENT_STORE_PATH(self) -> str:
        return get_settings().event_store_path

    @property
    def MAX_BATCH_SIZE(self) -> int:
        return get_settings().max_batch_size

    @property
    def CACHE_TTL_SECONDS(self) -> int:
        return get_settings().cache_ttl_seconds

    def validate(self) -> bool:
        """Validate configuration."""
        settings = get_settings()
        if not settings.neo4j.uri:
            raise ValueError("NEO4J_URI is required")
        if not settings.neo4j.user or not settings.neo4j.password:
            raise ValueError("Neo4j credentials are required")
        return True

    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        s = get_settings()
        return {
            "MCP_SERVER_NAME": s.server_name,
            "LOG_LEVEL": s.log_level,
            "NEO4J_URI": s.neo4j.uri,
            "NEO4J_USER": s.neo4j.user,
            "CHROMA_PERSIST_DIRECTORY": s.chromadb.persist_directory,
            "EMBEDDING_MODEL": s.embedding.model,
            "EMBEDDING_CACHE_DIR": s.embedding.cache_dir,
            "EVENT_STORE_PATH": s.event_store_path,
            "MAX_BATCH_SIZE": s.max_batch_size,
            "CACHE_TTL_SECONDS": s.cache_ttl_seconds,
        }


# Singleton instance for legacy compatibility
Config = _LegacyConfigShim()

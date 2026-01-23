# src/api/dependencies.py
"""FastAPI dependency injection."""

from functools import lru_cache
from typing import Annotated, Optional
import anyio

from fastapi import Depends, HTTPException, status

from ..config import Config, load_config
from ..session.manager import SessionManager
from ..session.storage import SessionStorage
from ..library.scanner import LibraryScanner
from ..vector.store import QdrantVectorStore
from ..vector.search import SemanticSearch
from ..query.engine import QueryEngine
from ..sdk.client import ClaudeCodeClient


# =============================================================================
# Configuration
# =============================================================================


@lru_cache()
def get_config_sync() -> Config:
    """Get configuration synchronously (cached).

    Note: uses async AnyIO filesystem operations under the hood.
    """
    return anyio.run(load_config)


_config: Optional[Config] = None
_config_lock: Optional[anyio.Lock] = None


def _get_config_lock() -> anyio.Lock:
    """Get or create the config lock (lazy initialization)."""
    global _config_lock
    if _config_lock is None:
        _config_lock = anyio.Lock()
    return _config_lock


async def get_config() -> Config:
    """Get configuration (async, cached)."""
    global _config

    if _config is None:
        async with _get_config_lock():
            if _config is None:
                _config = await load_config()

    return _config


ConfigDep = Annotated[Config, Depends(get_config)]


# =============================================================================
# Session Manager
# =============================================================================


_session_manager: Optional[SessionManager] = None
_session_manager_lock: Optional[anyio.Lock] = None


def _get_session_manager_lock() -> anyio.Lock:
    """Get or create the session manager lock (lazy initialization)."""
    global _session_manager_lock
    if _session_manager_lock is None:
        _session_manager_lock = anyio.Lock()
    return _session_manager_lock


async def get_session_manager(config: ConfigDep) -> SessionManager:
    """Get or create the session manager singleton."""
    global _session_manager

    if _session_manager is None:
        async with _get_session_manager_lock():
            if _session_manager is None:
                # Ensure sessions directory exists
                sessions_path = anyio.Path(config.sessions.path)
                await sessions_path.mkdir(parents=True, exist_ok=True)

                storage = SessionStorage(config.sessions.path)
                _session_manager = SessionManager(storage, config.library.path)

    return _session_manager


SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]


# =============================================================================
# Library Scanner
# =============================================================================


_library_scanner: Optional[LibraryScanner] = None
_library_scanner_lock: Optional[anyio.Lock] = None


def _get_library_scanner_lock() -> anyio.Lock:
    """Get or create the library scanner lock (lazy initialization)."""
    global _library_scanner_lock
    if _library_scanner_lock is None:
        _library_scanner_lock = anyio.Lock()
    return _library_scanner_lock


async def get_library_scanner(config: ConfigDep) -> LibraryScanner:
    """Get or create the library scanner singleton."""
    global _library_scanner

    if _library_scanner is None:
        async with _get_library_scanner_lock():
            if _library_scanner is None:
                _library_scanner = LibraryScanner(config.library.path)

    return _library_scanner


LibraryScannerDep = Annotated[LibraryScanner, Depends(get_library_scanner)]


# =============================================================================
# Semantic Search
# =============================================================================


_vector_store: Optional[QdrantVectorStore] = None
_vector_store_init_error: Optional[str] = None
_vector_store_lock: Optional[anyio.Lock] = None
_semantic_search: Optional[SemanticSearch] = None
_semantic_search_lock: Optional[anyio.Lock] = None


def _get_vector_store_lock() -> anyio.Lock:
    """Get or create the vector store lock (lazy initialization)."""
    global _vector_store_lock
    if _vector_store_lock is None:
        _vector_store_lock = anyio.Lock()
    return _vector_store_lock


def _get_semantic_search_lock() -> anyio.Lock:
    """Get or create the semantic search lock (lazy initialization)."""
    global _semantic_search_lock
    if _semantic_search_lock is None:
        _semantic_search_lock = anyio.Lock()
    return _semantic_search_lock


async def get_vector_store(config: ConfigDep) -> QdrantVectorStore:
    """Get or create the vector store singleton."""
    global _vector_store, _vector_store_init_error

    if _vector_store is None:
        async with _get_vector_store_lock():
            if _vector_store is None:
                if _vector_store_init_error:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Vector store unavailable: {_vector_store_init_error}",
                    )

                vector_store = QdrantVectorStore(
                    url=config.vector.url,
                    port=config.vector.port,
                    api_key=config.vector.api_key,
                    collection_name=config.vector.collection_name,
                )
                # Initialize connection
                try:
                    await vector_store.initialize()
                except Exception as e:
                    _vector_store_init_error = str(e)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Vector store unavailable: {e}",
                    ) from e

                _vector_store = vector_store

    return _vector_store


async def get_semantic_search(
    config: ConfigDep,
    vector_store: Annotated[QdrantVectorStore, Depends(get_vector_store)],
) -> SemanticSearch:
    """Get or create the semantic search singleton."""
    global _semantic_search

    if _semantic_search is None:
        async with _get_semantic_search_lock():
            if _semantic_search is None:
                _semantic_search = SemanticSearch(
                    vector_store=vector_store,
                    library_path=config.library.path,
                )

    return _semantic_search


VectorStoreDep = Annotated[QdrantVectorStore, Depends(get_vector_store)]
SemanticSearchDep = Annotated[SemanticSearch, Depends(get_semantic_search)]


# =============================================================================
# Query Engine
# =============================================================================


_query_engine: Optional[QueryEngine] = None
_query_engine_lock: Optional[anyio.Lock] = None
_sdk_client: Optional[ClaudeCodeClient] = None
_sdk_client_lock: Optional[anyio.Lock] = None


def _get_query_engine_lock() -> anyio.Lock:
    """Get or create the query engine lock (lazy initialization)."""
    global _query_engine_lock
    if _query_engine_lock is None:
        _query_engine_lock = anyio.Lock()
    return _query_engine_lock


def _get_sdk_client_lock() -> anyio.Lock:
    """Get or create the SDK client lock (lazy initialization)."""
    global _sdk_client_lock
    if _sdk_client_lock is None:
        _sdk_client_lock = anyio.Lock()
    return _sdk_client_lock


async def get_sdk_client() -> ClaudeCodeClient:
    """Get or create the SDK client singleton."""
    global _sdk_client

    if _sdk_client is None:
        async with _get_sdk_client_lock():
            if _sdk_client is None:
                _sdk_client = ClaudeCodeClient()

    return _sdk_client


async def get_query_engine(
    config: ConfigDep,
    search: SemanticSearchDep,
) -> QueryEngine:
    """Get or create the query engine singleton."""
    global _query_engine

    if _query_engine is None:
        async with _get_query_engine_lock():
            if _query_engine is None:
                sdk_client = await get_sdk_client()
                _query_engine = QueryEngine(
                    search=search,
                    sdk_client=sdk_client,
                    storage_dir=f"{config.sessions.path}/conversations",
                )

    return _query_engine


QueryEngineDep = Annotated[QueryEngine, Depends(get_query_engine)]
SdkClientDep = Annotated[ClaudeCodeClient, Depends(get_sdk_client)]


# =============================================================================
# Utility Dependencies
# =============================================================================


async def require_session(
    session_id: str,
    manager: SessionManagerDep,
):
    """Require that a session exists."""
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return session


# =============================================================================
# Cleanup on shutdown
# =============================================================================


async def cleanup_dependencies():
    """Cleanup singleton instances on shutdown."""
    global _config, _config_lock
    global _session_manager, _session_manager_lock
    global _library_scanner, _library_scanner_lock
    global _vector_store, _vector_store_init_error, _vector_store_lock
    global _semantic_search, _semantic_search_lock
    global _query_engine, _query_engine_lock
    global _sdk_client, _sdk_client_lock

    _config = None
    _config_lock = None

    _session_manager = None
    _session_manager_lock = None

    _library_scanner = None
    _library_scanner_lock = None

    if _vector_store:
        await _vector_store.close()
        _vector_store = None
    _vector_store_init_error = None
    _vector_store_lock = None

    _semantic_search = None
    _semantic_search_lock = None

    _query_engine = None
    _query_engine_lock = None

    _sdk_client = None
    _sdk_client_lock = None

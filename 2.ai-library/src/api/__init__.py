# src/api/__init__.py
"""REST API for Knowledge Library.

This module provides the FastAPI-based REST API for the Knowledge Library system.
It includes endpoints for:
- Session management (create, list, get, delete extraction sessions)
- Library operations (browse, search, index content)
- Query/search operations (semantic search, RAG-based Q&A)

Usage:
    from src.api import create_app

    app = create_app()
    # Run with: uvicorn src.api:app --reload

For dependency injection:
    from src.api import (
        ConfigDep,
        SessionManagerDep,
        LibraryScannerDep,
        SemanticSearchDep,
        QueryEngineDep,
    )
"""

from .main import create_app, app
from .dependencies import (
    # Config
    get_config,
    get_config_sync,
    ConfigDep,
    # Session Manager
    get_session_manager,
    SessionManagerDep,
    # Library Scanner
    get_library_scanner,
    LibraryScannerDep,
    # Vector Store and Semantic Search
    get_vector_store,
    get_semantic_search,
    VectorStoreDep,
    SemanticSearchDep,
    # Query Engine
    get_query_engine,
    get_sdk_client,
    QueryEngineDep,
    SdkClientDep,
    # Utilities
    require_session,
    cleanup_dependencies,
)
from .errors import APIError
from .schemas import (
    # Generic responses
    ErrorResponse,
    SuccessResponse,
    # Session schemas
    CreateSessionRequest,
    SessionResponse,
    SessionListResponse,
    # Block schemas
    BlockResponse,
    BlockListResponse,
    # Cleanup schemas
    CleanupItemResponse,
    CleanupPlanResponse,
    CleanupDecisionRequest,
    # Routing schemas
    RoutingPlanResponse,
    BlockRoutingItemResponse,
    SelectDestinationRequest,
    MergeDecisionRequest,
    SetContentModeRequest,
    # Execution schemas
    ExecuteResponse,
    WriteResultResponse,
    # Library schemas
    LibraryFileResponse,
    LibraryCategoryResponse,
    LibraryStructureResponse,
    LibrarySearchResponse,
    IndexResponse,
    # Query schemas
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    AskRequest,
    AskResponse,
    SourceInfo,
    # Conversation schemas
    ConversationResponse,
    ConversationListResponse,
    # Stream event schema
    StreamEvent,
)

# Group exports by source module for maintainability
_APP_EXPORTS = [
    "create_app",
    "app",
]

_DEPENDENCY_EXPORTS = [
    # Config
    "get_config",
    "get_config_sync",
    "ConfigDep",
    # Session Manager
    "get_session_manager",
    "SessionManagerDep",
    # Library Scanner
    "get_library_scanner",
    "LibraryScannerDep",
    # Vector Store and Semantic Search
    "get_vector_store",
    "get_semantic_search",
    "VectorStoreDep",
    "SemanticSearchDep",
    # Query Engine
    "get_query_engine",
    "get_sdk_client",
    "QueryEngineDep",
    "SdkClientDep",
    # Utilities
    "require_session",
    "cleanup_dependencies",
]

_ERROR_EXPORTS = [
    "APIError",
]

_SCHEMA_EXPORTS = [
    # Generic responses
    "ErrorResponse",
    "SuccessResponse",
    # Session schemas
    "CreateSessionRequest",
    "SessionResponse",
    "SessionListResponse",
    # Block schemas
    "BlockResponse",
    "BlockListResponse",
    # Cleanup schemas
    "CleanupItemResponse",
    "CleanupPlanResponse",
    "CleanupDecisionRequest",
    # Routing schemas
    "RoutingPlanResponse",
    "BlockRoutingItemResponse",
    "SelectDestinationRequest",
    "MergeDecisionRequest",
    "SetContentModeRequest",
    # Execution schemas
    "ExecuteResponse",
    "WriteResultResponse",
    # Library schemas
    "LibraryFileResponse",
    "LibraryCategoryResponse",
    "LibraryStructureResponse",
    "LibrarySearchResponse",
    "IndexResponse",
    # Query schemas
    "SearchRequest",
    "SearchResponse",
    "SearchResultResponse",
    "AskRequest",
    "AskResponse",
    "SourceInfo",
    # Conversation schemas
    "ConversationResponse",
    "ConversationListResponse",
    # Stream event schema
    "StreamEvent",
]

__all__ = [
    *_APP_EXPORTS,
    *_DEPENDENCY_EXPORTS,
    *_ERROR_EXPORTS,
    *_SCHEMA_EXPORTS,
]

"""Query module for RAG-based question answering.

Provides the QueryEngine and supporting components for natural language
queries against the knowledge library.
"""

from src.query.conversation import Conversation, ConversationManager, ConversationTurn
from src.query.engine import ConversationNotFoundError, QueryEngine, QueryResult
from src.query.formatter import ParsedResponse, ResponseFormatter
from src.query.retriever import RetrievedChunk, Retriever

__all__ = [
    # Engine
    "QueryEngine",
    "QueryResult",
    "ConversationNotFoundError",
    # Retriever
    "Retriever",
    "RetrievedChunk",
    # Formatter
    "ResponseFormatter",
    "ParsedResponse",
    # Conversation
    "ConversationManager",
    "Conversation",
    "ConversationTurn",
]

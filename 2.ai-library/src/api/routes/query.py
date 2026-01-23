# src/api/routes/query.py
"""Query and search routes."""

from fastapi import APIRouter

from ..dependencies import SemanticSearchDep, QueryEngineDep
from ..errors import APIError
from ..schemas import (
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
    AskRequest,
    AskResponse,
    SourceInfo,
    FindSimilarResponse,
    FindSimilarResultResponse,
    ConversationResponse,
    ConversationTurnResponse,
    ConversationListResponse,
    SuccessResponse,
)
from ...query.engine import ConversationNotFoundError


router = APIRouter()


# =============================================================================
# Semantic Search
# =============================================================================


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    search: SemanticSearchDep,
):
    """Perform semantic search on the library."""
    try:
        results = await search.search(
            query=request.query,
            n_results=request.n_results,
            min_similarity=request.min_similarity,
            filter_taxonomy=request.filter_taxonomy,
            filter_content_type=request.filter_content_type,
        )

        return SearchResponse(
            results=[
                SearchResultResponse(
                    content=r.content,
                    file_path=r.file_path,
                    section=r.section,
                    similarity=r.similarity,
                    chunk_id=r.chunk_id,
                    taxonomy_path=r.taxonomy_path,
                    content_type=r.content_type,
                )
                for r in results
            ],
            query=request.query,
            total=len(results),
        )
    except Exception as e:
        raise APIError.internal_error(f"Search failed: {str(e)}")


# =============================================================================
# Ask (RAG Query)
# =============================================================================


@router.post("/ask", response_model=AskResponse)
async def ask_library(
    request: AskRequest,
    query_engine: QueryEngineDep,
):
    """
    Ask a question to the library using RAG.

    Retrieves relevant content, synthesizes an answer using an LLM,
    and returns the answer with source citations.
    """
    try:
        result = await query_engine.query(
            question=request.question,
            conversation_id=request.conversation_id,
            top_k=request.max_sources,
        )

        return AskResponse(
            answer=result.answer,
            sources=[
                SourceInfo(
                    file_path=chunk.source_file,
                    section=chunk.section,
                    similarity=chunk.similarity,
                )
                for chunk in result.raw_chunks[: request.max_sources]
            ],
            confidence=result.confidence,
            conversation_id=result.conversation_id,
            related_topics=result.related_topics,
        )
    except ConversationNotFoundError as e:
        raise APIError.not_found("Conversation", str(e).replace("Conversation not found: ", ""))
    except Exception as e:
        raise APIError.internal_error(f"Ask failed: {str(e)}")


# =============================================================================
# Conversations
# =============================================================================


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    query_engine: QueryEngineDep,
    limit: int = 20,
    offset: int = 0,
):
    """List recent conversations."""
    try:
        conversations = await query_engine.list_conversations(limit, offset)

        return ConversationListResponse(
            conversations=[
                ConversationResponse(
                    id=c.id,
                    title=c.title,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                    turns=[
                        ConversationTurnResponse(
                            role=t.role,
                            content=t.content,
                            timestamp=t.timestamp,
                            sources=t.sources,
                        )
                        for t in c.turns
                    ],
                )
                for c in conversations
            ],
            total=len(conversations),
        )
    except Exception as e:
        raise APIError.internal_error(f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    query_engine: QueryEngineDep,
):
    """Get a specific conversation by ID."""
    conversation = await query_engine.get_conversation(conversation_id)

    if not conversation:
        raise APIError.not_found("Conversation", conversation_id)

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        turns=[
            ConversationTurnResponse(
                role=t.role,
                content=t.content,
                timestamp=t.timestamp,
                sources=t.sources,
            )
            for t in conversation.turns
        ],
    )


@router.delete("/conversations/{conversation_id}", response_model=SuccessResponse)
async def delete_conversation(
    conversation_id: str,
    query_engine: QueryEngineDep,
):
    """Delete a conversation."""
    deleted = await query_engine.delete_conversation(conversation_id)

    if not deleted:
        raise APIError.not_found("Conversation", conversation_id)

    return SuccessResponse(
        success=True,
        message=f"Conversation {conversation_id} deleted",
    )


# =============================================================================
# Find Similar
# =============================================================================


@router.post("/similar", response_model=FindSimilarResponse)
async def find_similar(
    content: str,
    search: SemanticSearchDep,
    threshold: float = 0.7,
    exclude_file: str = None,
):
    """Find content similar to the provided text."""
    try:
        results = await search.find_merge_candidates(
            content=content,
            threshold=threshold,
            exclude_file=exclude_file,
        )

        return FindSimilarResponse(
            results=[
                FindSimilarResultResponse(
                    content=r.content,
                    file_path=r.file_path,
                    section=r.section,
                    similarity=r.similarity,
                    chunk_id=r.chunk_id,
                )
                for r in results
            ],
            total=len(results),
        )
    except Exception as e:
        raise APIError.internal_error(f"Find similar failed: {str(e)}")

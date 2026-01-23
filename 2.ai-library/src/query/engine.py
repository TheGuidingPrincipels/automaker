"""Query Engine for RAG-based question answering.

Orchestrates retrieval, augmentation, generation, and formatting.
"""

from dataclasses import dataclass, field
from typing import Optional

from src.query.conversation import Conversation, ConversationManager
from src.query.formatter import ResponseFormatter
from src.query.retriever import RetrievedChunk, Retriever
from src.sdk.client import ClaudeCodeClient, SDKResponse
from src.sdk.prompts.output_mode import OUTPUT_SYSTEM_PROMPT, build_query_prompt
from src.vector.search import SearchResult, SemanticSearch


# Confidence calculation weights
SIMILARITY_WEIGHT = 0.70
DIVERSITY_WEIGHT = 0.20
COVERAGE_WEIGHT = 0.10


@dataclass
class QueryResult:
    """Result of a RAG query."""

    answer: str
    sources: list[str]
    confidence: float
    conversation_id: Optional[str] = None
    related_topics: list[str] = field(default_factory=list)
    raw_chunks: list[RetrievedChunk] = field(default_factory=list)


class ConversationNotFoundError(RuntimeError):
    """Raised when a conversation ID does not exist."""


class QueryEngine:
    """RAG query engine for answering questions from the knowledge library."""

    def __init__(
        self,
        search: SemanticSearch,
        sdk_client: ClaudeCodeClient,
        storage_dir: str = "./sessions/conversations",
    ):
        """Initialize the query engine.

        Args:
            search: SemanticSearch instance for vector queries
            sdk_client: ClaudeCodeClient for LLM queries
            storage_dir: Directory for conversation storage
        """
        self.retriever = Retriever(search)
        self.formatter = ResponseFormatter()
        self.conversations = ConversationManager(storage_dir)
        self.sdk_client = sdk_client
        self.search = search

    async def query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        top_k: int = 10,
    ) -> QueryResult:
        """Execute a RAG query.

        Args:
            question: The user's question
            conversation_id: Optional conversation ID for multi-turn
            top_k: Number of chunks to retrieve

        Returns:
            QueryResult with answer, sources, and metadata
        """
        # Get conversation context if continuing
        conversation: Optional[Conversation] = None
        conversation_history = ""

        if conversation_id:
            conversation = await self.conversations.get(conversation_id)
            if not conversation:
                raise ConversationNotFoundError(
                    f"Conversation not found: {conversation_id}"
                )
            conversation_history = self.conversations.format_context(conversation)

        # Retrieve relevant chunks
        chunks = await self.retriever.retrieve(question, top_k=top_k)

        # Handle no results case
        if not chunks:
            no_results_answer = self.formatter.format_no_results_response(question)
            return QueryResult(
                answer=no_results_answer,
                sources=[],
                confidence=0.0,
                conversation_id=conversation_id,
                related_topics=[],
                raw_chunks=[],
            )

        # Format context for LLM
        chunk_data = [
            (c.content, c.source_file, c.section) for c in chunks
        ]
        context = self.formatter.format_context_for_llm(chunk_data)

        # Build the prompt
        prompt = build_query_prompt(
            query=question,
            context=context,
            conversation_history=conversation_history,
        )

        # Generate answer using LLM
        sdk_response = await self.sdk_client.query_text(
            system_prompt=OUTPUT_SYSTEM_PROMPT,
            user_prompt=prompt,
        )

        # Parse response and extract citations
        if isinstance(sdk_response, SDKResponse):
            if not sdk_response.success or not sdk_response.raw_response:
                error = sdk_response.error or "SDK query failed"
                raise RuntimeError(error)
            response_text = sdk_response.raw_response
        else:
            response_text = sdk_response

        parsed = self.formatter.parse_response(response_text)

        # Calculate confidence
        confidence = self._calculate_confidence(chunks)

        # Extract related topics
        related_topics = self._find_related_topics(chunks)

        # Handle conversation persistence
        final_conversation_id = conversation_id
        if conversation_id:
            # Add turns to existing conversation
            # Locking prevents concurrent deletion, so only first check needed
            updated = await self.conversations.add_turn(
                conversation_id, "user", question
            )
            if not updated:
                raise ConversationNotFoundError(
                    f"Conversation not found: {conversation_id}"
                )

            await self.conversations.add_turn(
                conversation_id,
                "assistant",
                parsed.answer,
                sources=parsed.sources,
            )
        else:
            # Create new conversation
            new_conversation = await self.conversations.create()
            await self.conversations.add_turn(
                new_conversation.id, "user", question
            )
            await self.conversations.add_turn(
                new_conversation.id,
                "assistant",
                parsed.answer,
                sources=parsed.sources,
            )
            final_conversation_id = new_conversation.id

        return QueryResult(
            answer=parsed.answer,
            sources=parsed.sources,
            confidence=confidence,
            conversation_id=final_conversation_id,
            related_topics=related_topics,
            raw_chunks=chunks,
        )

    async def search_only(
        self,
        query: str,
        n_results: int = 10,
        min_similarity: float = 0.3,
    ) -> list[SearchResult]:
        """Perform semantic search without LLM generation.

        Args:
            query: The search query
            n_results: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of SearchResult objects
        """
        return await self.search.search(
            query=query,
            n_results=n_results,
            min_similarity=min_similarity,
        )

    def _calculate_confidence(self, chunks: list[RetrievedChunk]) -> float:
        """Calculate confidence score based on retrieved chunks.

        Uses weighted components to prevent easy saturation at 1.0:
        - 70%: Average similarity of top chunks
        - 20%: Source diversity factor (normalized)
        - 10%: Content coverage factor (normalized)

        Args:
            chunks: List of retrieved chunks

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not chunks:
            return 0.0

        # 70%: Average similarity of top 5 chunks
        top_chunks = chunks[:5]
        avg_similarity = sum(c.similarity for c in top_chunks) / len(top_chunks)
        similarity_component = avg_similarity * SIMILARITY_WEIGHT

        # 20%: Source diversity factor (normalized: 1 source = 0, 5+ sources = 1)
        unique_sources = len(set(c.source_file for c in chunks))
        diversity_factor = min((unique_sources - 1) / 4.0, 1.0) if unique_sources > 0 else 0.0
        diversity_component = diversity_factor * DIVERSITY_WEIGHT

        # 10%: Content coverage factor (normalized: 0 chars = 0, 5000+ chars = 1)
        total_content = sum(len(c.content) for c in top_chunks)
        coverage_factor = min(total_content / 5000.0, 1.0)
        coverage_component = coverage_factor * COVERAGE_WEIGHT

        confidence = similarity_component + diversity_component + coverage_component
        return min(confidence, 1.0)

    def _find_related_topics(
        self, chunks: list[RetrievedChunk], max_topics: int = 5
    ) -> list[str]:
        """Extract related topics from chunk metadata.

        Args:
            chunks: List of retrieved chunks
            max_topics: Maximum number of topics to return

        Returns:
            List of related topic names
        """
        topics: set[str] = set()

        for chunk in chunks:
            # Extract section headings as topics
            if chunk.section:
                topics.add(chunk.section)

            # Extract category from file path
            if "/" in chunk.source_file:
                category = chunk.source_file.split("/")[0]
                if category and category != ".":
                    topics.add(category)

            # Check metadata for tags/categories
            if "category" in chunk.metadata:
                topics.add(chunk.metadata["category"])
            if "tags" in chunk.metadata:
                for tag in chunk.metadata["tags"]:
                    topics.add(tag)

        # Remove generic entries
        topics.discard("library")
        topics.discard("content")

        return list(topics)[:max_topics]

    async def get_conversation(
        self, conversation_id: str
    ) -> Optional[Conversation]:
        """Get a conversation by ID.

        Args:
            conversation_id: The conversation ID

        Returns:
            The Conversation if found, None otherwise
        """
        return await self.conversations.get(conversation_id)

    async def list_conversations(
        self, limit: int = 20, offset: int = 0
    ) -> list[Conversation]:
        """List recent conversations.

        Args:
            limit: Maximum number to return
            offset: Number to skip

        Returns:
            List of recent conversations
        """
        return await self.conversations.list_conversations(limit, offset)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: The conversation ID

        Returns:
            True if deleted, False if not found
        """
        return await self.conversations.delete(conversation_id)

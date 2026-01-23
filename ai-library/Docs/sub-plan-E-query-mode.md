# Sub-Plan E: Query Mode (Phase 6)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`knowledge-library`)
> **Dependencies**: Sub-Plan C (Vector/RAG), Sub-Plan D (REST API)
> **Next Phase**: Sub-Plan F (Web UI + Migration)

---

## Goal

Implement natural language queries against the knowledge library with RAG (Retrieval-Augmented Generation). This phase adds the "Output Mode" - the ability to ask questions and get answers with citations from your personal knowledge library.

---

## Prerequisites from Previous Phases

Before starting this phase, ensure:

**From Sub-Plan C:**

- Vector store functional (ChromaDB)
- Semantic search working
- Library indexer operational

**From Sub-Plan D:**

- REST API running
- Query endpoints scaffolded (`/api/query/search`, `/api/query/ask`)

---

## New Capabilities

| Capability               | Description                                      |
| ------------------------ | ------------------------------------------------ |
| **RAG Query Engine**     | Answer questions using retrieved library content |
| **Citation Extraction**  | Include source citations in responses            |
| **Conversation History** | Support multi-turn conversations                 |
| **Confidence Scoring**   | Indicate confidence based on source quality      |
| **Source Linking**       | Link answers back to specific library locations  |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT MODE FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User asks: "What do I know about JWT authentication?"                       │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. RETRIEVE                                                         │    │
│  │     └─ Vector search → Find relevant chunks from library             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  2. AUGMENT                                                          │    │
│  │     └─ Build context from retrieved chunks + conversation history    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  3. GENERATE                                                         │    │
│  │     └─ SDK query with OUTPUT_MODE system prompt                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  4. FORMAT                                                           │    │
│  │     └─ Extract citations, calculate confidence, format response      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                         │                                                    │
│                         ▼                                                    │
│  Response with answer + source citations + confidence                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## New Components

### Project Structure Additions

```
src/
├── query/
│   ├── __init__.py
│   ├── engine.py                 # Query processing engine
│   ├── retriever.py              # RAG retrieval logic
│   ├── formatter.py              # Format responses with citations
│   └── conversation.py           # Conversation history management
│
├── sdk/
│   └── prompts/
│       └── output_mode.py        # System prompt for query mode
```

---

## Implementation Details

### 1. Output Mode System Prompt (`src/sdk/prompts/output_mode.py`)

```python
# src/sdk/prompts/output_mode.py

OUTPUT_SYSTEM_PROMPT = """
You are a Knowledge Librarian in OUTPUT mode.
Your job is to answer questions using the user's personal knowledge library.

## Your Capabilities
- Access to the user's personal knowledge library (markdown files)
- Semantic search results showing relevant content
- Ability to synthesize information from multiple sources

## Response Guidelines

1. ONLY use information from the provided library content
2. ALWAYS cite sources using this format: [source: path/to/file.md]
3. If information is not in the library, clearly state: "This information is not in your library."
4. If information is partial, say what you found and what's missing
5. Suggest related topics the user might want to explore

## Citation Rules

- Every fact or piece of information must have a citation
- Use the exact file path provided in the context
- Multiple sources can be cited for the same fact: [source: file1.md][source: file2.md]
- When quoting directly, use quotation marks and cite

## Response Format

When answering:
- Be concise but complete
- Use bullet points for clarity when appropriate
- Include relevant quotes from the library when helpful
- End with a "Sources" section listing all cited files

## Handling Missing Information

If the library doesn't contain the requested information:
- Say "This information is not in your library."
- If there's related content, mention it
- Suggest what the user might want to add to their library

## Example Response

Based on your library, here's what I found about JWT authentication:

Your notes indicate that tokens should be validated on every request [source: library/tech/auth.md], including:
- Expiry check (exp claim)
- Signature verification
- Issuer validation (iss claim)

Your library also mentions that "refresh tokens should have a longer expiry than access tokens" [source: library/tech/auth.md].

However, I didn't find information about refresh token rotation strategies in your library. You might want to add notes on this topic.

**Sources:**
- library/tech/auth.md (Token Validation section)
"""

QUERY_PROMPT_TEMPLATE = """
## User Question
{question}

## Relevant Content from Your Knowledge Library

{context}

## Previous Conversation
{conversation_history}

## Instructions
Answer the question based ONLY on the library content above.
Include citations in the format [source: path/to/file.md].
If the information is not in the library, say so clearly.
"""
```

### 2. Query Engine (`src/query/engine.py`)

```python
# src/query/engine.py

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re

from ..vector.search import SemanticSearch
from ..sdk.client import SDKClient
from ..sdk.prompts.output_mode import OUTPUT_SYSTEM_PROMPT, QUERY_PROMPT_TEMPLATE
from .retriever import Retriever
from .formatter import ResponseFormatter
from .conversation import ConversationManager


@dataclass
class QueryResult:
    """Result of a query against the knowledge library."""
    answer: str
    sources: List[Dict[str, str]]
    confidence: float
    conversation_id: str
    related_topics: List[str]
    raw_chunks: List[Dict[str, Any]]


class QueryEngine:
    """
    Process natural language queries against the library using RAG.
    """

    def __init__(
        self,
        library_path: str,
        semantic_search: Optional[SemanticSearch] = None,
        sdk_client: Optional[SDKClient] = None,
    ):
        self.library_path = library_path
        self.search = semantic_search or SemanticSearch(library_path)
        self.sdk = sdk_client or SDKClient()
        self.retriever = Retriever(self.search)
        self.formatter = ResponseFormatter()
        self.conversations = ConversationManager()

    async def query(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        n_chunks: int = 10,
        min_similarity: float = 0.5,
    ) -> QueryResult:
        """
        Answer a question using the knowledge library.

        Args:
            question: The user's question
            conversation_id: Optional ID to continue a conversation
            n_chunks: Number of chunks to retrieve
            min_similarity: Minimum similarity threshold

        Returns:
            QueryResult with answer, sources, and metadata
        """
        # Ensure library is indexed
        await self.search.ensure_indexed()

        # Get or create conversation
        if conversation_id:
            conversation = await self.conversations.get(conversation_id)
        else:
            conversation = await self.conversations.create()

        # Retrieve relevant chunks
        chunks = await self.retriever.retrieve(
            question,
            n_results=n_chunks,
            min_similarity=min_similarity,
        )

        # Build context from chunks
        context = self._build_context(chunks)

        # Get conversation history
        history = self._format_conversation_history(conversation)

        # Build prompt
        prompt = QUERY_PROMPT_TEMPLATE.format(
            question=question,
            context=context,
            conversation_history=history,
        )

        # Query SDK
        response = await self.sdk.query(
            system_prompt=OUTPUT_SYSTEM_PROMPT,
            prompt=prompt,
        )

        # Parse response and extract citations
        answer, sources = self.formatter.parse_response(response, chunks)

        # Calculate confidence
        confidence = self._calculate_confidence(chunks, sources)

        # Find related topics
        related = self._find_related_topics(chunks)

        # Update conversation
        await self.conversations.add_turn(
            conversation.id,
            question=question,
            answer=answer,
            sources=sources,
        )

        return QueryResult(
            answer=answer,
            sources=sources,
            confidence=confidence,
            conversation_id=conversation.id,
            related_topics=related,
            raw_chunks=chunks,
        )

    async def search_only(
        self,
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search without RAG generation.
        Useful for exploring the library.
        """
        await self.search.ensure_indexed()

        results = await self.search.search(
            query=query,
            n_results=n_results,
            min_similarity=min_similarity,
        )

        return [
            {
                "content": r.content,
                "file_path": r.file_path,
                "section": r.section,
                "similarity": r.similarity,
            }
            for r in results
        ]

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from retrieved chunks."""
        if not chunks:
            return "(No relevant content found in your library)"

        context_parts = []
        for chunk in chunks:
            file_path = chunk.get("file_path", "unknown")
            section = chunk.get("section", "")
            content = chunk.get("content", "")
            similarity = chunk.get("similarity", 0)

            header = f"[From {file_path}"
            if section:
                header += f" > {section}"
            header += f"] (relevance: {similarity:.0%})"

            context_parts.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(context_parts)

    def _format_conversation_history(self, conversation) -> str:
        """Format conversation history for the prompt."""
        if not conversation or not conversation.turns:
            return "(No previous conversation)"

        # Get last 5 turns
        recent_turns = conversation.turns[-5:]

        parts = []
        for turn in recent_turns:
            parts.append(f"User: {turn.question}")
            parts.append(f"Assistant: {turn.answer[:500]}...")

        return "\n".join(parts)

    def _calculate_confidence(
        self,
        chunks: List[Dict[str, Any]],
        sources: List[Dict[str, str]],
    ) -> float:
        """
        Calculate confidence score based on retrieved content quality.

        Factors:
        - Average similarity of used chunks
        - Number of sources cited
        - Coverage of the question
        """
        if not chunks:
            return 0.0

        # Average similarity of top chunks
        similarities = [c.get("similarity", 0) for c in chunks[:5]]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0

        # Source coverage bonus
        source_bonus = min(len(sources) * 0.1, 0.3)  # Max 30% bonus

        confidence = min(avg_similarity + source_bonus, 1.0)
        return round(confidence, 2)

    def _find_related_topics(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Find related topics from retrieved chunks."""
        topics = set()

        for chunk in chunks:
            section = chunk.get("section", "")
            if section:
                topics.add(section)

            # Extract potential topics from file path
            file_path = chunk.get("file_path", "")
            parts = file_path.replace(".md", "").split("/")
            for part in parts:
                if part and part != "library":
                    topics.add(part.replace("-", " ").replace("_", " ").title())

        return list(topics)[:5]  # Return top 5
```

### 3. Retriever (`src/query/retriever.py`)

```python
# src/query/retriever.py

from typing import List, Dict, Any, Optional
from ..vector.search import SemanticSearch


class Retriever:
    """
    Handles retrieval of relevant content for RAG queries.
    Includes re-ranking and deduplication logic.
    """

    def __init__(self, semantic_search: SemanticSearch):
        self.search = semantic_search

    async def retrieve(
        self,
        query: str,
        n_results: int = 10,
        min_similarity: float = 0.5,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query
            n_results: Number of results to return
            min_similarity: Minimum similarity threshold
            rerank: Whether to apply re-ranking

        Returns:
            List of relevant chunks with metadata
        """
        # Get more results than needed for re-ranking
        raw_results = await self.search.search(
            query=query,
            n_results=n_results * 2,
            min_similarity=min_similarity,
        )

        # Convert to dict format
        chunks = [
            {
                "content": r.content,
                "file_path": r.file_path,
                "section": r.section,
                "similarity": r.similarity,
                "chunk_id": r.chunk_id,
            }
            for r in raw_results
        ]

        # Deduplicate
        chunks = self._deduplicate(chunks)

        # Re-rank if enabled
        if rerank:
            chunks = self._rerank(chunks, query)

        return chunks[:n_results]

    def _deduplicate(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate or highly overlapping chunks.
        """
        seen_content = set()
        unique_chunks = []

        for chunk in chunks:
            # Create a content fingerprint
            content = chunk["content"]
            fingerprint = content[:100].strip().lower()

            if fingerprint not in seen_content:
                seen_content.add(fingerprint)
                unique_chunks.append(chunk)

        return unique_chunks

    def _rerank(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Re-rank chunks based on additional signals.

        Signals considered:
        - Original similarity score (primary)
        - Section relevance
        - Content length (prefer substantial chunks)
        """
        query_words = set(query.lower().split())

        for chunk in chunks:
            base_score = chunk["similarity"]

            # Bonus for section match
            section = chunk.get("section", "").lower()
            section_words = set(section.split())
            section_overlap = len(query_words & section_words)
            section_bonus = section_overlap * 0.05

            # Bonus for substantial content
            content_length = len(chunk["content"])
            length_bonus = min(content_length / 1000, 0.1)  # Max 10% bonus

            # Calculate final score
            chunk["rerank_score"] = base_score + section_bonus + length_bonus

        # Sort by rerank score
        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return chunks

    async def retrieve_for_file(
        self,
        file_path: str,
        n_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks from a specific file.
        Useful for showing full context of a source.
        """
        from ..vector.store import VectorStore

        store = VectorStore()

        # Search with file filter
        results = await store.search(
            query="",  # Empty query to get all
            n_results=n_results,
            filter_file=file_path,
        )

        return [
            {
                "content": r["content"],
                "file_path": r["metadata"]["file_path"],
                "section": r["metadata"].get("section", ""),
                "chunk_index": r["metadata"].get("chunk_index", 0),
            }
            for r in results
        ]
```

### 4. Response Formatter (`src/query/formatter.py`)

```python
# src/query/formatter.py

from typing import List, Dict, Any, Tuple
import re


class ResponseFormatter:
    """
    Format and parse query responses, including citation extraction.
    """

    CITATION_PATTERN = r'\[source:\s*([^\]]+)\]'

    def parse_response(
        self,
        response: str,
        available_chunks: List[Dict[str, Any]],
    ) -> Tuple[str, List[Dict[str, str]]]:
        """
        Parse the model response and extract citations.

        Args:
            response: Raw model response
            available_chunks: Chunks that were provided as context

        Returns:
            Tuple of (cleaned_answer, sources_list)
        """
        # Extract citations
        citations = re.findall(self.CITATION_PATTERN, response)

        # Build sources list with details
        sources = []
        seen_files = set()

        for citation in citations:
            citation = citation.strip()
            if citation in seen_files:
                continue

            seen_files.add(citation)

            # Find matching chunk for excerpt
            excerpt = ""
            section = ""
            for chunk in available_chunks:
                if chunk.get("file_path") == citation:
                    excerpt = chunk.get("content", "")[:200] + "..."
                    section = chunk.get("section", "")
                    break

            sources.append({
                "file": citation,
                "section": section,
                "excerpt": excerpt,
            })

        # Clean up response (optionally remove inline citations for cleaner display)
        # For now, keep them as they provide context
        cleaned_answer = response

        return cleaned_answer, sources

    def format_sources_section(self, sources: List[Dict[str, str]]) -> str:
        """
        Format sources as a markdown section.
        """
        if not sources:
            return ""

        lines = ["\n**Sources:**"]
        for source in sources:
            line = f"- {source['file']}"
            if source.get("section"):
                line += f" ({source['section']})"
            lines.append(line)

        return "\n".join(lines)

    def format_no_results_response(self, question: str) -> str:
        """
        Format response when no relevant content is found.
        """
        return (
            f"This information is not in your library.\n\n"
            f"Your question about \"{question}\" doesn't match any content "
            f"in your knowledge library. You might want to:\n"
            f"- Add notes on this topic\n"
            f"- Rephrase your question\n"
            f"- Check if the library is properly indexed"
        )

    def format_partial_results_response(
        self,
        answer: str,
        missing_aspects: List[str],
    ) -> str:
        """
        Format response when only partial information is available.
        """
        if not missing_aspects:
            return answer

        missing_note = (
            "\n\n**Note:** Your library doesn't contain information about: "
            + ", ".join(missing_aspects)
        )

        return answer + missing_note
```

### 5. Conversation Manager (`src/query/conversation.py`)

```python
# src/query/conversation.py

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import json
from pathlib import Path


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    question: str
    answer: str
    sources: List[Dict[str, str]]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Conversation:
    """A conversation with the knowledge library."""
    id: str
    created_at: datetime
    turns: List[ConversationTurn] = field(default_factory=list)


class ConversationManager:
    """
    Manage conversation history for multi-turn queries.
    """

    def __init__(self, storage_path: str = "./sessions/conversations"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Conversation] = {}

    async def create(self) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            id=str(uuid.uuid4())[:8],
            created_at=datetime.now(),
            turns=[],
        )
        self._cache[conversation.id] = conversation
        await self._save(conversation)
        return conversation

    async def get(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        # Check cache first
        if conversation_id in self._cache:
            return self._cache[conversation_id]

        # Load from storage
        conversation = await self._load(conversation_id)
        if conversation:
            self._cache[conversation_id] = conversation

        return conversation

    async def add_turn(
        self,
        conversation_id: str,
        question: str,
        answer: str,
        sources: List[Dict[str, str]],
    ) -> Conversation:
        """Add a turn to a conversation."""
        conversation = await self.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        turn = ConversationTurn(
            question=question,
            answer=answer,
            sources=sources,
        )
        conversation.turns.append(turn)

        await self._save(conversation)
        return conversation

    async def list_conversations(
        self,
        limit: int = 20,
    ) -> List[Conversation]:
        """List recent conversations."""
        conversations = []

        for file_path in sorted(
            self.storage_path.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            conversation = await self._load(file_path.stem)
            if conversation:
                conversations.append(conversation)

        return conversations

    async def delete(self, conversation_id: str) -> bool:
        """Delete a conversation."""
        file_path = self.storage_path / f"{conversation_id}.json"
        if file_path.exists():
            file_path.unlink()
            self._cache.pop(conversation_id, None)
            return True
        return False

    async def _save(self, conversation: Conversation) -> None:
        """Save conversation to storage."""
        file_path = self.storage_path / f"{conversation.id}.json"

        data = {
            "id": conversation.id,
            "created_at": conversation.created_at.isoformat(),
            "turns": [
                {
                    "question": turn.question,
                    "answer": turn.answer,
                    "sources": turn.sources,
                    "timestamp": turn.timestamp.isoformat(),
                }
                for turn in conversation.turns
            ],
        }

        file_path.write_text(json.dumps(data, indent=2))

    async def _load(self, conversation_id: str) -> Optional[Conversation]:
        """Load conversation from storage."""
        file_path = self.storage_path / f"{conversation_id}.json"

        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text())
            return Conversation(
                id=data["id"],
                created_at=datetime.fromisoformat(data["created_at"]),
                turns=[
                    ConversationTurn(
                        question=turn["question"],
                        answer=turn["answer"],
                        sources=turn["sources"],
                        timestamp=datetime.fromisoformat(turn["timestamp"]),
                    )
                    for turn in data["turns"]
                ],
            )
        except Exception:
            return None
```

### 6. Updated Query API Routes (`src/api/routes/query.py`)

```python
# src/api/routes/query.py (complete implementation)

from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated, Optional, List
from pydantic import BaseModel

from ..dependencies import get_semantic_search, get_app_config
from ..schemas import SearchResponse, SearchResultResponse
from ...query.engine import QueryEngine
from ...vector.search import SemanticSearch
from ...config import Config


router = APIRouter()


# ============== Request/Response Models ==============

class QueryRequest(BaseModel):
    """Request for querying the library."""
    question: str
    conversation_id: Optional[str] = None
    n_chunks: int = 10
    min_similarity: float = 0.5


class SourceInfo(BaseModel):
    """Information about a source."""
    file: str
    section: str
    excerpt: str


class QueryResponse(BaseModel):
    """Response from a query."""
    answer: str
    sources: List[SourceInfo]
    confidence: float
    conversation_id: str
    related_topics: List[str]


class ConversationTurnResponse(BaseModel):
    """A turn in a conversation."""
    question: str
    answer: str
    sources: List[SourceInfo]
    timestamp: str


class ConversationResponse(BaseModel):
    """A conversation."""
    id: str
    created_at: str
    turns: List[ConversationTurnResponse]


# ============== Dependencies ==============

def get_query_engine(
    config: Annotated[Config, Depends(get_app_config)],
    search: Annotated[SemanticSearch, Depends(get_semantic_search)],
) -> QueryEngine:
    """Get query engine instance."""
    return QueryEngine(
        library_path=config.library.path,
        semantic_search=search,
    )


# ============== Endpoints ==============

@router.post("/ask", response_model=QueryResponse)
async def query_library(
    request: QueryRequest,
    engine: Annotated[QueryEngine, Depends(get_query_engine)],
):
    """
    Query the knowledge library with natural language.

    This endpoint uses RAG (Retrieval-Augmented Generation) to:
    1. Find relevant content in your library
    2. Generate an answer based on that content
    3. Include citations to source files

    The response includes:
    - answer: The generated answer
    - sources: List of cited source files with excerpts
    - confidence: Confidence score (0-1) based on source quality
    - conversation_id: ID to continue this conversation
    - related_topics: Related topics found in your library
    """
    try:
        result = await engine.query(
            question=request.question,
            conversation_id=request.conversation_id,
            n_chunks=request.n_chunks,
            min_similarity=request.min_similarity,
        )

        return QueryResponse(
            answer=result.answer,
            sources=[
                SourceInfo(
                    file=s["file"],
                    section=s.get("section", ""),
                    excerpt=s.get("excerpt", ""),
                )
                for s in result.sources
            ],
            confidence=result.confidence,
            conversation_id=result.conversation_id,
            related_topics=result.related_topics,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    query: str,
    limit: int = 10,
    min_similarity: float = 0.5,
    engine: Annotated[QueryEngine, Depends(get_query_engine)] = None,
):
    """
    Perform semantic search without RAG generation.

    Returns raw search results from the vector store.
    Useful for exploring the library or debugging.
    """
    results = await engine.search_only(
        query=query,
        n_results=limit,
        min_similarity=min_similarity,
    )

    return SearchResponse(
        query=query,
        results=[
            SearchResultResponse(
                content=r["content"],
                file_path=r["file_path"],
                section=r.get("section", ""),
                similarity=r["similarity"],
                chunk_id=r.get("chunk_id", ""),
            )
            for r in results
        ],
        total=len(results),
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    limit: int = 20,
    engine: Annotated[QueryEngine, Depends(get_query_engine)] = None,
):
    """List recent conversations."""
    conversations = await engine.conversations.list_conversations(limit=limit)

    return [
        ConversationResponse(
            id=c.id,
            created_at=c.created_at.isoformat(),
            turns=[
                ConversationTurnResponse(
                    question=t.question,
                    answer=t.answer,
                    sources=[
                        SourceInfo(
                            file=s["file"],
                            section=s.get("section", ""),
                            excerpt=s.get("excerpt", ""),
                        )
                        for s in t.sources
                    ],
                    timestamp=t.timestamp.isoformat(),
                )
                for t in c.turns
            ],
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    engine: Annotated[QueryEngine, Depends(get_query_engine)] = None,
):
    """Get a specific conversation."""
    conversation = await engine.conversations.get(conversation_id)

    if not conversation:
        raise HTTPException(404, f"Conversation {conversation_id} not found")

    return ConversationResponse(
        id=conversation.id,
        created_at=conversation.created_at.isoformat(),
        turns=[
            ConversationTurnResponse(
                question=t.question,
                answer=t.answer,
                sources=[
                    SourceInfo(
                        file=s["file"],
                        section=s.get("section", ""),
                        excerpt=s.get("excerpt", ""),
                    )
                    for s in t.sources
                ],
                timestamp=t.timestamp.isoformat(),
            )
            for t in conversation.turns
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    engine: Annotated[QueryEngine, Depends(get_query_engine)] = None,
):
    """Delete a conversation."""
    success = await engine.conversations.delete(conversation_id)

    if not success:
        raise HTTPException(404, f"Conversation {conversation_id} not found")

    return {"success": True, "message": f"Conversation {conversation_id} deleted"}
```

### 7. Web UI Integration (No CLI)

Primary UX is the Web UI (Sub-Plan F) with an embedded Claude Code chat panel:

- user asks a question in the UI,
- frontend calls `POST /api/query/ask`,
- response renders answer + citations, and
- conversation history is browseable via `/api/query/conversations/*`.

---

## API Endpoint Summary

### Query Endpoints (`/api/query`)

| Method | Endpoint              | Description            |
| ------ | --------------------- | ---------------------- |
| POST   | `/ask`                | Query library with RAG |
| POST   | `/search`             | Semantic search only   |
| GET    | `/conversations`      | List conversations     |
| GET    | `/conversations/{id}` | Get conversation       |
| DELETE | `/conversations/{id}` | Delete conversation    |

---

## Example Usage

### API

```bash
# Query with RAG
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What do I know about JWT authentication?"}'

# Continue conversation
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What about refresh tokens?",
    "conversation_id": "abc123"
  }'

# Semantic search
curl -X POST "http://localhost:8000/api/query/search?query=authentication&limit=5"
```

---

## Acceptance Criteria

- [ ] Query engine with RAG retrieval working
- [ ] Output mode system prompt implemented
- [ ] Citation extraction from responses
- [ ] Confidence scoring based on source quality
- [ ] Conversation history support (multi-turn)
- [ ] Conversation persistence to disk
- [ ] Query API endpoint (`/api/query/ask`)
- [ ] Search API endpoint (`/api/query/search`)
- [ ] Conversation management endpoints
- [ ] Related topics extraction
- [ ] Proper handling of "not in library" cases

---

## Notes for Downstream Session

1. **SDK Client**: Ensure the SDK client is properly initialized with the output mode system prompt
2. **Index First**: Ensure the vector index exists before first query (triggered automatically on startup or via `POST /api/library/index`)
3. **Conversation Storage**: Conversations are stored in `./sessions/conversations/` as JSON files
4. **Confidence Interpretation**:
   - 0.8+: High confidence, multiple relevant sources
   - 0.5-0.8: Moderate confidence, some relevant content
   - <0.5: Low confidence, limited relevant content
5. **Web UI Integration**: This completes the backend - Sub-Plan F will build the frontend to consume these endpoints

---

_End of Sub-Plan E_

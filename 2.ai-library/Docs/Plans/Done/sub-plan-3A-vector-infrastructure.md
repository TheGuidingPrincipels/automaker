# Sub-Plan 3A: Vector Infrastructure (Phase 3A)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`knowledge-library`)
> **Dependencies**: Sub-Plan A (Core Engine), Sub-Plan B (Smart Routing)
> **Next Phase**: Sub-Plan D (REST API) or Sub-Plan 3B (Intelligence Layer)
> **Revision Date**: 2026-01-21
> **Split From**: `sub-plan-C-vector-rag-revised.md`
> **Scope**: Qdrant vector store, embedding providers, indexing, semantic search, backward-compatible interfaces

---

## Goal

Implement the **vector search infrastructure** using Qdrant that immediately upgrades Sub-Plan B's candidate finding from lexical matching to vector similarity. This phase establishes:

1. **Qdrant Vector Store** - Production-grade vector database with metadata support
2. **Embedding Provider Abstraction** - Pluggable providers (Mistral, OpenAI)
3. **Library Indexer** - Index markdown files with semantic chunking
4. **Semantic Search** - Find similar content using embeddings
5. **Backward-Compatible Interfaces** - Upgrade `CandidateFinder` and `MergeDetector` for Sub-Plan B

Phase 3B (Intelligence Layer) will add classification, taxonomy, and relationship capabilities on top of this infrastructure.

---

## Prerequisites from Previous Phases

Before starting this phase, ensure:

**From Sub-Plan A:**

- All data models implemented (`ContentBlock`, `ExtractionSession`, etc.)
- Session management working
- Content extraction functional
- Library manifest generation working

**From Sub-Plan B:**

- `PlanningFlow` implemented (CleanupPlan → RoutingPlan generation)
- `CandidateFinder` interface defined (lexical baseline)
- `MergeDetector` interface defined (keyword overlap baseline)
- Prompt contracts established (JSON schemas for routing)

---

## New Capabilities

| Capability                           | Description                                           |
| ------------------------------------ | ----------------------------------------------------- |
| **Qdrant Vector Store**              | Production-grade vector DB with metadata payloads     |
| **Embedding Provider Abstraction**   | Pluggable embedding providers (Mistral, OpenAI, etc.) |
| **Semantic Chunking**                | 512-2048 token chunks with overlap                    |
| **Library Indexing**                 | Index all markdown files for semantic search          |
| **Incremental Indexing**             | Checksum-based, only reindex changed files            |
| **Semantic Search**                  | Find relevant content using vector similarity         |
| **Vector-Powered Candidate Finding** | Upgrade Phase 2 lexical matching to vector similarity |
| **Enhanced Merge Detection**         | Use vector similarity instead of keyword matching     |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3A: VECTOR INFRASTRUCTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  Markdown Files  │───▶│  Library Indexer │───▶│  Qdrant Store    │      │
│  │  (from library)  │    │  (chunking +     │    │  (vectors +      │      │
│  └──────────────────┘    │   embedding)     │    │   basic payload) │      │
│                          └──────────────────┘    └────────┬─────────┘      │
│                                                           │                 │
│  ┌──────────────────┐    ┌──────────────────┐            │                 │
│  │  Embedding       │◀───│  Provider        │            │                 │
│  │  Providers       │    │  Factory         │            │                 │
│  │  (Mistral/OpenAI)│    └──────────────────┘            │                 │
│  └──────────────────┘                                    │                 │
│                                                           ▼                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     BACKWARD COMPATIBLE INTERFACES                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐       │  │
│  │  │ CandidateFinder │  │ MergeDetector   │  │ SemanticSearch  │       │  │
│  │  │ .top_candidates │  │ .find_merge_    │  │ .search()       │       │  │
│  │  │ ()              │  │  candidates()   │  │ .find_merge_    │       │  │
│  │  │ [UPGRADED]      │  │ [UPGRADED]      │  │  candidates()   │       │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PREPARED FOR PHASE 3B (not active yet)                               │  │
│  │  - Payload schema has fields for: taxonomy, classification,           │  │
│  │    relationships, provenance, audit_trail                             │  │
│  │  - These fields remain empty/default until Phase 3B activates them    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
src/
├── vector/
│   ├── __init__.py
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract embedding provider
│   │   ├── mistral.py              # Mistral API provider (default)
│   │   ├── openai.py               # OpenAI API provider
│   │   └── local.py                # Local sentence-transformers (future)
│   ├── embeddings.py               # Provider factory
│   ├── store.py                    # QdrantVectorStore
│   ├── indexer.py                  # Library indexer
│   ├── search.py                   # SemanticSearch interface
│   └── chunking.py                 # Semantic chunking (512-2048 tokens)
│
├── payloads/
│   ├── __init__.py
│   └── schema.py                   # Content payload schema (basic fields active, 3B fields prepared)
│
└── library/
    ├── candidates.py               # CandidateFinder (Phase 3A vector upgrade)
    └── manifest.py                 # (unchanged from Phase 2)
```

---

## Implementation Details

### 1. Embedding Provider Abstraction

#### 1.1 Base Provider (`src/vector/providers/base.py`)

```python
# src/vector/providers/base.py

from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel


class EmbeddingProviderConfig(BaseModel):
    """Configuration for an embedding provider."""
    provider: str                     # "mistral", "openai", "cohere", "local"
    model: str                        # Model name/ID
    api_key: Optional[str] = None     # Can be None if using env var
    api_key_env_var: Optional[str] = None  # e.g., "MISTRAL_API_KEY"
    base_url: Optional[str] = None    # Optional custom endpoint
    dimensions: Optional[int] = None  # Expected embedding dimensions


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, config: EmbeddingProviderConfig):
        self.config = config
        self._api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> Optional[str]:
        """Resolve API key from config or environment variable."""
        import os

        # Direct config takes precedence
        if self.config.api_key:
            return self.config.api_key

        # Fall back to environment variable
        if self.config.api_key_env_var:
            return os.environ.get(self.config.api_key_env_var)

        # Default env var based on provider
        default_env_vars = {
            "mistral": "MISTRAL_API_KEY",
            "openai": "OPENAI_API_KEY",
            "cohere": "COHERE_API_KEY",
        }
        default_var = default_env_vars.get(self.config.provider)
        if default_var:
            return os.environ.get(default_var)

        return None

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass

    async def embed_single(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embeddings = await self.embed([text])
        return embeddings[0]

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimensions for this provider/model."""
        pass
```

#### 1.2 Mistral Provider (`src/vector/providers/mistral.py`)

```python
# src/vector/providers/mistral.py

import httpx
from typing import List

from .base import EmbeddingProvider, EmbeddingProviderConfig


class MistralEmbeddingProvider(EmbeddingProvider):
    """Mistral API embedding provider."""

    DIMENSIONS = {
        "mistral-embed": 1024,
    }

    def __init__(self, config: EmbeddingProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.mistral.ai/v1"
        self.model = config.model or "mistral-embed"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Mistral API."""
        if not self._api_key:
            raise ValueError(
                "Mistral API key not found. Set MISTRAL_API_KEY environment variable "
                "or provide api_key in config."
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return [item["embedding"] for item in data["data"]]

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS.get(self.model, 1024)
```

#### 1.3 OpenAI Provider (`src/vector/providers/openai.py`)

```python
# src/vector/providers/openai.py

import httpx
from typing import List

from .base import EmbeddingProvider, EmbeddingProviderConfig


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI API embedding provider."""

    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, config: EmbeddingProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.model = config.model or "text-embedding-3-small"

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not self._api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or provide api_key in config."
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "input": texts,
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            return [item["embedding"] for item in data["data"]]

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS.get(self.model, 1536)
```

#### 1.4 Provider Factory (`src/vector/embeddings.py`)

```python
# src/vector/embeddings.py

from typing import Optional

from .providers.base import EmbeddingProvider, EmbeddingProviderConfig
from .providers.mistral import MistralEmbeddingProvider
from .providers.openai import OpenAIEmbeddingProvider


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    _providers = {
        "mistral": MistralEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        # Future: "cohere": CohereEmbeddingProvider,
        # Future: "local": LocalEmbeddingProvider,
    }

    @classmethod
    def create(cls, config: EmbeddingProviderConfig) -> EmbeddingProvider:
        """Create an embedding provider based on config."""
        provider_class = cls._providers.get(config.provider)
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown embedding provider: {config.provider}. "
                f"Available: {available}"
            )
        return provider_class(config)

    @classmethod
    def register(cls, name: str, provider_class: type):
        """Register a custom embedding provider."""
        cls._providers[name] = provider_class


def get_embedding_provider(config: Optional[dict] = None) -> EmbeddingProvider:
    """
    Get the configured embedding provider.

    Args:
        config: Optional config dict. If not provided, loads from settings.

    Returns:
        Configured EmbeddingProvider instance.
    """
    if config is None:
        from ..config import get_config
        app_config = get_config()
        config = app_config.embeddings

    provider_config = EmbeddingProviderConfig(**config)
    return EmbeddingProviderFactory.create(provider_config)
```

---

### 2. Basic Payload Schema (`src/payloads/schema.py`)

This schema includes all fields needed for Phase 3A, plus prepared fields for Phase 3B (which remain empty/default until 3B activates them).

```python
# src/payloads/schema.py

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ContentType(str, Enum):
    """Types of content in the knowledge library."""
    AGENT_SYSTEM = "agent_system"
    BLUEPRINT = "blueprint"
    FEATURE = "feature"
    RESEARCH = "research"
    NOTE = "note"
    GENERAL = "general"


class ClassificationTier(str, Enum):
    """Which classification tier was used. (Phase 3B)"""
    FAST = "fast"
    LLM = "llm"
    MANUAL = "manual"
    NONE = "none"  # Phase 3A default


class RelationshipType(str, Enum):
    """Supported relationship types for pseudo-graph. (Phase 3B)"""
    # Content relationships
    IMPLEMENTS = "implements"
    DEPENDS_ON = "depends_on"
    RELATES_TO = "relates_to"
    REFERENCES = "references"
    # Workflow relationships
    PRODUCES = "produces"
    CONSUMES = "consumes"
    TRIGGERS = "triggers"
    # Evolution relationships
    SUPERSEDES = "supersedes"
    DERIVES_FROM = "derives_from"
    MERGES = "merges"


class TaxonomyPath(BaseModel):
    """
    Hierarchical taxonomy location.

    Phase 3A: Can use simple full_path string.
    Phase 3B: Full structured taxonomy with levels.
    """
    level1: str = ""                      # Human-defined (e.g., "Agent-Systems")
    level2: str = ""                      # Human-defined (e.g., "Research")
    level3: Optional[str] = None          # AI-assisted
    level4: Optional[str] = None          # AI-assisted
    full_path: str = ""                   # e.g., "Agent-Systems/Research/Market-Analysis"

    @classmethod
    def from_path_string(cls, path: str) -> "TaxonomyPath":
        """Parse a path string like 'Agent-Systems/Research/Market-Analysis'."""
        parts = path.split("/")
        return cls(
            level1=parts[0] if len(parts) > 0 else "",
            level2=parts[1] if len(parts) > 1 else "",
            level3=parts[2] if len(parts) > 2 else None,
            level4=parts[3] if len(parts) > 3 else None,
            full_path=path,
        )

    @classmethod
    def from_file_path(cls, file_path: str) -> "TaxonomyPath":
        """
        Derive taxonomy from file path (Phase 3A simple approach).
        Phase 3B will use proper classification instead.
        """
        # Remove library prefix and .md extension
        path = file_path.replace("library/", "").replace(".md", "")
        return cls.from_path_string(path)


class Relationship(BaseModel):
    """
    A single relationship to another content item.

    Phase 3B: Relationships are actively managed.
    Phase 3A: This structure exists but relationships list remains empty.
    """
    target_id: str
    relationship_type: RelationshipType
    metadata: dict = Field(default_factory=dict)  # Type-specific metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"


class ClassificationResult(BaseModel):
    """
    Result of content classification.

    Phase 3B: Populated by ClassificationService.
    Phase 3A: Uses default/empty values.
    """
    taxonomy_path: TaxonomyPath = Field(default_factory=TaxonomyPath)
    confidence: float = 0.0               # 0.0 = not classified (Phase 3A default)
    tier_used: ClassificationTier = ClassificationTier.NONE
    reasoning: Optional[str] = None       # LLM explanation (if LLM tier used)
    alternatives: list[TaxonomyPath] = Field(default_factory=list)


class Provenance(BaseModel):
    """Track where content came from (no information loss)."""
    source_file: str                      # Original file path
    source_url: Optional[str] = None      # If from web
    source_session_id: Optional[str] = None  # Extraction session
    extraction_method: str = "manual"     # "manual" | "automated" | "llm"
    original_heading_path: list[str] = Field(default_factory=list)
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class AuditEntry(BaseModel):
    """
    Single audit log entry.

    Phase 3B: Full audit trail management.
    Phase 3A: Basic creation entry only.
    """
    action: str                           # "created" | "updated" | "merged" | "moved"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: str = "system"
    details: dict = Field(default_factory=dict)
    previous_state: Optional[dict] = None  # For rollback capability


class ContentPayload(BaseModel):
    """
    Complete payload schema for Qdrant points.

    This schema is designed to support both Phase 3A and Phase 3B:
    - Phase 3A: Uses basic fields (identity, content metadata, provenance)
    - Phase 3B: Activates classification, relationships, audit_trail

    Fields marked with (Phase 3B) remain at default values until Phase 3B.
    """
    # === PHASE 3A: ACTIVE FIELDS ===

    # Identity
    content_id: str                       # UUID
    content_type: ContentType = ContentType.GENERAL

    # Content metadata
    title: Optional[str] = None
    file_path: str                        # Current location in library
    section: Optional[str] = None
    chunk_index: int = 0
    chunk_total: int = 1
    content_hash: str = ""                # For deduplication

    # Provenance (basic tracking)
    provenance: Provenance = Field(default_factory=lambda: Provenance(source_file=""))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # === PHASE 3B: PREPARED FIELDS (default/empty until 3B) ===

    # Taxonomy (Phase 3B: populated by ClassificationService)
    taxonomy: TaxonomyPath = Field(default_factory=TaxonomyPath)

    # Classification metadata (Phase 3B)
    classification: ClassificationResult = Field(default_factory=ClassificationResult)

    # Relationships - pseudo-graph edges (Phase 3B)
    relationships: list[Relationship] = Field(default_factory=list)

    # Audit trail (Phase 3B: full management)
    audit_trail: list[AuditEntry] = Field(default_factory=list)

    # === METHODS ===

    def add_relationship(
        self,
        target_id: str,
        rel_type: RelationshipType,
        metadata: dict = None,
    ) -> None:
        """
        Add a relationship to another content item.
        (Phase 3B method - included for forward compatibility)
        """
        self.relationships.append(Relationship(
            target_id=target_id,
            relationship_type=rel_type,
            metadata=metadata or {},
        ))
        self.updated_at = datetime.utcnow()
        self.audit_trail.append(AuditEntry(
            action="relationship_added",
            details={"target_id": target_id, "type": rel_type.value},
        ))

    def get_relationships_by_type(
        self,
        rel_type: RelationshipType,
    ) -> list[Relationship]:
        """Get all relationships of a specific type. (Phase 3B method)"""
        return [r for r in self.relationships if r.relationship_type == rel_type]

    def to_qdrant_payload(self) -> dict:
        """Convert to dict for Qdrant storage."""
        return self.model_dump(mode="json")

    @classmethod
    def from_qdrant_payload(cls, payload: dict) -> "ContentPayload":
        """Reconstruct from Qdrant payload dict."""
        return cls.model_validate(payload)

    @classmethod
    def create_basic(
        cls,
        content_id: str,
        file_path: str,
        section: Optional[str] = None,
        chunk_index: int = 0,
        chunk_total: int = 1,
        content_hash: str = "",
        source_file: str = "",
    ) -> "ContentPayload":
        """
        Factory method for Phase 3A basic payload creation.
        Creates a payload with minimal fields, leaving 3B fields at defaults.
        """
        # Derive simple taxonomy from file path
        taxonomy = TaxonomyPath.from_file_path(file_path)

        return cls(
            content_id=content_id,
            file_path=file_path,
            section=section,
            chunk_index=chunk_index,
            chunk_total=chunk_total,
            content_hash=content_hash,
            taxonomy=taxonomy,
            provenance=Provenance(
                source_file=source_file or file_path,
                extraction_method="automated",
            ),
            audit_trail=[AuditEntry(action="created")],
        )
```

---

### 3. Qdrant Vector Store (`src/vector/store.py`)

```python
# src/vector/store.py

from typing import Optional
from pathlib import Path
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from .embeddings import get_embedding_provider
from ..payloads.schema import ContentPayload, RelationshipType


class QdrantVectorStore:
    """
    Qdrant-based vector store with rich metadata payloads.

    Phase 3A: Core vector storage and search functionality.
    Phase 3B: Adds relationship queries and advanced filtering.
    """

    COLLECTION_NAME = "knowledge_library"

    def __init__(
        self,
        url: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        embedding_config: Optional[dict] = None,
    ):
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=url,
            port=port,
            api_key=api_key,
        )

        # Initialize embedding provider
        self.embeddings = get_embedding_provider(embedding_config)

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.COLLECTION_NAME for c in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.embeddings.dimensions,
                    distance=Distance.COSINE,
                ),
            )

            # Create payload indexes for efficient filtering
            self._create_payload_indexes()

    def _create_payload_indexes(self) -> None:
        """Create indexes on frequently queried payload fields."""
        indexes = [
            ("content_type", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.full_path", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.level1", models.PayloadSchemaType.KEYWORD),
            ("taxonomy.level2", models.PayloadSchemaType.KEYWORD),
            ("file_path", models.PayloadSchemaType.KEYWORD),
            ("content_hash", models.PayloadSchemaType.KEYWORD),
            ("classification.confidence", models.PayloadSchemaType.FLOAT),
            ("created_at", models.PayloadSchemaType.DATETIME),
            ("updated_at", models.PayloadSchemaType.DATETIME),
        ]

        for field_name, field_type in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name=field_name,
                    field_schema=field_type,
                )
            except Exception:
                pass  # Index may already exist

    async def add_content(
        self,
        content_id: str,
        text: str,
        payload: ContentPayload,
    ) -> None:
        """
        Add a single content item with its embedding and rich payload.
        """
        embedding = await self.embeddings.embed_single(text)

        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[
                PointStruct(
                    id=content_id,
                    vector=embedding,
                    payload=payload.to_qdrant_payload(),
                )
            ],
        )

    async def add_contents_batch(
        self,
        items: list[tuple[str, str, ContentPayload]],  # (id, text, payload)
        batch_size: int = 100,
    ) -> None:
        """
        Add multiple content items in batches.
        """
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            texts = [item[1] for item in batch]
            embeddings = await self.embeddings.embed(texts)

            points = [
                PointStruct(
                    id=item[0],
                    vector=embeddings[j],
                    payload=item[2].to_qdrant_payload(),
                )
                for j, item in enumerate(batch)
            ]

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
            )

    async def search(
        self,
        query: str,
        n_results: int = 10,
        filter_taxonomy_l1: Optional[str] = None,
        filter_taxonomy_l2: Optional[str] = None,
        filter_content_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
    ) -> list[dict]:
        """
        Search for similar content with optional filters.

        Returns results with payloads and similarity scores.
        """
        query_embedding = await self.embeddings.embed_single(query)

        # Build filter conditions
        conditions = []

        if filter_taxonomy_l1:
            conditions.append(
                models.FieldCondition(
                    key="taxonomy.level1",
                    match=models.MatchValue(value=filter_taxonomy_l1),
                )
            )

        if filter_taxonomy_l2:
            conditions.append(
                models.FieldCondition(
                    key="taxonomy.level2",
                    match=models.MatchValue(value=filter_taxonomy_l2),
                )
            )

        if filter_content_type:
            conditions.append(
                models.FieldCondition(
                    key="content_type",
                    match=models.MatchValue(value=filter_content_type),
                )
            )

        if min_confidence is not None:
            conditions.append(
                models.FieldCondition(
                    key="classification.confidence",
                    range=models.Range(gte=min_confidence),
                )
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=n_results,
            with_payload=True,
        )

        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": ContentPayload.from_qdrant_payload(hit.payload),
            }
            for hit in results
        ]

    async def search_by_relationship(
        self,
        content_id: str,
        relationship_type: RelationshipType,
    ) -> list[dict]:
        """
        Find all content related to a given item by relationship type.

        This enables pseudo-graph traversal.
        (Phase 3B: Active use. Phase 3A: Available but relationships empty.)
        """
        # First, get the source content
        source = self.client.retrieve(
            collection_name=self.COLLECTION_NAME,
            ids=[content_id],
            with_payload=True,
        )

        if not source:
            return []

        payload = ContentPayload.from_qdrant_payload(source[0].payload)
        related_ids = [
            r.target_id for r in payload.relationships
            if r.relationship_type == relationship_type
        ]

        if not related_ids:
            return []

        # Retrieve related content
        related = self.client.retrieve(
            collection_name=self.COLLECTION_NAME,
            ids=related_ids,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in related
        ]

    async def find_by_taxonomy_path(
        self,
        taxonomy_path: str,
        n_results: int = 100,
    ) -> list[dict]:
        """
        Find all content under a taxonomy path.

        Supports prefix matching (e.g., "Blueprints/Development" matches all Development blueprints).
        """
        results = self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="taxonomy.full_path",
                        match=models.MatchText(text=taxonomy_path),
                    )
                ]
            ),
            limit=n_results,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in results[0]
        ]

    async def find_duplicates(
        self,
        content_hash: str,
    ) -> list[dict]:
        """Find content with matching hash (potential duplicates)."""
        results = self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="content_hash",
                        match=models.MatchValue(value=content_hash),
                    )
                ]
            ),
            limit=10,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
            }
            for point in results[0]
        ]

    async def update_payload(
        self,
        content_id: str,
        payload_updates: dict,
    ) -> None:
        """Update specific payload fields for a content item."""
        self.client.set_payload(
            collection_name=self.COLLECTION_NAME,
            payload=payload_updates,
            points=[content_id],
        )

    async def delete_content(self, content_id: str) -> None:
        """Delete a content item."""
        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.PointIdsList(points=[content_id]),
        )

    async def delete_by_file(self, file_path: str) -> None:
        """Delete all content from a specific file."""
        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_path",
                            match=models.MatchValue(value=file_path),
                        )
                    ]
                )
            ),
        )

    def get_stats(self) -> dict:
        """Get collection statistics."""
        info = self.client.get_collection(self.COLLECTION_NAME)
        return {
            "total_points": info.points_count,
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "status": info.status,
            "embedding_dimensions": self.embeddings.dimensions,
            "provider": self.embeddings.config.provider,
            "model": self.embeddings.config.model,
        }
```

---

### 4. Library Indexer (`src/vector/indexer.py`)

```python
# src/vector/indexer.py

from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import yaml
import uuid
from datetime import datetime

from .store import QdrantVectorStore
from ..payloads.schema import ContentPayload, Provenance, AuditEntry


class LibraryIndexer:
    """
    Keep vector index in sync with markdown files in the library.
    Supports incremental indexing based on file checksums.
    """

    def __init__(
        self,
        library_path: str,
        vector_store: QdrantVectorStore,
    ):
        self.library_path = Path(library_path)
        self.store = vector_store
        self.index_state_file = self.library_path / ".vector_state.yaml"

    async def index_file(self, file_path: Path) -> int:
        """
        Index a single markdown file. Returns chunk count.
        """
        content = file_path.read_text(encoding="utf-8")
        rel_path = str(file_path.relative_to(self.library_path))

        # Extract chunks (paragraphs, sections, etc.)
        chunks = self._extract_chunks_for_indexing(content, rel_path)

        if not chunks:
            return 0

        # Remove old chunks for this file
        await self.store.delete_by_file(rel_path)

        # Add new chunks
        items = [
            (chunk["id"], chunk["content"], chunk["payload"])
            for chunk in chunks
        ]
        await self.store.add_contents_batch(items)

        # Update state
        await self._update_file_state(rel_path, content)

        return len(chunks)

    async def index_all(self, force: bool = False) -> Dict[str, int]:
        """
        Index all markdown files in library.

        Args:
            force: If True, reindex all files regardless of checksums

        Returns:
            Dict mapping file paths to chunk counts
        """
        results = {}
        state = await self._load_state()

        for md_file in self.library_path.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue  # Skip index files

            rel_path = str(md_file.relative_to(self.library_path))

            # Check if file needs indexing
            if not force:
                current_checksum = self._calculate_checksum(md_file)
                stored_checksum = state.get(rel_path, {}).get("checksum")

                if current_checksum == stored_checksum:
                    continue  # File hasn't changed

            chunk_count = await self.index_file(md_file)
            results[rel_path] = chunk_count

        return results

    async def remove_deleted_files(self) -> List[str]:
        """
        Remove vectors for files that no longer exist.
        Returns list of removed file paths.
        """
        state = await self._load_state()
        removed = []

        for rel_path in list(state.keys()):
            full_path = self.library_path / rel_path
            if not full_path.exists():
                await self.store.delete_by_file(rel_path)
                del state[rel_path]
                removed.append(rel_path)

        await self._save_state(state)
        return removed

    async def find_similar(
        self,
        content: str,
        n_results: int = 5,
        exclude_file: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find similar content in the library.

        Args:
            content: Content to find similar matches for
            n_results: Number of results to return
            exclude_file: Optional file to exclude from results

        Returns:
            List of similar chunks with metadata
        """
        results = await self.store.search(content, n_results=n_results + 5)

        # Filter out excluded file if specified
        if exclude_file:
            results = [
                r for r in results
                if r["payload"].file_path != exclude_file
            ]

        return results[:n_results]

    def _extract_chunks_for_indexing(
        self,
        content: str,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        """
        Extract content chunks for vector indexing.

        Chunks are created at section/paragraph boundaries to maintain
        semantic coherence. Target chunk size: 512-2048 tokens.
        """
        chunks = []
        chunk_index = 0
        current_section = ""

        lines = content.split("\n")
        current_chunk = []
        chunk_start_line = 0

        for i, line in enumerate(lines):
            # Detect section headers
            if line.startswith("#"):
                # Save previous chunk if exists
                if current_chunk:
                    chunk_text = "\n".join(current_chunk).strip()
                    if len(chunk_text) > 50:  # Minimum chunk size
                        chunk_id = str(uuid.uuid4())
                        content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                        payload = ContentPayload.create_basic(
                            content_id=chunk_id,
                            file_path=file_path,
                            section=current_section,
                            chunk_index=chunk_index,
                            content_hash=content_hash,
                            source_file=file_path,
                        )

                        chunks.append({
                            "id": chunk_id,
                            "content": chunk_text,
                            "payload": payload,
                        })
                        chunk_index += 1

                # Start new section
                current_section = line.lstrip("#").strip()
                current_chunk = [line]
                chunk_start_line = i

            # Detect paragraph breaks (double newline)
            elif line.strip() == "" and current_chunk:
                chunk_text = "\n".join(current_chunk).strip()
                if len(chunk_text) > 50:
                    chunk_id = str(uuid.uuid4())
                    content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                    payload = ContentPayload.create_basic(
                        content_id=chunk_id,
                        file_path=file_path,
                        section=current_section,
                        chunk_index=chunk_index,
                        content_hash=content_hash,
                        source_file=file_path,
                    )

                    chunks.append({
                        "id": chunk_id,
                        "content": chunk_text,
                        "payload": payload,
                    })
                    chunk_index += 1
                    current_chunk = []
                    chunk_start_line = i + 1
            else:
                current_chunk.append(line)

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk).strip()
            if len(chunk_text) > 50:
                chunk_id = str(uuid.uuid4())
                content_hash = hashlib.md5(chunk_text.encode()).hexdigest()

                payload = ContentPayload.create_basic(
                    content_id=chunk_id,
                    file_path=file_path,
                    section=current_section,
                    chunk_index=chunk_index,
                    content_hash=content_hash,
                    source_file=file_path,
                )

                chunks.append({
                    "id": chunk_id,
                    "content": chunk_text,
                    "payload": payload,
                })

        # Update chunk_total for all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk["payload"].chunk_total = total

        return chunks

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file content."""
        content = file_path.read_bytes()
        return hashlib.md5(content).hexdigest()

    async def _load_state(self) -> Dict[str, Dict]:
        """Load indexing state from file."""
        if not self.index_state_file.exists():
            return {}

        with open(self.index_state_file) as f:
            return yaml.safe_load(f) or {}

    async def _save_state(self, state: Dict[str, Dict]) -> None:
        """Save indexing state to file."""
        with open(self.index_state_file, "w") as f:
            yaml.safe_dump(state, f)

    async def _update_file_state(self, rel_path: str, content: str) -> None:
        """Update state for a single file."""
        state = await self._load_state()
        state[rel_path] = {
            "checksum": hashlib.md5(content.encode()).hexdigest(),
            "indexed_at": datetime.now().isoformat(),
        }
        await self._save_state(state)
```

---

### 5. Semantic Search Interface (`src/vector/search.py`)

```python
# src/vector/search.py

from typing import Optional
from dataclasses import dataclass

from .store import QdrantVectorStore
from .indexer import LibraryIndexer
from ..payloads.schema import ContentPayload


@dataclass
class SearchResult:
    """
    A search result with metadata.

    BACKWARD COMPATIBLE with Sub-Plan B expectations.
    """
    content: str
    file_path: str
    section: str
    similarity: float
    chunk_id: str
    # Phase 3A additions
    taxonomy_path: Optional[str] = None
    content_type: Optional[str] = None
    payload: Optional[ContentPayload] = None


class SemanticSearch:
    """
    High-level semantic search interface for the knowledge library.

    BACKWARD COMPATIBLE with Sub-Plan B interfaces.
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        library_path: Optional[str] = None,
    ):
        self.store = vector_store
        self.library_path = library_path
        self.indexer = LibraryIndexer(
            library_path=library_path,
            vector_store=vector_store,
        ) if library_path else None

    async def search(
        self,
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.5,
        filter_taxonomy: Optional[str] = None,
        filter_content_type: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search the library for content similar to the query.

        BACKWARD COMPATIBLE interface.

        Args:
            query: Natural language search query
            n_results: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            filter_taxonomy: Optional taxonomy path filter
            filter_content_type: Optional content type filter

        Returns:
            List of SearchResult objects sorted by similarity
        """
        # Parse taxonomy filter
        taxonomy_l1 = None
        taxonomy_l2 = None
        if filter_taxonomy:
            parts = filter_taxonomy.split("/")
            taxonomy_l1 = parts[0] if len(parts) > 0 else None
            taxonomy_l2 = parts[1] if len(parts) > 1 else None

        raw_results = await self.store.search(
            query=query,
            n_results=n_results * 2,
            filter_taxonomy_l1=taxonomy_l1,
            filter_taxonomy_l2=taxonomy_l2,
            filter_content_type=filter_content_type,
        )

        results = []
        for r in raw_results:
            similarity = r["score"]
            if similarity >= min_similarity:
                payload = r["payload"]
                results.append(SearchResult(
                    content="",  # Content stored separately in Qdrant documents
                    file_path=payload.file_path,
                    section=payload.section or "",
                    similarity=similarity,
                    chunk_id=r["id"],
                    taxonomy_path=payload.taxonomy.full_path if payload.taxonomy else None,
                    content_type=payload.content_type.value if payload.content_type else None,
                    payload=payload,
                ))

        return results[:n_results]

    async def find_merge_candidates(
        self,
        content: str,
        threshold: float = 0.7,
        exclude_file: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Find content that might be candidates for merging.

        BACKWARD COMPATIBLE with Sub-Plan B MergeDetector expectations.

        Args:
            content: New content to find matches for
            threshold: Similarity threshold for merge consideration
            exclude_file: File to exclude (typically the source file)

        Returns:
            List of potential merge candidates
        """
        results = await self.search(
            query=content,
            n_results=10,
            min_similarity=threshold,
        )

        # Filter out excluded file
        if exclude_file:
            results = [r for r in results if r.file_path != exclude_file]

        return results

    async def ensure_indexed(self, force: bool = False) -> dict:
        """
        Ensure the library is indexed before searching.

        BACKWARD COMPATIBLE interface.
        """
        if not self.indexer:
            return {"status": "no_indexer", "files_indexed": 0}

        return await self.indexer.index_all(force=force)

    def get_stats(self) -> dict:
        """Get search index statistics."""
        return self.store.get_stats()
```

---

### 6. Backward-Compatible Candidate Finder (`src/library/candidates.py`)

This preserves the interface from Sub-Plan B while using vector search:

```python
# src/library/candidates.py (Phase 3A vector upgrade)

from dataclasses import dataclass
from typing import Optional

from ..models.content import ContentBlock
from ..vector.store import QdrantVectorStore
from ..vector.search import SemanticSearch


@dataclass
class CandidateDestination:
    """
    A candidate destination for a content block.

    PRESERVED from Sub-Plan B for backward compatibility.
    """
    file_path: str
    section: Optional[str]
    similarity: float
    snippet: str
    # Phase 3A additions (optional, for enhanced UX)
    taxonomy_path: Optional[str] = None
    content_type: Optional[str] = None


class CandidateFinder:
    """
    Find candidate destinations for content blocks.

    Phase 2: Lexical matching (manifest + keyword overlap)
    Phase 3A: Vector similarity (this implementation)

    INTERFACE PRESERVED for Sub-Plan B compatibility:
    - top_candidates(manifest, block, limit) -> List[CandidateDestination]
    """

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        search: Optional[SemanticSearch] = None,
    ):
        self.store = vector_store
        self.search = search or SemanticSearch(vector_store)

    async def top_candidates(
        self,
        manifest: dict,
        block: ContentBlock,
        limit: int = 8,
    ) -> list[CandidateDestination]:
        """
        Find top candidate destinations for a content block.

        BACKWARD COMPATIBLE with Sub-Plan B PlanningFlow.

        Args:
            manifest: Library manifest from Sub-Plan A/B
            block: Content block to find candidates for
            limit: Maximum number of candidates to return

        Returns:
            List of CandidateDestination sorted by similarity
        """
        # Ensure index is up to date
        await self.search.ensure_indexed()

        # Get block content for search
        search_content = getattr(block, 'content_canonical', None) or block.content

        # Search for similar content
        results = await self.store.search(
            query=search_content,
            n_results=limit * 2,  # Get more, filter by manifest
        )

        # Map results to candidates, constrained by manifest
        candidates: list[CandidateDestination] = []

        for result in results:
            payload = result["payload"]
            file_path = payload.file_path
            section = payload.section

            # Validate against manifest
            if not self._is_in_manifest(manifest, file_path, section):
                continue

            candidates.append(CandidateDestination(
                file_path=file_path,
                section=section,
                similarity=result["score"],
                snippet=self._get_snippet(payload),
                taxonomy_path=payload.taxonomy.full_path if payload.taxonomy else None,
                content_type=payload.content_type.value if payload.content_type else None,
            ))

            if len(candidates) >= limit:
                break

        # If not enough candidates from vector search, add from manifest
        if len(candidates) < 3:
            candidates.extend(
                self._fallback_from_manifest(manifest, block, limit - len(candidates))
            )

        return candidates[:limit]

    def _is_in_manifest(
        self,
        manifest: dict,
        file_path: str,
        section: Optional[str],
    ) -> bool:
        """Check if a file/section exists in the library manifest."""
        files = manifest.get("files", [])

        for file_info in files:
            if file_info.get("path") == file_path:
                if section is None:
                    return True
                sections = file_info.get("sections", [])
                return section in sections

        return False

    def _get_snippet(self, payload, max_length: int = 300) -> str:
        """Extract a snippet from payload for preview."""
        title = payload.title or ""
        return title[:max_length]

    def _fallback_from_manifest(
        self,
        manifest: dict,
        block: ContentBlock,
        limit: int,
    ) -> list[CandidateDestination]:
        """
        Fallback: suggest destinations from manifest when vector search
        doesn't have enough results.

        This preserves Phase 2 behavior as a safety net.
        """
        candidates = []
        files = manifest.get("files", [])

        # Simple heuristic: match by keywords in file path
        block_words = set(block.content.lower().split())

        for file_info in files:
            path = file_info.get("path", "")
            path_words = set(path.lower().replace("/", " ").replace("-", " ").split())

            overlap = len(block_words & path_words)
            if overlap > 0:
                candidates.append(CandidateDestination(
                    file_path=path,
                    section=None,
                    similarity=overlap / max(len(block_words), len(path_words)),
                    snippet=file_info.get("description", "")[:300],
                ))

        candidates.sort(key=lambda c: c.similarity, reverse=True)
        return candidates[:limit]
```

---

### 7. Configuration Updates

#### `configs/settings.yaml` (Phase 3A)

```yaml
# configs/settings.yaml (Phase 3A)

# Embedding provider configuration
embeddings:
  provider: mistral
  model: mistral-embed
  # api_key: (use MISTRAL_API_KEY env var)

# Example: Switch to OpenAI
# embeddings:
#   provider: openai
#   model: text-embedding-3-small
#   # api_key: sk-...  # Or set OPENAI_API_KEY env var

# Qdrant vector store
vector:
  url: localhost
  port: 6333
  # api_key: (for Qdrant Cloud)
  collection_name: knowledge_library

# Chunking settings
chunking:
  min_tokens: 512
  max_tokens: 2048
  overlap_tokens: 128
  strategy: semantic # "semantic" | "fixed" | "sentence"
```

#### `pyproject.toml` (Phase 3A dependencies)

```toml
[project]
dependencies = [
    # ... existing dependencies from Phase 1/2 ...
    "qdrant-client>=1.7.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
openai = ["openai>=1.0.0"]
local = ["sentence-transformers>=2.2.0"]
all-embeddings = ["knowledge-library[openai,local]"]
```

---

## Embedding Provider Reference

| Provider              | Model                    | Dimensions | Notes                        |
| --------------------- | ------------------------ | ---------- | ---------------------------- |
| **Mistral** (default) | `mistral-embed`          | 1024       | Good balance of quality/cost |
| OpenAI                | `text-embedding-3-small` | 1536       | High quality, higher cost    |
| OpenAI                | `text-embedding-3-large` | 3072       | Highest quality              |
| Cohere                | `embed-english-v3.0`     | 1024       | Alternative option (future)  |
| Local                 | Sentence Transformers    | varies     | Offline capability (future)  |

---

## Acceptance Criteria

### Core Functionality

- [ ] Qdrant vector store working with basic metadata payloads
- [ ] Embedding provider abstraction (Mistral default, OpenAI alternative)
- [ ] API key resolution (env var OR config file)
- [ ] Library indexer syncs files to vectors
- [ ] Incremental indexing (checksum-based)
- [ ] Semantic search returns relevant chunks
- [ ] Provider switching works without code changes

### Backward Compatibility (Sub-Plan B)

- [ ] `CandidateFinder.top_candidates()` interface preserved
- [ ] `SemanticSearch.find_merge_candidates()` compatible with MergeDetector
- [ ] Library manifest structure unchanged
- [ ] PlanningFlow continues to work with upgraded CandidateFinder

### Performance

- [ ] Vector search <50ms for 100K chunks
- [ ] Indexing processes files incrementally
- [ ] Batch embedding requests for efficiency

### Operations

- [ ] API endpoints for indexing + search (no CLI dependency)
- [ ] Fail-fast on missing API keys (no silent fallbacks)
- [ ] Index state persisted for incremental updates

---

## Notes for Downstream Session

1. **Qdrant Setup**: Self-host with Docker (`docker run -p 6333:6333 qdrant/qdrant`) or use Qdrant Cloud free tier
2. **First Index**: Trigger via `POST /api/library/index` after library exists
3. **Payload Schema**: Includes fields for Phase 3B (taxonomy, classification, relationships) but they remain at defaults until 3B
4. **Phase 3B Upgrade**: Intelligence layer will activate classification, taxonomy manager, and relationship tracking
5. **Phase 4 Integration**: REST API exposes vector search endpoints immediately after 3A

---

_End of Sub-Plan 3A (Vector Infrastructure)_

# src/payloads/schema.py

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


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
    created_at: datetime = Field(default_factory=_utc_now)
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
    ingested_at: datetime = Field(default_factory=_utc_now)
    version: int = 1


class AuditEntry(BaseModel):
    """
    Single audit log entry.

    Phase 3B: Full audit trail management.
    Phase 3A: Basic creation entry only.
    """
    action: str                           # "created" | "updated" | "merged" | "moved"
    timestamp: datetime = Field(default_factory=_utc_now)
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
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

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
        self.updated_at = _utc_now()
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

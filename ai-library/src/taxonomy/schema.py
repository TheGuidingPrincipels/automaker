"""Taxonomy data models using Pydantic v2."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CategoryStatus(str, Enum):
    """Status of a taxonomy category."""

    ACTIVE = "active"
    PROPOSED = "proposed"
    DEPRECATED = "deprecated"


class TaxonomyNode(BaseModel):
    """A node in the taxonomy tree."""

    name: str = Field(..., description="Category name (slug format)")
    description: str = Field(default="", description="Human-readable description")
    locked: bool = Field(default=False, description="If true, only humans can modify")
    level: int = Field(default=1, ge=1, le=10, description="Depth level in taxonomy")
    parent_path: str | None = Field(
        default=None, description="Full path to parent (e.g., 'technical/programming')"
    )
    children: dict[str, TaxonomyNode] = Field(
        default_factory=dict, description="Child categories"
    )
    status: CategoryStatus = Field(
        default=CategoryStatus.ACTIVE, description="Category status"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(default="system", description="Who created this category")
    content_count: int = Field(
        default=0, description="Number of content items in this category"
    )
    centroid_vector: list[float] | None = Field(
        default=None, description="Average embedding vector for this category"
    )

    @property
    def full_path(self) -> str:
        """Get full taxonomy path."""
        if self.parent_path:
            return f"{self.parent_path}/{self.name}"
        return self.name

    def get_child(self, name: str) -> TaxonomyNode | None:
        """Get a direct child by name."""
        return self.children.get(name)

    def add_child(self, node: TaxonomyNode) -> None:
        """Add a child node."""
        node.parent_path = self.full_path
        node.level = self.level + 1
        self.children[node.name] = node


class ProposedCategory(BaseModel):
    """A category proposed by AI for human review."""

    path: str = Field(..., description="Proposed full path")
    name: str = Field(..., description="Category name")
    description: str = Field(..., description="Proposed description")
    parent_path: str = Field(..., description="Parent category path")
    confidence: float = Field(..., ge=0.0, le=1.0, description="AI confidence score")
    evidence: list[str] = Field(
        default_factory=list, description="Content IDs supporting this category"
    )
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    proposed_by: str = Field(default="ai", description="Who proposed this")
    status: str = Field(default="pending", description="pending, approved, rejected")
    review_notes: str | None = Field(default=None)


class ClassificationThresholds(BaseModel):
    """Thresholds for classification decisions."""

    fast_tier_confidence_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Below this, escalate to LLM"
    )
    new_category_confidence_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Above this for auto-approve"
    )
    auto_approve_level3_plus: bool = Field(
        default=True, description="Auto-approve high-confidence Level 3+"
    )


class EvolutionRules(BaseModel):
    """Rules for taxonomy evolution."""

    min_content_for_split: int = Field(
        default=10, ge=1, description="Min items before suggesting split"
    )
    max_items_per_category: int = Field(
        default=100, ge=10, description="Suggest split above this"
    )
    similarity_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Merge similar categories above this"
    )


class TaxonomyConfig(BaseModel):
    """Full taxonomy configuration."""

    version: str = Field(default="1.0")
    classification: ClassificationThresholds = Field(
        default_factory=ClassificationThresholds
    )
    categories: dict[str, TaxonomyNode] = Field(
        default_factory=dict, description="Root-level categories"
    )
    proposed_categories: list[ProposedCategory] = Field(
        default_factory=list, description="AI-proposed categories pending review"
    )
    evolution: EvolutionRules = Field(default_factory=EvolutionRules)

    def get_category_by_path(self, path: str) -> TaxonomyNode | None:
        """Get a category by its full path (e.g., 'technical/programming/python')."""
        parts = path.strip("/").split("/")
        if not parts:
            return None

        current = self.categories.get(parts[0])
        if current is None:
            return None

        for part in parts[1:]:
            current = current.get_child(part)
            if current is None:
                return None

        return current

    def validate_path(self, path: str) -> bool:
        """Check if a taxonomy path exists."""
        return self.get_category_by_path(path) is not None

    def get_all_paths(self, prefix: str = "") -> list[str]:
        """Get all valid taxonomy paths."""
        paths = []

        def collect_paths(node: TaxonomyNode, current_path: str) -> None:
            full_path = f"{current_path}/{node.name}" if current_path else node.name
            paths.append(full_path)
            for child in node.children.values():
                collect_paths(child, full_path)

        for root in self.categories.values():
            if not prefix or root.name.startswith(prefix):
                collect_paths(root, "")

        return paths


class CategoryProposal(BaseModel):
    """Request to create a new category."""

    name: str = Field(..., min_length=1, max_length=50)
    description: str = Field(..., min_length=10, max_length=500)
    parent_path: str = Field(..., description="Path to parent category")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence_ids: list[str] = Field(
        default_factory=list, description="Content IDs as evidence"
    )


class ClassificationResult(BaseModel):
    """Result of classifying content into taxonomy."""

    primary_path: str = Field(..., description="Best matching taxonomy path")
    primary_confidence: float = Field(..., ge=0.0, le=1.0)
    alternatives: list[tuple[str, float]] = Field(
        default_factory=list, description="Alternative paths with scores"
    )
    tier_used: str = Field(..., description="'fast' or 'llm'")
    new_category_proposed: CategoryProposal | None = Field(
        default=None, description="If AI proposes a new category"
    )
    processing_time_ms: float = Field(default=0.0)

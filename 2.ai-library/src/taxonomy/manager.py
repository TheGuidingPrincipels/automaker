"""Taxonomy manager for loading, validating, and evolving the taxonomy."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import yaml

from src.taxonomy.schema import (
    CategoryProposal,
    CategoryStatus,
    ProposedCategory,
    TaxonomyConfig,
    TaxonomyNode,
)

logger = logging.getLogger(__name__)


class TaxonomyManager:
    """Manages the taxonomy lifecycle: loading, validation, and evolution."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize the taxonomy manager.

        Args:
            config_path: Path to taxonomy.yaml. If None, uses default location.
        """
        self.config_path = Path(config_path) if config_path else self._default_path()
        self.config: TaxonomyConfig | None = None
        self._dirty = False

    @staticmethod
    def _default_path() -> Path:
        """Get default taxonomy config path."""
        return Path(__file__).parent.parent.parent / "configs" / "taxonomy.yaml"

    def load(self) -> TaxonomyConfig:
        """Load taxonomy configuration from YAML.

        Returns:
            Loaded and parsed taxonomy configuration.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config is invalid.
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Taxonomy config not found: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        self.config = self._parse_config(raw_config)
        logger.info(
            "Loaded taxonomy with %d root categories",
            len(self.config.categories),
        )
        return self.config

    def _parse_config(self, raw: dict) -> TaxonomyConfig:
        """Parse raw YAML dict into TaxonomyConfig.

        Args:
            raw: Raw dictionary from YAML.

        Returns:
            Parsed TaxonomyConfig.
        """
        # Parse categories recursively
        categories = {}
        if "categories" in raw:
            for name, data in raw.get("categories", {}).items():
                categories[name] = self._parse_category(name, data, level=1)

        # Parse proposed categories
        proposed = []
        for p in raw.get("proposed_categories", []):
            proposed.append(ProposedCategory(**p))

        return TaxonomyConfig(
            version=raw.get("version", "1.0"),
            classification=raw.get("classification", {}),
            categories=categories,
            proposed_categories=proposed,
            evolution=raw.get("evolution", {}),
        )

    def _parse_category(
        self,
        name: str,
        data: dict,
        level: int,
        parent_path: str | None = None,
    ) -> TaxonomyNode:
        """Recursively parse a category node.

        Args:
            name: Category name.
            data: Category data from YAML.
            level: Depth level.
            parent_path: Path to parent.

        Returns:
            Parsed TaxonomyNode.
        """
        children = {}
        for child_name, child_data in data.get("children", {}).items():
            full_path = f"{parent_path}/{name}" if parent_path else name
            children[child_name] = self._parse_category(
                child_name,
                child_data,
                level=level + 1,
                parent_path=full_path,
            )

        return TaxonomyNode(
            name=name,
            description=data.get("description", ""),
            locked=data.get("locked", False),
            level=level,
            parent_path=parent_path,
            children=children,
            status=CategoryStatus(data.get("status", "active")),
        )

    def save(self) -> None:
        """Save current taxonomy configuration to YAML."""
        if self.config is None:
            raise ValueError("No taxonomy loaded to save")

        output = self._config_to_dict(self.config)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(output, f, default_flow_style=False, sort_keys=False)

        self._dirty = False
        logger.info("Saved taxonomy to %s", self.config_path)

    def _config_to_dict(self, config: TaxonomyConfig) -> dict:
        """Convert TaxonomyConfig to YAML-serializable dict."""
        return {
            "version": config.version,
            "classification": config.classification.model_dump(),
            "categories": {
                name: self._category_to_dict(cat)
                for name, cat in config.categories.items()
            },
            "proposed_categories": [
                p.model_dump() for p in config.proposed_categories
            ],
            "evolution": config.evolution.model_dump(),
        }

    def _category_to_dict(self, node: TaxonomyNode) -> dict:
        """Convert TaxonomyNode to YAML-serializable dict."""
        result = {
            "description": node.description,
            "locked": node.locked,
        }
        if node.children:
            result["children"] = {
                name: self._category_to_dict(child)
                for name, child in node.children.items()
            }
        else:
            result["children"] = {}
        return result

    def validate_path(self, path: str) -> bool:
        """Check if a taxonomy path is valid.

        Args:
            path: Taxonomy path (e.g., 'technical/programming/python').

        Returns:
            True if path exists in taxonomy.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")
        return self.config.validate_path(path)

    def get_category(self, path: str) -> TaxonomyNode | None:
        """Get a category by path.

        Args:
            path: Full taxonomy path.

        Returns:
            TaxonomyNode if found, None otherwise.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")
        return self.config.get_category_by_path(path)

    def get_all_paths(self) -> list[str]:
        """Get all valid taxonomy paths.

        Returns:
            List of all valid paths in the taxonomy.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")
        return self.config.get_all_paths()

    def propose_category(self, proposal: CategoryProposal) -> ProposedCategory:
        """Propose a new category (AI-initiated).

        Args:
            proposal: Category proposal with name, description, parent path.

        Returns:
            Created ProposedCategory record.

        Raises:
            ValueError: If parent path doesn't exist or proposal is invalid.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")

        # Validate parent path exists
        parent = self.get_category(proposal.parent_path)
        if parent is None:
            raise ValueError(f"Parent path not found: {proposal.parent_path}")

        # Check if parent is at Level 2+ (AI can only propose Level 3+)
        if parent.level < 2:
            raise ValueError(
                f"Cannot propose category under Level 1. Parent level: {parent.level}"
            )

        # Create proposed category
        proposed = ProposedCategory(
            path=f"{proposal.parent_path}/{proposal.name}",
            name=proposal.name,
            description=proposal.description,
            parent_path=proposal.parent_path,
            confidence=proposal.confidence,
            evidence=proposal.evidence_ids,
            proposed_at=datetime.now(UTC),
            proposed_by="ai",
            status="pending",
        )

        # Auto-approve if confidence is high enough and Level 3+
        thresholds = self.config.classification
        if (
            proposal.confidence >= thresholds.new_category_confidence_threshold
            and thresholds.auto_approve_level3_plus
            and parent.level >= 2
        ):
            return self._approve_category(proposed)

        # Otherwise, add to pending proposals
        self.config.proposed_categories.append(proposed)
        self._dirty = True
        logger.info("Proposed new category: %s (confidence: %.2f)", proposed.path, proposed.confidence)
        return proposed

    def _approve_category(self, proposed: ProposedCategory) -> ProposedCategory:
        """Approve and create a proposed category.

        Args:
            proposed: The proposed category to approve.

        Returns:
            Updated ProposedCategory with approved status.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")

        parent = self.get_category(proposed.parent_path)
        if parent is None:
            raise ValueError(f"Parent path not found: {proposed.parent_path}")

        # Create new node
        new_node = TaxonomyNode(
            name=proposed.name,
            description=proposed.description,
            locked=False,  # AI-created categories are not locked
            level=parent.level + 1,
            parent_path=proposed.parent_path,
            status=CategoryStatus.ACTIVE,
            created_at=datetime.now(UTC),
            created_by=proposed.proposed_by,
        )

        parent.add_child(new_node)
        proposed.status = "approved"
        self._dirty = True

        logger.info("Auto-approved category: %s", proposed.path)
        return proposed

    def approve_proposal(self, path: str, review_notes: str | None = None) -> bool:
        """Manually approve a pending category proposal.

        Args:
            path: Path of the proposed category.
            review_notes: Optional notes from reviewer.

        Returns:
            True if approved, False if not found.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")

        for proposed in self.config.proposed_categories:
            if proposed.path == path and proposed.status == "pending":
                proposed.review_notes = review_notes
                self._approve_category(proposed)
                return True

        return False

    def reject_proposal(self, path: str, reason: str) -> bool:
        """Reject a pending category proposal.

        Args:
            path: Path of the proposed category.
            reason: Reason for rejection.

        Returns:
            True if rejected, False if not found.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")

        for proposed in self.config.proposed_categories:
            if proposed.path == path and proposed.status == "pending":
                proposed.status = "rejected"
                proposed.review_notes = reason
                self._dirty = True
                logger.info("Rejected category proposal: %s - %s", path, reason)
                return True

        return False

    def get_pending_proposals(self) -> list[ProposedCategory]:
        """Get all pending category proposals.

        Returns:
            List of pending proposals.
        """
        if self.config is None:
            raise ValueError("Taxonomy not loaded")
        return [p for p in self.config.proposed_categories if p.status == "pending"]

    def update_content_count(self, path: str, delta: int = 1) -> None:
        """Update content count for a category.

        Args:
            path: Category path.
            delta: Amount to add (can be negative).
        """
        category = self.get_category(path)
        if category:
            category.content_count += delta
            self._dirty = True

    def needs_save(self) -> bool:
        """Check if taxonomy has unsaved changes."""
        return self._dirty

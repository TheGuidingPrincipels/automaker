# Sub-Plan 3B: Intelligence Layer (Phase 3B)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`knowledge-library`)
> **Dependencies**: Sub-Plan A (Core Engine), Sub-Plan B (Smart Routing), **Sub-Plan 3A (Vector Infrastructure)**
> **Next Phase**: Sub-Plan D (REST API) or Sub-Plan E (Query Mode)
> **Revision Date**: 2026-01-21
> **Split From**: `sub-plan-C-vector-rag-revised.md`
> **Scope**: Two-tier classification, taxonomy manager, relationship manager, composite ranking

---

## Goal

Build the **intelligence layer** on top of Phase 3A's vector infrastructure, adding:

1. **Two-Tier Classification** - Fast embedding tier (<100ms) + LLM fallback (>90% accuracy)
2. **Human-Controlled Taxonomy** - Top 2 levels human-defined, AI-assisted deeper classification
3. **Pseudo-Graph Relationships** - 10 relationship types enabling 85% of graph DB capability
4. **Composite Ranking** - Multi-signal scoring (similarity + taxonomy + recency)
5. **Provenance & Audit** - Full tracking for no information loss

This phase activates the prepared fields in Phase 3A's payload schema.

---

## Prerequisites from Previous Phases

Before starting this phase, ensure:

**From Sub-Plan A:**

- All data models implemented (`ContentBlock`, `ExtractionSession`, etc.)
- Session management working
- Content extraction functional

**From Sub-Plan B:**

- `PlanningFlow` implemented (CleanupPlan → RoutingPlan generation)
- `CandidateFinder` interface defined
- Prompt contracts established

**From Sub-Plan 3A (Required):**

- Qdrant vector store working
- Embedding provider abstraction functional
- Library indexer operational
- `ContentPayload` schema with prepared fields for 3B
- `SemanticSearch` interface working
- `CandidateFinder` upgraded to vector similarity

---

## New Capabilities

| Capability                         | Description                                                |
| ---------------------------------- | ---------------------------------------------------------- |
| **Two-Tier Classification**        | Fast embedding tier + LLM fallback for confident placement |
| **Human-Controlled Taxonomy**      | Configurable hierarchy (YAML), top-2 levels human-defined  |
| **Taxonomy Centroids**             | Precomputed embeddings for fast-tier classification        |
| **Pseudo-Graph Relationships**     | 10 relationship types stored in Qdrant payloads            |
| **Relationship Traversal**         | Query related content, dependency chains                   |
| **Composite Ranking**              | Similarity + taxonomy overlap + recency scoring            |
| **Full Provenance Tracking**       | Audit trail for all content changes                        |
| **AI-Assisted Category Expansion** | LLM proposes new Level 3+ categories                       |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3B: INTELLIGENCE LAYER                              │
│                    (builds on Phase 3A infrastructure)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐      │
│  │  Content Block   │───▶│  Classification  │───▶│  Qdrant Store    │      │
│  │  (from Phase 1)  │    │  Service         │    │  (from 3A +      │      │
│  └──────────────────┘    │  ┌────────────┐  │    │   rich payloads) │      │
│                          │  │ Fast Tier  │  │    └────────┬─────────┘      │
│                          │  │ (embedding │  │             │                 │
│                          │  │  centroid) │  │             │                 │
│                          │  └─────┬──────┘  │             ▼                 │
│                          │        │         │    ┌──────────────────┐      │
│                          │  confidence      │    │  Relationship    │      │
│                          │  < threshold?    │    │  Manager         │      │
│                          │        │         │    │  (pseudo-graph)  │      │
│                          │        ▼         │    └──────────────────┘      │
│                          │  ┌────────────┐  │                               │
│                          │  │ LLM Tier   │  │    ┌──────────────────┐      │
│                          │  │ (fallback) │  │    │  Taxonomy        │      │
│                          │  └────────────┘  │    │  Manager         │      │
│                          └──────────────────┘    │  (YAML config)   │      │
│                                                  └──────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                         COMPOSITE RANKING                              │  │
│  │  Score = 0.6 * similarity + 0.25 * taxonomy_overlap + 0.15 * recency  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure (Additions to 3A)

```
src/
├── classification/
│   ├── __init__.py
│   ├── service.py                  # Two-tier classification orchestrator
│   ├── fast_tier.py                # Embedding centroid comparison
│   └── llm_tier.py                 # LLM fallback for low confidence
│
├── taxonomy/
│   ├── __init__.py
│   ├── manager.py                  # TaxonomyManager (load/validate/evolve)
│   ├── centroids.py                # Compute/cache taxonomy centroids
│   └── schema.py                   # Taxonomy Pydantic models
│
├── relationships/
│   ├── __init__.py
│   ├── manager.py                  # RelationshipManager (CRUD)
│   ├── types.py                    # 10 relationship type definitions
│   └── traversal.py                # Pseudo-graph traversal utilities
│
├── ranking/
│   ├── __init__.py
│   └── composite.py                # Composite ranking implementation
│
configs/
└── taxonomy.yaml                   # Human-controlled taxonomy configuration
```

---

## Implementation Details

### 1. Taxonomy Configuration (`configs/taxonomy.yaml`)

Human-controlled taxonomy with AI-assisted expansion:

```yaml
# configs/taxonomy.yaml
#
# TAXONOMY CONFIGURATION
# - Levels 1-2: Human-defined (modify this file)
# - Levels 3+: AI-assisted (proposals require approval)

version: '1.0'
last_updated: '2026-01-21'

# Classification settings
classification:
  fast_tier_threshold: 0.75 # Confidence threshold for fast tier
  llm_tier_threshold: 0.85 # Minimum confidence from LLM tier
  max_alternatives: 3 # Number of alternative paths to suggest

# Human-defined taxonomy (Levels 1-2)
taxonomy:
  - name: 'Agent-Systems'
    description: 'AI agent system documentation and specifications'
    children:
      - name: 'Research'
        description: 'Research agents for information gathering'
        allow_ai_subcategories: true
      - name: 'Feature-Planning'
        description: 'Agents for planning new features'
        allow_ai_subcategories: true
      - name: 'Implementation'
        description: 'Agents for code implementation'
        allow_ai_subcategories: true
      - name: 'Bug-Fixing-Verification'
        description: 'Agents for debugging and verification'
        allow_ai_subcategories: true

  - name: 'Blueprints'
    description: 'Reusable templates and patterns across domains'
    children:
      - name: 'Development'
        description: 'Software development patterns and practices'
        allow_ai_subcategories: true
      - name: 'AI-Agents'
        description: 'AI and agent-related blueprints'
        allow_ai_subcategories: true
      - name: 'Productivity'
        description: 'Productivity systems and workflows'
        allow_ai_subcategories: true
      - name: 'Learning'
        description: 'Learning methodologies and frameworks'
        allow_ai_subcategories: true
      - name: 'Business'
        description: 'Business strategies and processes'
        allow_ai_subcategories: true
      - name: 'Health'
        description: 'Health and wellness frameworks'
        allow_ai_subcategories: true
      - name: 'Mindset'
        description: 'Mental models and mindset frameworks'
        allow_ai_subcategories: true
      - name: 'Marketing'
        description: 'Marketing strategies and campaigns'
        allow_ai_subcategories: true

  - name: 'Features'
    description: 'Application feature documentation'
    children:
      - name: 'Core'
        description: 'Core application features'
        allow_ai_subcategories: true
      - name: 'Integrations'
        description: 'Third-party integrations'
        allow_ai_subcategories: true
      - name: 'UI-Components'
        description: 'User interface components'
        allow_ai_subcategories: true

# AI-proposed categories (populated dynamically, requires approval)
ai_proposed_categories: []

# Rules for AI category creation
ai_rules:
  require_approval_for_new_level2: true # New Level 2 always needs human approval
  auto_approve_level3_if_confident: true # Auto-approve Level 3+ if confidence > 0.9
  max_depth: 4 # Maximum taxonomy depth
```

---

### 2. Taxonomy Manager (`src/taxonomy/manager.py`)

```python
# src/taxonomy/manager.py

from pathlib import Path
from typing import Optional
from datetime import datetime
import yaml
from pydantic import BaseModel

from ..payloads.schema import TaxonomyPath


class TaxonomyNode(BaseModel):
    """A node in the taxonomy tree."""
    name: str
    description: str
    allow_ai_subcategories: bool = True
    children: list["TaxonomyNode"] = []


class TaxonomyConfig(BaseModel):
    """Parsed taxonomy configuration."""
    version: str
    classification: dict
    taxonomy: list[TaxonomyNode]
    ai_proposed_categories: list[dict] = []
    ai_rules: dict


class TaxonomyManager:
    """
    Manages the human-controlled taxonomy.

    Responsibilities:
    - Load/validate taxonomy from YAML
    - Check if paths are valid
    - Propose new categories (Level 3+)
    - Track AI-proposed categories for approval
    """

    def __init__(self, config_path: str = "configs/taxonomy.yaml"):
        self.config_path = Path(config_path)
        self.config: Optional[TaxonomyConfig] = None
        self._path_cache: set[str] = set()

    async def load(self) -> None:
        """Load taxonomy configuration from YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Taxonomy config not found: {self.config_path}")

        content = self.config_path.read_text()
        data = yaml.safe_load(content)

        # Parse taxonomy nodes recursively
        taxonomy_nodes = [
            self._parse_node(node) for node in data.get("taxonomy", [])
        ]

        self.config = TaxonomyConfig(
            version=data.get("version", "1.0"),
            classification=data.get("classification", {}),
            taxonomy=taxonomy_nodes,
            ai_proposed_categories=data.get("ai_proposed_categories", []),
            ai_rules=data.get("ai_rules", {}),
        )

        # Build path cache for fast validation
        self._build_path_cache()

    def _parse_node(self, data: dict) -> TaxonomyNode:
        """Recursively parse a taxonomy node."""
        children = [
            self._parse_node(child) for child in data.get("children", [])
        ]
        return TaxonomyNode(
            name=data["name"],
            description=data.get("description", ""),
            allow_ai_subcategories=data.get("allow_ai_subcategories", True),
            children=children,
        )

    def _build_path_cache(self) -> None:
        """Build a cache of all valid paths for fast lookup."""
        self._path_cache.clear()

        def traverse(nodes: list[TaxonomyNode], prefix: str = "") -> None:
            for node in nodes:
                path = f"{prefix}/{node.name}" if prefix else node.name
                self._path_cache.add(path)
                traverse(node.children, path)

        if self.config:
            traverse(self.config.taxonomy)

    def is_valid_path(self, path: str) -> bool:
        """Check if a taxonomy path exists."""
        return path in self._path_cache

    def get_valid_level2_paths(self) -> list[str]:
        """Get all valid Level 1/Level 2 paths."""
        paths = []
        if not self.config:
            return paths

        for l1 in self.config.taxonomy:
            for l2 in l1.children:
                paths.append(f"{l1.name}/{l2.name}")

        return paths

    def get_node_at_path(self, path: str) -> Optional[TaxonomyNode]:
        """Get the taxonomy node at a specific path."""
        if not self.config:
            return None

        parts = path.split("/")
        nodes = self.config.taxonomy

        for part in parts:
            found = None
            for node in nodes:
                if node.name == part:
                    found = node
                    nodes = node.children
                    break
            if not found:
                return None

        return found

    def can_create_subcategory(self, parent_path: str) -> bool:
        """Check if AI can create subcategories under this path."""
        node = self.get_node_at_path(parent_path)
        if not node:
            return False
        return node.allow_ai_subcategories

    async def propose_new_category(
        self,
        parent_path: str,
        name: str,
        description: str,
        confidence: float,
    ) -> dict:
        """
        Propose a new AI-generated category.

        Returns proposal dict for approval workflow.
        """
        if not self.can_create_subcategory(parent_path):
            raise ValueError(f"Cannot create subcategories under {parent_path}")

        depth = len(parent_path.split("/")) + 1
        max_depth = self.config.ai_rules.get("max_depth", 4) if self.config else 4

        if depth > max_depth:
            raise ValueError(f"Maximum taxonomy depth ({max_depth}) exceeded")

        proposal = {
            "parent_path": parent_path,
            "name": name,
            "description": description,
            "full_path": f"{parent_path}/{name}",
            "confidence": confidence,
            "depth": depth,
            "status": "pending",
            "proposed_at": datetime.utcnow().isoformat(),
        }

        # Auto-approve if rules allow and confidence is high
        auto_approve = (
            self.config
            and self.config.ai_rules.get("auto_approve_level3_if_confident", False)
            and depth >= 3
            and confidence > 0.9
        )

        if auto_approve:
            proposal["status"] = "auto_approved"
            await self._add_category_to_config(proposal)

        return proposal

    async def _add_category_to_config(self, proposal: dict) -> None:
        """Add an approved category to the taxonomy."""
        # This would update the YAML file and rebuild cache
        # Implementation depends on persistence strategy
        self._path_cache.add(proposal["full_path"])

    def get_classification_threshold(self, tier: str) -> float:
        """Get confidence threshold for a classification tier."""
        if not self.config:
            return 0.75 if tier == "fast" else 0.85
        return self.config.classification.get(f"{tier}_tier_threshold", 0.75)
```

---

### 3. Two-Tier Classification Service (`src/classification/service.py`)

```python
# src/classification/service.py

from typing import Optional
from dataclasses import dataclass

from ..taxonomy.manager import TaxonomyManager
from ..payloads.schema import (
    TaxonomyPath,
    ClassificationResult,
    ClassificationTier,
)
from .fast_tier import FastTierClassifier
from .llm_tier import LLMTierClassifier


@dataclass
class ClassificationRequest:
    """Request for content classification."""
    content: str
    content_type_hint: Optional[str] = None
    source_file_hint: Optional[str] = None


class ClassificationService:
    """
    Two-tier classification system.

    Tier 1 (Fast): Embedding centroid comparison
    - Latency: <100ms
    - Accuracy: 70-80%
    - Used when: confidence > threshold

    Tier 2 (LLM): Full reasoning with Claude
    - Latency: 2-5s
    - Accuracy: >90%
    - Used when: fast tier confidence < threshold
    """

    def __init__(
        self,
        taxonomy_manager: TaxonomyManager,
        fast_tier: FastTierClassifier,
        llm_tier: LLMTierClassifier,
    ):
        self.taxonomy = taxonomy_manager
        self.fast_tier = fast_tier
        self.llm_tier = llm_tier

    async def classify(
        self,
        request: ClassificationRequest,
    ) -> ClassificationResult:
        """
        Classify content using two-tier approach.

        1. Try fast tier (embedding centroid comparison)
        2. If confidence < threshold, escalate to LLM tier
        3. Return classification with confidence and reasoning
        """
        # Get threshold from taxonomy config
        fast_threshold = self.taxonomy.get_classification_threshold("fast")

        # Tier 1: Fast classification
        fast_result = await self.fast_tier.classify(
            content=request.content,
            valid_paths=self.taxonomy.get_valid_level2_paths(),
        )

        if fast_result.confidence >= fast_threshold:
            return ClassificationResult(
                taxonomy_path=fast_result.taxonomy_path,
                confidence=fast_result.confidence,
                tier_used=ClassificationTier.FAST,
                reasoning=None,
                alternatives=fast_result.alternatives,
            )

        # Tier 2: LLM classification (fallback)
        llm_result = await self.llm_tier.classify(
            content=request.content,
            taxonomy_config=self.taxonomy.config,
            fast_tier_suggestion=fast_result,
            content_type_hint=request.content_type_hint,
        )

        # Check if LLM wants to propose a new category
        if llm_result.proposed_new_category:
            proposal = await self.taxonomy.propose_new_category(
                parent_path=llm_result.proposed_new_category["parent_path"],
                name=llm_result.proposed_new_category["name"],
                description=llm_result.proposed_new_category["description"],
                confidence=llm_result.confidence,
            )
            llm_result.new_category_proposal = proposal

        return ClassificationResult(
            taxonomy_path=llm_result.taxonomy_path,
            confidence=llm_result.confidence,
            tier_used=ClassificationTier.LLM,
            reasoning=llm_result.reasoning,
            alternatives=llm_result.alternatives,
        )
```

---

### 4. Fast Tier Classifier (`src/classification/fast_tier.py`)

```python
# src/classification/fast_tier.py

from typing import Optional
from dataclasses import dataclass
import pickle
from pathlib import Path

from ..payloads.schema import TaxonomyPath, ClassificationResult, ClassificationTier


@dataclass
class FastTierResult:
    """Result from fast tier classification."""
    taxonomy_path: TaxonomyPath
    confidence: float
    alternatives: list[TaxonomyPath]


class FastTierClassifier:
    """
    Fast classification using embedding centroid comparison.

    Precomputes centroids for each taxonomy path and compares
    new content against them using cosine similarity.
    """

    def __init__(self, vector_store, centroid_cache_path: str = "cache/centroids.pkl"):
        self.store = vector_store
        self.cache_path = Path(centroid_cache_path)
        self.centroids: dict[str, list[float]] = {}

    async def load_centroids(self) -> None:
        """Load or compute taxonomy centroids."""
        if self.cache_path.exists():
            with open(self.cache_path, "rb") as f:
                self.centroids = pickle.load(f)
        else:
            await self.compute_centroids()

    async def compute_centroids(self) -> None:
        """
        Compute centroids for each taxonomy path from existing indexed content.

        A centroid is the average embedding of all content in that taxonomy path.
        """
        # Get all unique taxonomy paths from indexed content
        stats = self.store.get_stats()
        if stats["total_points"] == 0:
            return

        # Query for all content grouped by taxonomy path
        # This is a simplified version - production would use scroll/pagination
        results = await self.store.find_by_taxonomy_path("", n_results=10000)

        # Group embeddings by taxonomy path
        path_embeddings: dict[str, list[list[float]]] = {}
        for result in results:
            payload = result["payload"]
            path = payload.taxonomy.full_path if payload.taxonomy else ""
            if not path:
                continue

            # Get the embedding for this content
            # Note: In production, we'd store embeddings or re-fetch them
            # For now, we'll use a simplified approach
            if path not in path_embeddings:
                path_embeddings[path] = []

        # Compute centroid for each path (average of embeddings)
        for path, embeddings in path_embeddings.items():
            if embeddings:
                centroid = self._compute_centroid(embeddings)
                self.centroids[path] = centroid

        # Save to cache
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.centroids, f)

    def _compute_centroid(self, embeddings: list[list[float]]) -> list[float]:
        """Compute the centroid (average) of a list of embeddings."""
        if not embeddings:
            return []

        dim = len(embeddings[0])
        centroid = [0.0] * dim

        for emb in embeddings:
            for i, val in enumerate(emb):
                centroid[i] += val

        n = len(embeddings)
        return [c / n for c in centroid]

    async def classify(
        self,
        content: str,
        valid_paths: list[str],
    ) -> FastTierResult:
        """
        Classify content by comparing against taxonomy centroids.

        Returns the best matching path with confidence score.
        """
        # Get embedding for content
        embedding = await self.store.embeddings.embed_single(content)

        # Compare against centroids
        scores = []
        for path in valid_paths:
            if path in self.centroids:
                centroid = self.centroids[path]
                similarity = self._cosine_similarity(embedding, centroid)
                scores.append((path, similarity))

        if not scores:
            # No centroids available, return low confidence
            return FastTierResult(
                taxonomy_path=TaxonomyPath.from_path_string(valid_paths[0] if valid_paths else "General"),
                confidence=0.0,
                alternatives=[],
            )

        # Sort by similarity
        scores.sort(key=lambda x: x[1], reverse=True)

        best_path, best_score = scores[0]
        alternatives = [
            TaxonomyPath.from_path_string(path)
            for path, _ in scores[1:4]  # Top 3 alternatives
        ]

        return FastTierResult(
            taxonomy_path=TaxonomyPath.from_path_string(best_path),
            confidence=best_score,
            alternatives=alternatives,
        )

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
```

---

### 5. LLM Tier Classifier (`src/classification/llm_tier.py`)

```python
# src/classification/llm_tier.py

from typing import Optional
from dataclasses import dataclass, field
import json

from ..payloads.schema import TaxonomyPath
from ..sdk.client import SDKClient
from .fast_tier import FastTierResult


@dataclass
class LLMTierResult:
    """Result from LLM tier classification."""
    taxonomy_path: TaxonomyPath
    confidence: float
    reasoning: str
    alternatives: list[TaxonomyPath]
    proposed_new_category: Optional[dict] = None
    new_category_proposal: Optional[dict] = None


CLASSIFICATION_PROMPT = """
You are classifying content into a knowledge library taxonomy.

## Taxonomy Structure

{taxonomy_structure}

## Content to Classify

```

{content}

````

## Fast Tier Suggestion (may be incorrect)

Path: {fast_suggestion_path}
Confidence: {fast_suggestion_confidence}

## Your Task

1. Determine the best taxonomy path for this content
2. If no existing path fits well, you may propose a NEW Level 3+ category
3. Provide your reasoning

## Response Format

```json
{{
  "taxonomy_path": "Level1/Level2/Level3",
  "confidence": 0.95,
  "reasoning": "Brief explanation of why this path is appropriate",
  "alternatives": ["Alternative/Path/1", "Alternative/Path/2"],
  "propose_new_category": null
}}
````

If proposing a new category:

```json
{{
  "taxonomy_path": "Blueprints/Development/NewCategory",
  "confidence": 0.9,
  "reasoning": "No existing category covers X, proposing NewCategory",
  "alternatives": [],
  "propose_new_category": {{
    "parent_path": "Blueprints/Development",
    "name": "NewCategory",
    "description": "Description of what belongs here"
  }}
}}
```

IMPORTANT: Only propose new categories at Level 3 or deeper. Levels 1-2 are human-controlled.
"""

class LLMTierClassifier:
"""
LLM-based classification for cases where fast tier has low confidence.

    Uses Claude to:
    1. Classify content with full reasoning
    2. Propose new taxonomy categories when needed
    """

    def __init__(self, sdk_client: SDKClient):
        self.sdk = sdk_client

    async def classify(
        self,
        content: str,
        taxonomy_config,
        fast_tier_suggestion: FastTierResult,
        content_type_hint: Optional[str] = None,
    ) -> LLMTierResult:
        """
        Classify content using LLM reasoning.
        """
        # Format taxonomy structure for prompt
        taxonomy_structure = self._format_taxonomy(taxonomy_config)

        prompt = CLASSIFICATION_PROMPT.format(
            taxonomy_structure=taxonomy_structure,
            content=content[:2000],  # Truncate for context limits
            fast_suggestion_path=fast_tier_suggestion.taxonomy_path.full_path,
            fast_suggestion_confidence=fast_tier_suggestion.confidence,
        )

        response = await self.sdk.query(prompt)

        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            # Fallback to fast tier suggestion
            return LLMTierResult(
                taxonomy_path=fast_tier_suggestion.taxonomy_path,
                confidence=fast_tier_suggestion.confidence,
                reasoning="LLM classification failed, using fast tier result",
                alternatives=fast_tier_suggestion.alternatives,
            )

        return LLMTierResult(
            taxonomy_path=TaxonomyPath.from_path_string(data["taxonomy_path"]),
            confidence=data.get("confidence", 0.8),
            reasoning=data.get("reasoning", ""),
            alternatives=[
                TaxonomyPath.from_path_string(p)
                for p in data.get("alternatives", [])
            ],
            proposed_new_category=data.get("propose_new_category"),
        )

    def _format_taxonomy(self, config) -> str:
        """Format taxonomy config for the prompt."""
        if not config:
            return "(No taxonomy configured)"

        lines = []

        def traverse(nodes, prefix=""):
            for node in nodes:
                path = f"{prefix}/{node.name}" if prefix else node.name
                lines.append(f"- {path}: {node.description}")
                traverse(node.children, path)

        traverse(config.taxonomy)
        return "\n".join(lines)

````

---

### 6. Relationship Manager (`src/relationships/manager.py`)

```python
# src/relationships/manager.py

from typing import Optional
from datetime import datetime

from ..vector.store import QdrantVectorStore
from ..payloads.schema import (
    ContentPayload,
    Relationship,
    RelationshipType,
    AuditEntry,
)


class RelationshipManager:
    """
    Manages pseudo-graph relationships stored in Qdrant payloads.

    Supports:
    - Creating/updating/deleting relationships
    - Bidirectional relationship tracking
    - Relationship traversal queries
    """

    def __init__(self, vector_store: QdrantVectorStore):
        self.store = vector_store

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        metadata: Optional[dict] = None,
        bidirectional: bool = False,
    ) -> None:
        """
        Create a relationship between two content items.

        Args:
            source_id: ID of the source content
            target_id: ID of the target content
            relationship_type: Type of relationship
            metadata: Optional relationship metadata
            bidirectional: If True, create inverse relationship too
        """
        # Add relationship to source
        await self._add_relationship_to_content(
            content_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or {},
        )

        # Add inverse relationship if bidirectional
        if bidirectional:
            inverse_type = self._get_inverse_type(relationship_type)
            if inverse_type:
                await self._add_relationship_to_content(
                    content_id=target_id,
                    target_id=source_id,
                    relationship_type=inverse_type,
                    metadata=metadata or {},
                )

    async def _add_relationship_to_content(
        self,
        content_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        metadata: dict,
    ) -> None:
        """Add a relationship to a content item's payload."""
        # Retrieve current content
        results = self.store.client.retrieve(
            collection_name=self.store.COLLECTION_NAME,
            ids=[content_id],
            with_payload=True,
        )

        if not results:
            raise ValueError(f"Content {content_id} not found")

        payload = ContentPayload.from_qdrant_payload(results[0].payload)

        # Check for duplicate
        existing = [
            r for r in payload.relationships
            if r.target_id == target_id and r.relationship_type == relationship_type
        ]
        if existing:
            return  # Relationship already exists

        # Add new relationship
        payload.relationships.append(Relationship(
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata,
        ))

        # Update audit trail
        payload.audit_trail.append(AuditEntry(
            action="relationship_added",
            details={
                "target_id": target_id,
                "type": relationship_type.value,
            },
        ))
        payload.updated_at = datetime.utcnow()

        # Update in Qdrant
        self.store.client.set_payload(
            collection_name=self.store.COLLECTION_NAME,
            payload=payload.to_qdrant_payload(),
            points=[content_id],
        )

    def _get_inverse_type(
        self,
        relationship_type: RelationshipType,
    ) -> Optional[RelationshipType]:
        """Get the inverse relationship type for bidirectional relationships."""
        inverses = {
            RelationshipType.IMPLEMENTS: None,  # One-way
            RelationshipType.DEPENDS_ON: None,  # One-way
            RelationshipType.RELATES_TO: RelationshipType.RELATES_TO,  # Symmetric
            RelationshipType.REFERENCES: None,  # One-way
            RelationshipType.PRODUCES: RelationshipType.CONSUMES,
            RelationshipType.CONSUMES: RelationshipType.PRODUCES,
            RelationshipType.TRIGGERS: None,  # One-way
            RelationshipType.SUPERSEDES: None,  # One-way (inverse would be "superseded_by")
            RelationshipType.DERIVES_FROM: None,  # One-way
            RelationshipType.MERGES: None,  # One-way
        }
        return inverses.get(relationship_type)

    async def get_related_content(
        self,
        content_id: str,
        relationship_type: Optional[RelationshipType] = None,
    ) -> list[dict]:
        """
        Get all content related to a given item.

        Optionally filter by relationship type.
        """
        if relationship_type:
            return await self.store.search_by_relationship(
                content_id=content_id,
                relationship_type=relationship_type,
            )
        return await self._get_all_related(content_id)

    async def _get_all_related(self, content_id: str) -> list[dict]:
        """Get all related content regardless of relationship type."""
        results = self.store.client.retrieve(
            collection_name=self.store.COLLECTION_NAME,
            ids=[content_id],
            with_payload=True,
        )

        if not results:
            return []

        payload = ContentPayload.from_qdrant_payload(results[0].payload)
        related_ids = [r.target_id for r in payload.relationships]

        if not related_ids:
            return []

        related = self.store.client.retrieve(
            collection_name=self.store.COLLECTION_NAME,
            ids=related_ids,
            with_payload=True,
        )

        return [
            {
                "id": point.id,
                "payload": ContentPayload.from_qdrant_payload(point.payload),
                "relationship": next(
                    r for r in payload.relationships if r.target_id == point.id
                ),
            }
            for point in related
        ]

    async def remove_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
    ) -> None:
        """Remove a specific relationship."""
        results = self.store.client.retrieve(
            collection_name=self.store.COLLECTION_NAME,
            ids=[source_id],
            with_payload=True,
        )

        if not results:
            return

        payload = ContentPayload.from_qdrant_payload(results[0].payload)

        # Remove matching relationship
        payload.relationships = [
            r for r in payload.relationships
            if not (r.target_id == target_id and r.relationship_type == relationship_type)
        ]

        # Update audit trail
        payload.audit_trail.append(AuditEntry(
            action="relationship_removed",
            details={
                "target_id": target_id,
                "type": relationship_type.value,
            },
        ))
        payload.updated_at = datetime.utcnow()

        # Update in Qdrant
        self.store.client.set_payload(
            collection_name=self.store.COLLECTION_NAME,
            payload=payload.to_qdrant_payload(),
            points=[source_id],
        )

    async def find_dependency_chain(
        self,
        content_id: str,
        max_depth: int = 5,
    ) -> list[list[str]]:
        """
        Find all dependency chains from a content item.

        Useful for impact analysis (what breaks if I change this?).
        """
        chains = []
        visited = set()

        async def traverse(current_id: str, chain: list[str], depth: int):
            if depth > max_depth or current_id in visited:
                return

            visited.add(current_id)
            new_chain = chain + [current_id]

            dependents = await self.store.search_by_relationship(
                content_id=current_id,
                relationship_type=RelationshipType.DEPENDS_ON,
            )

            if not dependents:
                chains.append(new_chain)
                return

            for dep in dependents:
                await traverse(dep["id"], new_chain, depth + 1)

        await traverse(content_id, [], 0)
        return chains

    async def find_implementation_chain(
        self,
        blueprint_id: str,
    ) -> list[dict]:
        """
        Find all implementations of a blueprint.

        Useful for tracking blueprint usage.
        """
        return await self.store.search_by_relationship(
            content_id=blueprint_id,
            relationship_type=RelationshipType.IMPLEMENTS,
        )
````

---

### 7. Composite Ranking (`src/ranking/composite.py`)

```python
# src/ranking/composite.py

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class RankedResult:
    """A search result with composite ranking score."""
    content_id: str
    vector_similarity: float
    taxonomy_overlap: float
    recency_score: float
    composite_score: float
    payload: dict


class CompositeRanker:
    """
    Composite ranking combining multiple signals.

    Score = w1 * vector_similarity + w2 * taxonomy_overlap + w3 * recency

    Default weights based on research:
    - Vector similarity: 0.6 (primary signal)
    - Taxonomy overlap: 0.25 (structural relevance)
    - Recency: 0.15 (freshness)
    """

    def __init__(
        self,
        weight_similarity: float = 0.6,
        weight_taxonomy: float = 0.25,
        weight_recency: float = 0.15,
    ):
        self.w_sim = weight_similarity
        self.w_tax = weight_taxonomy
        self.w_rec = weight_recency

    def rank(
        self,
        results: list[dict],
        query_taxonomy: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> list[RankedResult]:
        """
        Apply composite ranking to search results.

        Args:
            results: Raw search results with scores and payloads
            query_taxonomy: Taxonomy path of the query context (for overlap)
            reference_time: Reference time for recency scoring (default: now)

        Returns:
            Results sorted by composite score
        """
        reference_time = reference_time or datetime.utcnow()
        ranked = []

        for r in results:
            payload = r["payload"]

            # Vector similarity (already computed)
            vector_sim = r["score"]

            # Taxonomy overlap
            result_taxonomy = payload.taxonomy.full_path if payload.taxonomy else ""
            tax_overlap = self._taxonomy_overlap(query_taxonomy, result_taxonomy)

            # Recency score
            updated_at = payload.updated_at
            recency = self._recency_score(updated_at, reference_time)

            # Composite score
            composite = (
                self.w_sim * vector_sim +
                self.w_tax * tax_overlap +
                self.w_rec * recency
            )

            ranked.append(RankedResult(
                content_id=r["id"],
                vector_similarity=vector_sim,
                taxonomy_overlap=tax_overlap,
                recency_score=recency,
                composite_score=composite,
                payload=payload,
            ))

        # Sort by composite score
        ranked.sort(key=lambda x: x.composite_score, reverse=True)
        return ranked

    def _taxonomy_overlap(
        self,
        query_path: Optional[str],
        result_path: str,
    ) -> float:
        """
        Calculate taxonomy path overlap.

        Returns 1.0 for exact match, 0.5 for same Level 1, etc.
        """
        if not query_path or not result_path:
            return 0.0

        query_parts = query_path.split("/")
        result_parts = result_path.split("/")

        matching = 0
        for i, (q, r) in enumerate(zip(query_parts, result_parts)):
            if q == r:
                matching += 1
            else:
                break

        if matching == 0:
            return 0.0

        # Weight deeper matches more
        max_depth = max(len(query_parts), len(result_parts))
        return matching / max_depth

    def _recency_score(
        self,
        updated_at: datetime,
        reference_time: datetime,
    ) -> float:
        """
        Calculate recency score (exponential decay).

        Returns 1.0 for today, ~0.5 for 30 days ago, ~0.1 for 90 days ago.
        """
        if not updated_at:
            return 0.5  # Unknown age = neutral

        days_old = (reference_time - updated_at).days
        if days_old < 0:
            days_old = 0

        # Exponential decay with half-life of 30 days
        import math
        half_life = 30
        return math.exp(-0.693 * days_old / half_life)
```

---

### 8. Configuration Updates (Phase 3B additions)

Add to `configs/settings.yaml`:

```yaml
# configs/settings.yaml (Phase 3B additions)

# Classification settings
classification:
  fast_tier_threshold: 0.75
  llm_tier_threshold: 0.85
  enable_llm_fallback: true
  centroid_cache_path: cache/centroids.pkl

# Composite ranking weights
ranking:
  weight_similarity: 0.6
  weight_taxonomy: 0.25
  weight_recency: 0.15

# Taxonomy configuration path
taxonomy:
  config_path: configs/taxonomy.yaml
```

---

## Relationship Types Reference

| Type             | Direction                 | Metadata                                            | Use Case                              |
| ---------------- | ------------------------- | --------------------------------------------------- | ------------------------------------- |
| **IMPLEMENTS**   | Blueprint → Agent/Feature | `implementation_status`, `adaptation_notes`         | Connect blueprints to implementations |
| **DEPENDS_ON**   | Any → Any                 | `dependency_type` (hard/soft), `version_constraint` | Track dependencies                    |
| **RELATES_TO**   | Bidirectional             | `relationship_strength`, `description`              | General semantic links                |
| **REFERENCES**   | Any → Any                 | `reference_type` (citation/example), `context`      | Citations, see-also                   |
| **PRODUCES**     | Agent → Content           | `output_format`, `production_frequency`             | Agent outputs                         |
| **CONSUMES**     | Agent → Content           | `input_format`, `required`                          | Agent inputs                          |
| **TRIGGERS**     | Agent → Agent             | `trigger_condition`, `delay`                        | Workflow chains                       |
| **SUPERSEDES**   | New → Old                 | `supersede_reason`, `breaking_changes`              | Version management                    |
| **DERIVES_FROM** | Content → Source          | `derivation_method`, `information_loss`             | Provenance                            |
| **MERGES**       | Result → Sources          | `merge_strategy`, `conflicts_resolved`              | Consolidation                         |

---

## Acceptance Criteria

### Classification

- [ ] Two-tier classification working (fast tier <100ms)
- [ ] LLM fallback activates when confidence < threshold
- [ ] Classification confidence scores are meaningful
- [ ] AI can propose new Level 3+ categories
- [ ] Human approval required for new Level 2 categories

### Taxonomy

- [ ] Taxonomy manager loads/validates YAML configuration
- [ ] Path validation works correctly
- [ ] AI-proposed categories tracked for approval
- [ ] Auto-approve option works for high-confidence Level 3+

### Relationships

- [ ] All 10 relationship types supported
- [ ] Bidirectional relationships work correctly
- [ ] Relationship traversal queries work
- [ ] Dependency chain analysis functional
- [ ] Audit trail tracks relationship changes

### Ranking

- [ ] Composite ranking improves relevance over pure vector similarity
- [ ] Taxonomy overlap scoring works correctly
- [ ] Recency scoring applies exponential decay
- [ ] Weights are configurable

### Integration

- [ ] Payload schema fields activated (taxonomy, classification, relationships)
- [ ] Classification integrates with indexing pipeline
- [ ] Relationships queryable via search interface
- [ ] Phase 3A interfaces still work (backward compatible)

---

## Notes for Downstream Session

1. **Centroid Computation**: Run centroid computation after initial indexing is complete
2. **LLM Tier Cost**: Monitor LLM tier usage - it's slower and costs more
3. **Taxonomy Evolution**: New AI-proposed categories appear in `ai_proposed_categories` for review
4. **Relationship Consistency**: When deleting content, clean up relationships pointing to it
5. **Phase 4 Integration**: REST API will expose classification and relationship endpoints
6. **Phase 5 Query Mode**: This intelligence layer powers semantic queries with relationship traversal

---

_End of Sub-Plan 3B (Intelligence Layer)_

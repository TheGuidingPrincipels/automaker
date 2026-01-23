# Sub-Plan A: Core Engine (Phase 1)

> **Master Plan Reference**: `knowledge-library-master-plan.md`
> **Execution Location**: This repository (`Info-Adding-Sec.` → to be renamed `knowledge-library`)
> **Dependencies**: None (this is the foundation)
> **Next Phase**: Sub-Plan B (Smart Routing)

---

## Goal

Build a working **SDK-driven** extraction engine that:

1. deterministically parses a source markdown document into blocks,
2. uses Claude Code SDK to propose **cleanup/structuring decisions** (with explicit user approval),
3. uses Claude Code SDK to propose a **complete routing plan** with top-3 destination options per block,
4. executes the approved plan automatically with **100% write verification**, then
5. deletes the source document only after verification succeeds.

The primary UX is the Web UI (Phase 5) with an embedded Claude Code chat + decision columns. CLI is optional dev tooling only (not the product path).

---

## Context

### System Overview

The Knowledge Library System ("The Reliable Librarian") enables users to:

1. **Input Mode**: Extract information from raw documents into organized, persistent markdown files
2. **Output Mode**: Query and retrieve information from the library using natural language

This phase focuses on the **foundational infrastructure** for Input Mode.

### Core Principles (Non-Negotiable)

| Principle                         | Description                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **100% Information Preservation** | No content lost during extraction, routing, or merging                                                                                 |
| **Complete Extraction**           | Source document fully emptied into library → can be deleted                                                                            |
| **User Verification**             | Cleanup (discard) and routing always require explicit user decisions; merges (refinement only) show triple-view                        |
| **All Blocks Resolved**           | Cannot complete session until every block has a destination                                                                            |
| **Persistent Storage**            | Markdown files are source of truth, kept forever                                                                                       |
| **Category Organization**         | Library organized into category subfolders                                                                                             |
| **No Silent Discard**             | Nothing is removed unless the user explicitly approves discard (in UI)                                                                 |
| **Code Blocks Are Byte-Strict**   | Fenced code blocks must be written byte-for-byte identical (no formatting changes)                                                     |
| **STRICT Preserves Words**        | In STRICT mode, prose may change whitespace/line-wrapping, but words/sentences must remain identical (verified via canonical checksum) |
| **Checksum Verification**         | Every write operation is verified by reading back and comparing checksums                                                              |
| **Single Approval**               | User approves the complete routing plan once, then execution is automatic                                                              |
| **Fail-Fast**                     | If any integrity check fails, stop immediately and report                                                                              |
| **Content Modes**                 | STRICT (no merges/rewrites; preserve words) or REFINEMENT (optional merges/rewrites with triple-view and verification)                 |

---

## Deliverables

### 1. Project Structure

Create the following directory structure:

```
knowledge-library/                    # This repository (root)
├── src/
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── content.py                # ContentBlock, SourceDocument
│   │   ├── session.py                # ExtractionSession, SessionPhase
│   │   ├── cleanup_plan.py           # CleanupPlan (user-approved discard + structuring)
│   │   ├── routing_plan.py           # RoutingPlan (top-3 options + dispositions)
│   │   └── library.py                # LibraryFile, Category
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── parser.py                 # Markdown parsing, block extraction
│   │   ├── canonicalize.py           # STRICT prose canonicalization rules
│   │   └── checksums.py              # Checksums (exact + canonical)
│   │
│   ├── sdk/
│   │   ├── __init__.py
│   │   ├── client.py                 # Claude Code SDK wrapper
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── cleanup_mode.py       # System prompt for cleanup/structuring plan
│   │       ├── routing_mode.py       # System prompt for routing plan generation
│   │       └── output_mode.py        # System prompt for queries (Phase 6)
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── writer.py                 # File creation, content insertion
│   │   └── markers.py                # Tracking markers for idempotency
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py                # Session lifecycle management
│   │   └── storage.py                # Session persistence (JSON → future DB)
│   │
│   └── library/
│       ├── __init__.py
│       ├── scanner.py                # Scan library structure
│       ├── manifest.py               # Library manifest for constrained routing
│       └── categories.py             # Category management
│
├── library/                          # Knowledge storage (markdown files)
│   ├── _index.yaml                   # Category definitions
│   └── .gitkeep
│
├── sessions/                         # Session state persistence
│   └── .gitkeep
│
├── configs/
│   ├── settings.yaml                 # Application settings
│   └── prompts.yaml                  # Prompt templates (optional)
│
├── tests/
│   ├── __init__.py
│   ├── test_extraction.py
│   ├── test_execution.py
│   ├── test_session.py
│   └── fixtures/
│       ├── sample_source.md
│       └── sample_library/
│
├── pyproject.toml
├── README.md
└── CLAUDE.md                         # Instructions for Claude Code
```

---

### 2. Core Data Models

#### 2.1 Content Models (`src/models/content.py`)

```python
# src/models/content.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    HEADER_SECTION = "header_section"
    PARAGRAPH = "paragraph"
    LIST = "list"
    CODE_BLOCK = "code_block"
    BLOCKQUOTE = "blockquote"
    TABLE = "table"


class ContentBlock(BaseModel):
    """
    A semantic unit of content extracted from a source document.

    STRICT rules:
    - Code blocks are byte-for-byte strict (exact checksum must match on read-back).
    - Prose blocks preserve words/sentences; whitespace/line wrapping may change.
      This is enforced via a canonical form + canonical checksum.
    """

    id: str                              # e.g., "block_001"
    block_type: BlockType

    # Content
    content: str                         # Exact extracted content (verbatim)
    content_canonical: str               # Canonicalized form for STRICT prose verification
    canonicalization_version: str = "v1"

    # Source tracking
    source_file: str
    source_line_start: int
    source_line_end: int
    heading_path: list[str] = Field(default_factory=list)  # e.g., ["STEP 2", "Alignment Validation", "Critical Findings"]

    # Integrity (all stored as 16-char SHA-256 prefixes for readability; full hash optional later)
    checksum_exact: str = Field(min_length=16, max_length=16)
    checksum_canonical: str = Field(min_length=16, max_length=16)

    # Pipeline status
    integrity_verified: bool = False      # True after successful write verification
    is_executed: bool = False             # Has been written to library

    @classmethod
    def from_source(cls, content: str, **kwargs) -> "ContentBlock":
        """Create block with automatic checksums (exact + canonical)."""
        import hashlib
        canonical = kwargs.pop("content_canonical")
        return cls(
            content=content,
            checksum_exact=hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            checksum_canonical=hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16],
            content_canonical=canonical,
            **kwargs
        )


class SourceDocument(BaseModel):
    """A document being processed for extraction."""

    file_path: str
    checksum_exact: str               # For detecting changes (exact bytes)
    total_blocks: int
    blocks: list[ContentBlock]
```

#### 2.2 Session Models (`src/models/session.py`)

```python
# src/models/session.py

from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from .content import SourceDocument
from .content_mode import ContentMode
from .cleanup_plan import CleanupPlan
from .routing_plan import RoutingPlan


class SessionPhase(str, Enum):
    INITIALIZED = "initialized"           # Session created
    PARSING = "parsing"                   # Reading file and extracting blocks
    CLEANUP_PLAN_READY = "cleanup_plan_ready"   # Cleanup/structuring plan generated
    ROUTING_PLAN_READY = "routing_plan_ready"   # Complete routing plan generated
    AWAITING_APPROVAL = "awaiting_approval"     # User reviewing cleanup + routing
    READY_TO_EXECUTE = "ready_to_execute"       # All blocks resolved + plan approved
    EXECUTING = "executing"                     # Writing blocks to library
    VERIFYING = "verifying"                     # Post-execution checksum verification
    COMPLETED = "completed"                     # All blocks written and verified
    ERROR = "error"                             # Something went wrong


class ExtractionSession(BaseModel):
    """
    Complete session state for extracting a source document into the library.
    Designed to be serializable and resumable.
    """

    id: str
    created_at: datetime
    updated_at: datetime
    phase: SessionPhase

    # Source document
    source: Optional[SourceDocument] = None

    # Library context
    library_path: str
    library_manifest: Optional[dict] = None      # Snapshot used to constrain routing (model later)

    # Content mode (STRICT or REFINEMENT)
    content_mode: ContentMode = ContentMode.STRICT

    # AI-proposed plans (explicitly user-approved)
    cleanup_plan: Optional[CleanupPlan] = None
    routing_plan: Optional[RoutingPlan] = None

    # Conversation state
    pending_questions: list[dict] = Field(default_factory=list)
    conversation_history: list[dict] = Field(default_factory=list)

    # Execution tracking
    execution_log: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    # Completion
    source_deleted: bool = False

    @property
    def can_execute(self) -> bool:
        """
        Can execute only when:
        - source is parsed into blocks,
        - cleanup decisions are complete (every block kept or explicitly discarded),
        - routing decisions are complete (every kept block has a selected destination),
        - routing plan is approved.
        """
        if not self.source or not self.routing_plan:
            return False
        if not self.routing_plan.approved:
            return False
        return self.routing_plan.all_blocks_resolved
```

#### 2.3 Cleanup Plan Models (`src/models/cleanup_plan.py`)

Cleanup happens before routing. The model may propose discard candidates and optional structuring suggestions, but **nothing is discarded unless the user explicitly approves**.

```python
# src/models/cleanup_plan.py

from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CleanupDisposition(str, Enum):
    KEEP = "keep"
    DISCARD = "discard"   # Only allowed with explicit user approval


class CleanupItem(BaseModel):
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str

    # Model suggestion (never executed automatically)
    suggested_disposition: str = CleanupDisposition.KEEP
    suggestion_reason: str = ""

    # User decision
    final_disposition: Optional[str] = None  # "keep" or "discard"


class CleanupPlan(BaseModel):
    session_id: str
    source_file: str
    created_at: datetime = Field(default_factory=datetime.now)

    items: List[CleanupItem] = Field(default_factory=list)

    approved: bool = False
    approved_at: Optional[datetime] = None

    @property
    def all_decided(self) -> bool:
        return all(i.final_disposition in (CleanupDisposition.KEEP, CleanupDisposition.DISCARD) for i in self.items)
```

#### 2.4 Library Models (`src/models/library.py`)

```python
# src/models/library.py

from pydantic import BaseModel, Field


class LibraryFile(BaseModel):
    """
    Represents a file in the library.
    """

    path: str                         # Relative to library root
    category: str                     # Parent category
    title: str
    sections: list[str] = Field(default_factory=list)
    last_modified: str
    block_count: int = 0              # Number of routed blocks


class LibraryCategory(BaseModel):
    """
    A category (folder) in the library.
    """

    name: str
    path: str                         # Relative to library root
    description: str
    files: list[LibraryFile] = Field(default_factory=list)
    subcategories: list["LibraryCategory"] = Field(default_factory=list)
```

---

### 3. SDK-Driven Ingestion Interface (Claude Code SDK)

This application is **not** driven by a CLI in production. It is driven by:

1. Claude Code SDK (for cleanup + routing plan generation), and
2. the Web UI + API (Phase 4/5) for user decisions (click-to-accept, no typing required).

Phase 1 provides a backend orchestration surface in `SessionManager` that the API/UI can call later:

- `create_session(source_path, library_path)` → parse source into blocks + persist session
- `build_library_manifest(library_path)` → produce a manifest (files + sections + summaries)
- `generate_cleanup_plan(session_id)` → AI proposes discard candidates (no automatic discard)
- `set_cleanup_decision(session_id, block_id, keep|discard)` → user decision
- `generate_routing_plan(session_id)` → AI proposes top-3 destinations per kept block
- `select_destination(session_id, block_id, option_index|custom_selection)` → user click selection
- `approve_plan(session_id)` → single final approval gate (only if all blocks resolved)
- `execute_session(session_id)` → deterministic writer + read-back verification + report
- `delete_source(session_id)` → only after 100% verification success

Claude Code SDK usage is limited to structured JSON outputs for plans; **all file writes are performed by our engine** with checksum verification.

---

### 4. Configuration

#### 4.1 Settings File (`configs/settings.yaml`)

```yaml
# configs/settings.yaml

# Library settings
library:
  path: ./library
  index_file: _index.yaml

# Session settings
sessions:
  path: ./sessions
  auto_save: true

# SDK settings
sdk:
  # Claude Code runtime model to use for this repository/session.
  # Verified: Claude Code supports `--model ...` (e.g., `claude --model opus`).
  # Not yet verified (skip for now): programmatic temperature/max_tokens via Claude Code SDK.
  model: claude-opus-4-5-20251101
  temperature: 0 # TODO(verify): only enforce if supported by Claude Code/SDK
  max_turns: 6

  # Auth: use Claude Code subscription/auth token via environment.
  # TODO(verify): confirm the correct env var name in current Claude Code docs.
  auth_token_env_var: ANTHROPIC_AUTH_TOKEN

# Safety settings
safety:
  require_all_resolved: true
  verify_before_execute: true
  verify_after_execute: true
  backup_before_write: true
  require_explicit_discard: true # No silent deletion of content blocks
  forbid_merges_in_strict: true # No rewrites/merges in STRICT mode

# Extraction settings
extraction:
  confidence_threshold: 0.8 # Below this, ask user
  max_block_size: 5000 # Characters
  preserve_code_blocks: true

# Structuring/Cleanup settings (Phase 1)
cleanup:
  default_disposition: keep # keep unless user explicitly discards
  allow_split_suggestions: true # model may suggest splitting oversized/mixed blocks
  allow_format_suggestions: true # model may suggest safe formatting changes (no word changes)

# STRICT verification settings (Phase 1)
strict:
  canonicalization_version: v1
  code_blocks_byte_strict: true

# Content handling settings
content:
  default_mode: strict # "strict" or "refinement"

# Source deletion settings
source:
  deletion_behavior: confirm # "auto", "confirm", or "never"
```

#### 4.2 Configuration Loader (`src/config.py`)

```python
# src/config.py

from typing import Optional
import yaml
from pydantic import BaseModel, Field
import anyio


class LibraryConfig(BaseModel):
    path: str = "./library"
    index_file: str = "_index.yaml"


class SessionsConfig(BaseModel):
    path: str = "./sessions"
    auto_save: bool = True


class SDKConfig(BaseModel):
    model: str = "claude-opus-4-5-20251101"
    temperature: float = 0.0           # TODO(verify): only enforce if supported by Claude Code/SDK
    max_turns: int = 6
    auth_token_env_var: str = "ANTHROPIC_AUTH_TOKEN"


class SafetyConfig(BaseModel):
    require_all_resolved: bool = True
    verify_before_execute: bool = True
    verify_after_execute: bool = True
    backup_before_write: bool = True
    require_explicit_discard: bool = True
    forbid_merges_in_strict: bool = True


class ExtractionConfig(BaseModel):
    confidence_threshold: float = 0.8
    max_block_size: int = 5000
    preserve_code_blocks: bool = True


class CleanupConfig(BaseModel):
    default_disposition: str = "keep"
    allow_split_suggestions: bool = True
    allow_format_suggestions: bool = True


class StrictConfig(BaseModel):
    canonicalization_version: str = "v1"
    code_blocks_byte_strict: bool = True


class Config(BaseModel):
    library: LibraryConfig = Field(default_factory=LibraryConfig)
    sessions: SessionsConfig = Field(default_factory=SessionsConfig)
    sdk: SDKConfig = Field(default_factory=SDKConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)
    strict: StrictConfig = Field(default_factory=StrictConfig)

    @property
    def library_path(self) -> str:
        return self.library.path


async def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from YAML file (async)."""
    path = anyio.Path(config_path or "configs/settings.yaml")
    if await path.exists():
        text = await path.read_text()
        data = yaml.safe_load(text)
        return Config(**data) if data else Config()

    return Config()


async def get_config() -> Config:
    """Get the global configuration instance (async)."""
    return await load_config()
```

---

### 5. Python Project Configuration (`pyproject.toml`)

```toml
[project]
name = "knowledge-library"
version = "0.1.0"
description = "Personal Knowledge Library System - The Reliable Librarian"
requires-python = ">=3.11"
dependencies = [
    "claude-code-sdk>=0.0.23",
    "anyio>=4.0.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

### 6. Additional Components to Implement

#### 6.1 Extraction Parser (`src/extraction/parser.py`)

Implement markdown parsing to extract content blocks:

- Parse headers and build a `heading_path` stack (e.g., `["STEP 2", "Alignment Validation", "Critical Findings"]`)
- Split blocks at `###` by default (configurable), with edge-case handling for mixed documents
- Treat fenced code blocks as **atomic** blocks (`block_type=CODE_BLOCK`) with byte-accurate extraction
- Extract paragraphs, lists, blockquotes, tables as prose blocks
- Track line numbers for source mapping
- Generate unique block IDs

#### 6.2 Checksums (`src/extraction/checksums.py`)

Implement content integrity verification:

- Generate 16-character SHA-256 prefixes for:
  - `checksum_exact` (exact extracted bytes)
  - `checksum_canonical` (STRICT prose canonical form)
- Canonicalization rules:
  - Prose: normalize whitespace/line wraps/blank lines but preserve words/sentences
  - Code: canonical form == exact form (byte-strict)
- Verify checksums are stable across pipeline steps

#### 6.3 Session Manager (`src/session/manager.py`)

Implement session lifecycle:

- Create new sessions with unique IDs
- Load/save sessions to JSON files
- Manage session phase transitions
- Generate AI plans (cleanup + routing) and persist them into session state
- Record user decisions (discard/keep, per-block destination selection) without requiring user typing
- Enforce gates:
  - no execute until all blocks are `keep+selected_destination` or `discard (approved)`
  - no source deletion until 100% write verification succeeds

#### 6.4 Session Storage (`src/session/storage.py`)

Implement session persistence:

- Save session state as JSON
- Load session state from JSON
- List available sessions
- Delete old sessions

#### 6.5 Library Scanner (`src/library/scanner.py`)

Implement library structure scanning:

- Scan library folder for markdown files
- Extract file metadata (sections, last modified)
- Build category tree structure
- Produce a **Library Manifest** snapshot (`src/library/manifest.py`) used to constrain routing

#### 6.6 Writer (`src/execution/writer.py`)

Implement file writing operations:

- Create new files with content
- Append content to existing files
- Insert content at specific locations
- Backup files before modification

#### 6.7 Markers (`src/execution/markers.py`)

Implement tracking markers:

- Wrap content with source tracking markers
- Parse markers from existing content
- Support idempotent operations

#### 6.8 SDK Client (`src/sdk/client.py`)

Implement Claude Code SDK wrapper:

- Initialize SDK client
- Send cleanup plan and routing plan queries (two dedicated prompts)
- Parse structured responses
- Handle conversation context
- Do **not** allow the SDK to write files directly; file writes are engine-only (verified)

---

### 7. Content Integrity Module (`src/extraction/integrity.py`)

**NEW COMPONENT** - Write Verification (STRICT prose canonical + code byte-strict)

```python
# src/extraction/integrity.py

import hashlib
from dataclasses import dataclass
from typing import Optional

from ..models.content import ContentBlock, BlockType
from ..models.content_mode import ContentMode
from .canonicalize import canonicalize_prose_v1

@dataclass
class ContentIntegrity:
    """
    Track integrity through write + read-back verification.

    Verification rules:
    - CODE_BLOCK: exact byte checksum must match.
    - STRICT prose: canonical checksum must match (whitespace/line wraps allowed).
    - REFINEMENT: canonical/exact checksums are recorded, not enforced (merge verification happens later).
    """

    block_id: str
    expected_exact: str
    expected_canonical: str
    written_content: Optional[str] = None
    written_exact: Optional[str] = None
    written_canonical: Optional[str] = None
    verified: bool = False

    @classmethod
    def from_block(cls, block: ContentBlock) -> "ContentIntegrity":
        """Create integrity tracker from an extracted block."""
        return cls(
            block_id=block.id,
            expected_exact=block.checksum_exact,
            expected_canonical=block.checksum_canonical,
        )

    @staticmethod
    def _hash(content: str) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def verify_write(self, block: ContentBlock, mode: ContentMode, written_content: str) -> bool:
        """Verify written content matches expected content under the active mode."""
        self.written_content = written_content
        self.written_exact = self._hash(written_content)
        self.written_canonical = self._hash(canonicalize_prose_v1(written_content))

        if mode == ContentMode.REFINEMENT:
            self.verified = True
            return True

        if block.block_type == BlockType.CODE_BLOCK:
            self.verified = (self.expected_exact == self.written_exact)
        else:
            self.verified = (self.expected_canonical == self.written_canonical)
        return self.verified

    def assert_integrity(self) -> None:
        """Raise if integrity check failed."""
        if not self.verified:
            raise IntegrityError(
                f"Content integrity check FAILED!\n"
                f"Expected exact:     {self.expected_exact}\n"
                f"Expected canonical: {self.expected_canonical}\n"
                f"Written exact:      {self.written_exact}\n"
                f"Written canonical:  {self.written_canonical}\n"
                f"Content may have been modified."
            )


class IntegrityError(Exception):
    """Raised when content integrity verification fails."""
    pass
```

---

### 8. Content Mode (`src/models/content_mode.py`)

**NEW COMPONENT** - Two modes for content handling

```python
# src/models/content_mode.py

from enum import Enum


class ContentMode(str, Enum):
    """Content handling mode for extraction."""
    STRICT = "strict"           # Preserve words/sentences; whitespace/line wraps may change; no merges/rewrites
    REFINEMENT = "refinement"   # Optional rewrites/merges with user verification (triple-view)

    @property
    def allows_modifications(self) -> bool:
        return self == ContentMode.REFINEMENT

    @property
    def description(self) -> str:
        if self == ContentMode.STRICT:
            return "Strict - preserve words/sentences; code blocks are byte-strict; no merges/rewrites"
        return "Refinement - optional formatting/merges with user verification (no information loss)"
```

**Refinement Mode Rules:**

- CAN fix grammar issues
- CAN fix formatting problems
- CANNOT alter information content
- CANNOT add new information
- CANNOT remove existing information

---

### 9. Routing Plan Model (`src/models/routing_plan.py`)

**NEW COMPONENT** - Complete routing plan for single approval

```python
# src/models/routing_plan.py

from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class BlockDestination(BaseModel):
    """One destination option for a single block (top-3 UI choices)."""
    destination_file: str                  # e.g., "library/tech/auth.md"
    destination_section: Optional[str] = None
    action: str                            # "create_file" | "create_section" | "append" | "insert_before" | "insert_after" | ("merge" in refinement)
    confidence: float                      # 0.0 to 1.0
    reasoning: str

    # For creation actions
    proposed_file_title: Optional[str] = None
    proposed_section_title: Optional[str] = None


class BlockRoutingItem(BaseModel):
    """Routing options + user selection for one kept block."""
    block_id: str
    heading_path: List[str] = Field(default_factory=list)
    content_preview: str                   # First 200 chars

    # Model output (always 3 options unless library empty)
    options: List[BlockDestination] = Field(default_factory=list)  # length 3

    # User decision (click selection; no typing required)
    selected_option_index: Optional[int] = None  # 0..2
    custom_destination_file: Optional[str] = None
    custom_destination_section: Optional[str] = None
    custom_action: Optional[str] = None

    status: str = "pending"                # "pending" | "selected" | "rejected"


class MergePreview(BaseModel):
    """Preview of a merge operation."""
    merge_id: str
    block_id: str
    existing_content: str
    existing_location: str
    new_content: str
    proposed_merge: str
    merge_reasoning: str


class PlanSummary(BaseModel):
    """Quick summary of the routing plan."""
    total_blocks: int
    blocks_to_new_files: int
    blocks_to_existing_files: int
    blocks_requiring_merge: int
    estimated_actions: int


class RoutingPlan(BaseModel):
    """Complete routing plan for user approval."""
    session_id: str
    source_file: str
    content_mode: str = "strict"      # "strict" or "refinement"
    created_at: datetime = Field(default_factory=datetime.now)

    # The complete plan
    blocks: List[BlockRoutingItem] = Field(default_factory=list)
    merge_previews: List[MergePreview] = Field(default_factory=list)  # refinement-only

    # Summary for quick review
    summary: Optional[PlanSummary] = None

    # Approval
    approved: bool = False
    approved_at: Optional[datetime] = None

    @property
    def all_blocks_resolved(self) -> bool:
        """All kept blocks must have a selected (or custom) destination."""
        return all(
            (b.status == "selected")
            and (b.selected_option_index is not None or b.custom_destination_file is not None)
            for b in self.blocks
        )

    @property
    def pending_count(self) -> int:
        return sum(1 for b in self.blocks if b.status == "pending")

    @property
    def accepted_count(self) -> int:
        return sum(1 for b in self.blocks if b.status == "selected")
```

---

### 10. Updated Writer with Verification (`src/execution/writer.py`)

**UPDATED** - Writer now includes integrity verification

```python
async def write_block(
    self,
    block: ContentBlock,
    destination: str,
    position: str = "append",
    mode: ContentMode = ContentMode.STRICT,
) -> WriteResult:
    """Write block to destination with integrity verification."""

    # 1. Get the exact content to write
    content_to_write = block.content
    expected_exact = block.checksum_exact
    expected_canonical = block.checksum_canonical

    # 2. If REFINEMENT mode, apply grammar/format fixes (never modify code blocks)
    if mode == ContentMode.REFINEMENT and block.block_type != BlockType.CODE_BLOCK:
        content_to_write = await self._apply_refinements(content_to_write)
        # Note: In refinement mode, strict checksums are tracked but not enforced here.

    # 3. Write to file
    await self._write_to_file(destination, content_to_write, position)

    # 4. Read back what was written
    written_content = await self._read_written_section(destination, block.id)

    # 5. Verify checksums (STRICT rules differ for code vs prose)
    if mode == ContentMode.STRICT:
        written_exact = hashlib.sha256(written_content.encode("utf-8")).hexdigest()[:16]

        if block.block_type == BlockType.CODE_BLOCK:
            # Code blocks are byte-strict
            if expected_exact != written_exact:
                raise IntegrityError(
                    f"CRITICAL: Code block modified during write!\n"
                    f"Block: {block.id}\n"
                    f"Expected exact: {expected_exact}\n"
                    f"Got exact:      {written_exact}"
                )
        else:
            # Prose blocks preserve words/sentences; whitespace/line wraps may change
            written_canonical = hashlib.sha256(
                canonicalize_prose_v1(written_content).encode("utf-8")
            ).hexdigest()[:16]
            if expected_canonical != written_canonical:
                raise IntegrityError(
                    f"CRITICAL: Prose content changed during write!\n"
                    f"Block: {block.id}\n"
                    f"Expected canonical: {expected_canonical}\n"
                    f"Got canonical:      {written_canonical}"
                )

    # Optional: In refinement mode, still record what happened for auditing
    if mode == ContentMode.REFINEMENT:
        self._record_refinement_audit(block.id, expected_exact, expected_canonical, written_content)

    # 6. Mark as verified
    block.integrity_verified = True

    return WriteResult(success=True, verified=True)

```

Notes:

- `canonicalize_prose_v1(...)` is defined in `src/extraction/canonicalize.py` and must preserve words/sentences while normalizing whitespace/line-wraps.
- STRICT mode forbids merges/rewrites; refinement-mode merges are handled in Sub-Plan B/E with triple-view.

---

## Technology Stack (Phase 1)

| Component | Technology                   | Purpose                               |
| --------- | ---------------------------- | ------------------------------------- |
| Runtime   | Python 3.11+                 | Core language                         |
| SDK       | Claude Code SDK              | AI conversation for routing decisions |
| Async     | asyncio                      | Non-blocking I/O                      |
| Models    | Pydantic v2                  | Data validation and serialization     |
| Config    | YAML + Environment variables | Configuration files                   |
| Testing   | pytest + pytest-asyncio      | Test framework                        |

---

## Acceptance Criteria

- [ ] Project structure created with all directories
- [ ] All data models implemented with Pydantic v2
- [ ] Content extraction from markdown files works
- [ ] Library manifest snapshot generation works (files + sections)
- [ ] Basic Claude Code SDK integration works (JSON cleanup plan + JSON routing plan)
- [ ] Session creation and persistence (JSON)
- [ ] CleanupPlan: explicit keep/discard decisions per block (no silent discard)
- [ ] RoutingPlan: top-3 destination options per kept block + click selection
- [ ] Append/insert write operations to library files
- [ ] Marker wrapping for tracking source blocks
- [ ] Basic tests passing for core functionality
- [ ] Content integrity module implemented
- [ ] Canonicalization rules implemented (STRICT prose) + byte-strict code block verification
- [ ] ContentMode enum (STRICT/REFINEMENT) working, with merges forbidden in STRICT
- [ ] RoutingPlan model implemented
- [ ] Checksum generation on block extraction (exact + canonical)
- [ ] Write verification (read-back and compare exact/canonical per block type)
- [ ] IntegrityError raised on checksum mismatch
- [ ] Source deletion is only possible after 100% verification success

---

## Test Fixtures

### Sample Source Document (`tests/fixtures/sample_source.md`)

```markdown
# Project Notes

## Authentication Ideas

JWT tokens should be validated on every request. Consider implementing:

- Token refresh mechanism
- Blacklist for revoked tokens

## Database Schema

The users table needs these fields:

- id (UUID)
- email (unique)
- password_hash
- created_at

## Random Thoughts

Remember to review the API rate limiting approach next week.
```

### Expected Extraction Result

The parser should extract 4 blocks:

1. Header section: "Authentication Ideas" with content
2. List block: Token validation considerations
3. Header section: "Database Schema" with content
4. Paragraph: "Random Thoughts" content

---

## Notes for Downstream Session

1. **Start with models**: Implement all Pydantic models first as they define the data contracts
2. **SDK-first runtime**: The engine is driven by Claude Code SDK + Web UI (Phase 4/5). CLI is optional developer tooling only.
3. **Two AI prompts**: Cleanup/structuring plan first, then routing plan (single-pass, top-3 options per block)
4. **No vector search yet**: That's Phase 3; this phase uses simple file-based library scanning
5. **Session persistence**: Use simple JSON files; database migration is future work

---

## Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e ".[dev]"

# Prereq (Claude Code SDK): requires Node.js + Claude Code installed (per Claude Code docs),
# and authentication via your subscription (login/token per docs).
# Model selection can be verified via the Claude Code docs (e.g., `claude --model ...`).

# Run tests
pytest
```

---

_End of Sub-Plan A_

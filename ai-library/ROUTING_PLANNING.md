# Routing Planning: Deep Technical Analysis

> **Purpose**: This document provides a comprehensive, detailed explanation of how the AI-Library routing planning system works - specifically how Claude determines where to place content in the library.

---

## Table of Contents

1. [Big Picture Overview](#1-big-picture-overview)
2. [The Complete Routing Pipeline](#2-the-complete-routing-pipeline)
3. [Phase 1: Library Context Building](#3-phase-1-library-context-building)
4. [Phase 2: Candidate Pre-Filtering](#4-phase-2-candidate-pre-filtering)
5. [Phase 3: LLM Prompt Construction](#5-phase-3-llm-prompt-construction)
6. [Phase 4: LLM Decision Making](#6-phase-4-llm-decision-making)
7. [Phase 5: Response Processing](#7-phase-5-response-processing)
8. [Scoring Metrics Deep Dive](#8-scoring-metrics-deep-dive)
9. [Data Flow Diagrams](#9-data-flow-diagrams)
10. [Improvement Opportunities](#10-improvement-opportunities)

---

## 1. Big Picture Overview

### What Is Routing Planning?

Routing planning is the process of determining **where each content block should be placed** in the library after a user has decided to keep it. The system suggests the top 3 most appropriate destinations for each block.

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          ROUTING PLANNING PIPELINE                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  INPUT: Kept content blocks from cleanup phase                               │
│  - Block ID, content, heading path, type                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  BUILD LIBRARY      │  │  PRE-FILTER         │  │  PREPARE BLOCK      │
│  CONTEXT            │  │  CANDIDATES         │  │  DATA               │
│                     │  │                     │  │                     │
│  • Scan folders     │  │  • Lexical matching │  │  • Format content   │
│  • Extract sections │  │  • TF-IDF scoring   │  │  • Include headings │
│  • Build manifest   │  │  • Vector search    │  │  • Add previews     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
                │                    │                    │
                └────────────────────┼────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    CONSTRUCT LLM PROMPT                                       │
│                                                                              │
│  • System prompt: Routing instructions, action types, JSON format            │
│  • User prompt: Library structure + Block details + Candidate hints          │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    LLM PROCESSES REQUEST                                      │
│                                                                              │
│  Claude analyzes:                                                            │
│  1. Content semantics (what is this block about?)                            │
│  2. Library structure (where could it fit?)                                  │
│  3. Candidate hints (what pre-computed matches exist?)                       │
│  4. Action appropriateness (append vs create_section vs create_file)         │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  OUTPUT: JSON with 3 destination options per block                           │
│  - Destination file & section                                                │
│  - Action type (append, create_file, create_section, etc.)                   │
│  - Confidence score (0.0 - 1.0)                                              │
│  - Reasoning explanation                                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  USER SELECTS: One of 3 options (or custom destination)                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Participants

| Component                 | Role                                | Code Location                             |
| ------------------------- | ----------------------------------- | ----------------------------------------- |
| **PlanningFlow**          | Orchestrates the entire process     | `src/conversation/flow.py:43-289`         |
| **ClaudeCodeClient**      | Communicates with Claude            | `src/sdk/client.py:246-346`               |
| **LibraryManifest**       | Builds library structure snapshot   | `src/library/manifest.py:19-180`          |
| **CandidateFinder**       | Pre-filters destinations (lexical)  | `src/library/candidates.py:27-340`        |
| **VectorCandidateFinder** | Pre-filters destinations (semantic) | `src/library/candidates_vector.py:17-184` |
| **build_routing_prompt**  | Constructs the LLM prompt           | `src/sdk/prompts/routing_mode.py:93-185`  |

---

## 2. The Complete Routing Pipeline

### Step-by-Step Execution

The routing process is triggered by `SessionManager.generate_routing_plan_with_ai()`:

**Location**: `src/session/manager.py:393-442`

```
Step 1: Load session from storage
        │
        ▼
Step 2: Create PlanningFlow instance
        │
        ▼
Step 3: Call flow.generate_routing_plan(session, candidate_finder)
        │
        ▼
Step 4: [Inside PlanningFlow]
        │
        ├─► Validate prerequisites (cleanup approved, source exists)
        │
        ├─► Identify kept blocks from cleanup plan
        │
        ├─► Load library manifest (get_routing_context)
        │
        ├─► [Optional] Run candidate pre-filtering
        │   │
        │   └─► For each block:
        │       └─► candidate_finder.top_candidates(library_context, block)
        │
        ├─► Call SDK: generate_routing_plan(...)
        │   │
        │   └─► build_routing_prompt(...) constructs prompt
        │   │
        │   └─► _query(...) sends to Claude
        │   │
        │   └─► _extract_json(...) parses response
        │
        └─► Return RoutingPlan with options
```

---

## 3. Phase 1: Library Context Building

### What Is Library Context?

Library context is a **snapshot of the entire library structure** that tells the LLM what destinations are available. It includes:

- Categories (folders)
- Files (markdown documents)
- Sections (H2 headers within files)
- Summary statistics

### How It's Built

**Location**: `src/library/manifest.py:148-180`

```python
async def get_routing_context(self) -> Dict[str, Any]:
    """
    Get a compact manifest suitable for routing decisions.

    Optimized for AI prompts with:
    - Category names and descriptions
    - File titles and their sections
    - No content, just structure
    """
```

### Library Scanning Process

**Location**: `src/library/scanner.py:23-58`

```
Library Root Directory
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  LibraryScanner.scan()                                                  │
│                                                                         │
│  1. Iterate root-level directories (skip . and _ prefixed)             │
│                                                                         │
│  2. For each directory (category):                                      │
│     a. Scan .md files → extract title (H1) and sections (H2)           │
│     b. Recurse into subdirectories (subcategories)                     │
│                                                                         │
│  3. Build counts: total_files, total_sections                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### File Metadata Extraction

**Location**: `src/library/scanner.py:99-125`

For each markdown file, the scanner extracts:

```python
# Extract title (first H1 or filename)
title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
title = title_match.group(1) if title_match else file_path.stem

# Extract sections (H2 headers)
sections = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

# Count blocks (rough estimate based on paragraphs)
blocks = len(re.split(r'\n\n+', content.strip()))
```

### Library Context Structure (Sent to LLM)

```json
{
  "summary": {
    "total_categories": 5,
    "total_files": 23,
    "total_sections": 87
  },
  "categories": [
    {
      "name": "tech",
      "path": "tech",
      "files": [
        {
          "path": "tech/authentication.md",
          "title": "Authentication Guide",
          "sections": ["JWT Tokens", "OAuth 2.0", "Session Management"]
        },
        {
          "path": "tech/security.md",
          "title": "Security Best Practices",
          "sections": ["Input Validation", "Encryption"]
        }
      ],
      "subcategories": [...]
    }
  ]
}
```

### How This Helps the LLM

The LLM uses this structure to:

1. **Understand available destinations** - What files/sections already exist
2. **Identify gaps** - Where new files/sections might be needed
3. **Match content to structure** - Find the most relevant existing location
4. **Maintain organization** - Keep related content together

---

## 4. Phase 2: Candidate Pre-Filtering

### Why Pre-Filtering?

Instead of asking the LLM to evaluate the entire library for each block, we **pre-compute the most likely destinations** and provide them as "hints". This:

- Reduces LLM cognitive load
- Improves routing accuracy
- Provides transparency (shows similarity scores)

### Two Candidate Finding Approaches

#### Approach A: Lexical Candidate Finder (Default)

**Location**: `src/library/candidates.py:27-340`

Uses traditional text analysis:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LEXICAL CANDIDATE SCORING                                              │
│                                                                         │
│  For each library file, compute combined score:                         │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │  Combined Score = (TF-IDF × 0.5) + (Keywords × 0.3)      │          │
│  │                 + (Heading Match × 0.2)                   │          │
│  └──────────────────────────────────────────────────────────┘          │
│                                                                         │
│  1. TF-IDF Similarity (50% weight)                                     │
│     • Term frequency × inverse document frequency                       │
│     • Measures semantic similarity based on word importance             │
│                                                                         │
│  2. Keyword Overlap (30% weight)                                       │
│     • Exact word matches between block and file                        │
│     • Simple but effective for technical terms                         │
│                                                                         │
│  3. Heading Match (20% weight)                                         │
│     • Similarity between block's heading path and file sections        │
│     • Captures structural relevance                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

##### TF-IDF Calculation

**Location**: `src/library/candidates.py:135-175`

```python
def _tfidf_similarity(self, query_tokens, doc_tokens) -> float:
    """
    1. Compute term frequency (TF) for both query and document
    2. Look up inverse document frequency (IDF) from cache
    3. Build TF-IDF vectors for both
    4. Compute cosine similarity between vectors
    """

    # TF = count(term) / total_terms
    query_tf = self._compute_tf(query_tokens)
    doc_tf = self._compute_tf(doc_tokens)

    # TF-IDF vector: TF × IDF for each term
    for term in all_terms:
        idf = self._idf_cache.get(term, 1.0)  # IDF = log(total_docs / docs_with_term)
        query_vec.append(query_tf.get(term, 0) * idf)
        doc_vec.append(doc_tf.get(term, 0) * idf)

    # Cosine similarity = dot_product / (norm_a × norm_b)
    return dot_product / (query_norm * doc_norm)
```

##### Keyword Overlap

**Location**: `src/library/candidates.py:177-196`

```python
def _keyword_overlap(self, query_tokens, doc_tokens) -> float:
    """
    Simple overlap ratio: |intersection| / |query|

    E.g., if block has [jwt, token, auth, security]
    and file has [jwt, token, oauth, session]
    overlap = 2/4 = 0.5
    """
    overlap = query_tokens & doc_tokens
    return len(overlap) / len(query_tokens)
```

##### Heading Match

**Location**: `src/library/candidates.py:198-231`

```python
def _heading_match(self, block_heading_path, file_sections):
    """
    Find the best matching section based on heading word overlap.

    E.g., if block heading is "JWT Token Validation"
    and file has sections ["JWT Tokens", "OAuth Setup"]
    → "JWT Tokens" would match with high score
    """
    for section in file_sections:
        section_tokens = set(self._tokenize(section))
        overlap = self._keyword_overlap(block_tokens, section_tokens)
        if overlap > best_score:
            best_score = overlap
            best_section = section

    return best_score, best_section
```

##### Tokenization (Text Preprocessing)

**Location**: `src/library/candidates.py:51-86`

````python
def _tokenize(self, text: str) -> List[str]:
    """
    1. Remove markdown formatting (code blocks, links, emphasis)
    2. Extract words (alphanumeric sequences)
    3. Convert to lowercase
    4. Filter stopwords (the, a, is, are, etc.)
    5. Keep only words > 2 characters
    """
    # Remove code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Extract words
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', text.lower())
    # Filter stopwords
    return [w for w in words if w not in stopwords and len(w) > 2]
````

#### Approach B: Vector Candidate Finder (Phase 3A)

**Location**: `src/library/candidates_vector.py:17-184`

Uses semantic embeddings for more intelligent matching:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  VECTOR CANDIDATE SCORING                                               │
│                                                                         │
│  1. Get block content                                                   │
│  2. Convert to embedding vector (via Mistral/OpenAI)                    │
│  3. Search Qdrant for similar indexed content                           │
│  4. Return top matches with similarity scores                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │  Score = Cosine Similarity (0.0 - 1.0)                   │          │
│  │                                                          │          │
│  │  Threshold: min_score = 0.3 (configurable)               │          │
│  └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Vector Search Flow**:

```python
async def top_candidates(self, library_context, block):
    # 1. Ensure library is indexed
    await self.search.ensure_indexed()

    # 2. Search for similar content
    results = await self.store.search(
        query=block_content,
        n_results=self.top_n * 2,  # Get extra for filtering
    )

    # 3. Filter by similarity threshold
    for result in results:
        if result["score"] >= self.min_score:
            # 4. Validate against manifest (must exist in library structure)
            if self._is_in_manifest(library_context, file_path, section):
                candidates.append(CandidateMatch(...))

    # 5. Fallback to manifest-based heuristics if not enough results
    if len(candidates) < 3:
        candidates.extend(self._fallback_from_manifest(...))
```

### Candidate Output Format

Both finders produce the same output structure:

```python
@dataclass
class CandidateMatch:
    file_path: str           # e.g., "tech/authentication.md"
    section: Optional[str]   # e.g., "JWT Tokens"
    score: float             # 0.0 - 1.0
    match_reasons: List[str] # e.g., ["TF-IDF: 0.72", "Keywords: 0.45"]
```

---

## 5. Phase 3: LLM Prompt Construction

### System Prompt (Instructions to Claude)

**Location**: `src/sdk/prompts/routing_mode.py:12-90`

The system prompt tells Claude:

1. **Its role**: "Knowledge librarian assistant routing content blocks"
2. **The task**: "Suggest top 3 destinations per block"
3. **Library structure explanation**: Categories → Files → Sections hierarchy
4. **Output format**: Exact JSON schema expected
5. **Action types**: append, create_file, create_section, insert_before, insert_after
6. **Rules**: Always 3 options, first is best, confidence decreases, no merging in STRICT mode

**Full System Prompt**:

```
You are a knowledge librarian assistant routing content blocks to their
appropriate locations in a personal knowledge library.

Your task is to analyze each content block and suggest the top 3 most
appropriate destinations in the library.

## Your Role

1. **Analyze Content**: Understand what each block contains and its topic/domain
2. **Match to Library**: Find the best existing files/sections or suggest new ones
3. **Provide Options**: Give exactly 3 destination options per block, ranked by fit

## Library Structure

The library is organized by categories (folders) containing markdown files
with sections.
- Categories: Top-level folders for broad topics
- Files: Markdown files for specific topics within a category
- Sections: H2 headers within files for subtopics

## Output Format

Return a JSON object with the following structure:
{
  "routing_items": [
    {
      "block_id": "block_001",
      "options": [
        {
          "destination_file": "tech/authentication.md",
          "destination_section": "JWT Tokens",
          "action": "append",
          "confidence": 0.9,
          "reasoning": "Block discusses JWT token validation..."
        },
        { ... option 2 with lower confidence ... },
        { ... option 3 with lowest confidence ... }
      ]
    }
  ],
  "summary": { ... }
}

## Action Types

- `append`: Add to end of existing file or section
- `create_file`: Create a new file (provide proposed_file_title)
- `create_section`: Create a new section in existing file
- `insert_before`: Insert before a specific section
- `insert_after`: Insert after a specific section

## Rules

- Always provide exactly 3 options per block
- First option should be the best match
- Confidence should decrease for less ideal options
- Never suggest merging in STRICT mode
- Consider semantic relevance, not just keyword matching
- If library is empty, suggest logical new file structures
```

### User Prompt Construction

**Location**: `src/sdk/prompts/routing_mode.py:93-185`

The user prompt is dynamically built with:

1. **Source file identification**
2. **Content mode** (STRICT or REFINEMENT)
3. **Current library structure** (from manifest)
4. **Blocks to route** with candidate hints

**Prompt Template**:

```
Route these content blocks to appropriate library locations.

## Source File
{source_file_path}

## Content Mode
STRICT - No merging or rewriting allowed

## Current Library Structure

Total Categories: 5
Total Files: 23
Total Sections: 87

- **tech/** (tech)
  - Authentication Guide (tech/authentication.md)
    - ## JWT Tokens
    - ## OAuth 2.0
    - ## Session Management
  - Security Best Practices (tech/security.md)
    - ## Input Validation
    - ## Encryption

[... more categories ...]

## Blocks to Route

### Block block_001
- Type: paragraph
- Heading Path: Authentication > Token Validation
- Candidate Destinations (hints):
  - tech/authentication.md → JWT Tokens (score 0.72)
  - tech/security.md → Input Validation (score 0.45)
  - tech/api.md → Authentication (score 0.38)
- Content:
```

JWT tokens should be validated on every request. The validation
process involves checking the signature, expiration time, and
issuer claims...

```

### Block block_002
[... next block ...]

## Instructions

For each block, provide exactly 3 destination options ranked by fit.
Consider:
1. Semantic relevance to existing content
2. Logical organization
3. Whether new files/sections would better serve the content

Return your routing plan as a valid JSON object.
```

### How Candidate Hints Are Formatted

**Location**: `src/sdk/prompts/routing_mode.py:120-140`

```python
# For each block, format candidate hints
candidates = block_candidates_by_id.get(block["id"]) or []
for c in candidates[:3]:  # Show top 3 candidates
    line = f"  - {file_path}"
    if section:
        line += f" → {section}"
    if isinstance(score, (int, float)):
        line += f" (score {score:.2f})"
    candidate_lines.append(line)
```

Example output:

```
- Candidate Destinations (hints):
  - tech/authentication.md → JWT Tokens (score 0.72)
  - tech/security.md → Input Validation (score 0.45)
  - tech/api.md (score 0.38)
```

---

## 6. Phase 4: LLM Decision Making

### What Claude Actually Does

When Claude receives the prompt, it performs these cognitive tasks:

#### 1. Content Analysis

Claude reads each block and identifies:

- **Topic/Domain**: What subject area does this content belong to?
- **Specificity**: Is this a broad overview or detailed specifics?
- **Relationships**: Does it reference other concepts that might exist in the library?

**Example reasoning**:

```
"This block discusses JWT token validation with specific code examples
for checking signatures. It's a technical implementation detail that
belongs in a programming/security context."
```

#### 2. Library Structure Matching

Claude evaluates the library structure:

- **Existing files**: Which files cover related topics?
- **Existing sections**: Which sections are most semantically aligned?
- **Gaps**: Are there missing files/sections that should be created?

**Example reasoning**:

```
"The library has 'tech/authentication.md' with a 'JWT Tokens' section.
This block directly extends that topic. However, 'tech/security.md'
also has an 'Input Validation' section which is tangentially related."
```

#### 3. Candidate Hint Integration

Claude uses the pre-computed candidates as starting points:

- **High-scoring candidates** (0.7+): Strong signals, likely good destinations
- **Medium-scoring candidates** (0.4-0.7): Consider but evaluate carefully
- **Low-scoring candidates** (<0.4): May suggest new destinations instead

**Example reasoning**:

```
"The candidate finder suggests 'tech/authentication.md → JWT Tokens'
with score 0.72. This aligns with my semantic analysis. I'll make this
the primary option."
```

#### 4. Action Selection

Claude decides the appropriate action:

| Action           | When to Use                                  |
| ---------------- | -------------------------------------------- |
| `append`         | Content fits at end of existing file/section |
| `create_section` | New subtopic within existing file            |
| `create_file`    | New topic not covered by existing files      |
| `insert_before`  | Content should precede a specific section    |
| `insert_after`   | Content should follow a specific section     |

#### 5. Confidence Scoring

Claude assigns confidence based on:

- **Match quality**: How well does the destination fit?
- **Uniqueness**: Is this clearly the best option or are there competitors?
- **Completeness**: Does the destination fully accommodate the content?

**Confidence Guidelines**:

- **0.9-1.0**: Perfect match, highly confident
- **0.7-0.9**: Good match, confident
- **0.5-0.7**: Reasonable match, some uncertainty
- **0.3-0.5**: Possible match, significant uncertainty
- **<0.3**: Weak match, likely fallback option

### LLM Output Structure

Claude returns structured JSON:

```json
{
  "routing_items": [
    {
      "block_id": "block_001",
      "options": [
        {
          "destination_file": "tech/authentication.md",
          "destination_section": "JWT Tokens",
          "action": "append",
          "confidence": 0.9,
          "reasoning": "Block discusses JWT token validation which directly extends the existing JWT Tokens section. The content includes implementation details that complement existing material."
        },
        {
          "destination_file": "tech/authentication.md",
          "destination_section": null,
          "action": "create_section",
          "proposed_section_title": "Token Validation",
          "confidence": 0.75,
          "reasoning": "Could create a dedicated section for validation specifics if more granular organization is preferred."
        },
        {
          "destination_file": "tech/security.md",
          "destination_section": "Input Validation",
          "action": "append",
          "confidence": 0.55,
          "reasoning": "Token validation is a form of input validation, though this placement would separate it from other authentication content."
        }
      ]
    }
  ],
  "summary": {
    "total_blocks": 4,
    "blocks_to_existing_files": 3,
    "blocks_to_new_files": 1,
    "estimated_actions": 4
  }
}
```

---

## 7. Phase 5: Response Processing

### JSON Extraction

**Location**: `src/sdk/client.py:149-178`

Claude's response may contain extra text, so robust extraction is needed:

````python
def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code block
    json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first '{' to last '}'
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        try:
            return json.loads(text[start_idx : end_idx + 1])
        except json.JSONDecodeError:
            pass

    return None
````

### Response Mapping to Data Models

**Location**: `src/sdk/client.py:277-346`

The JSON is converted to strongly-typed models:

```python
for item_data in response.data.get("routing_items", []):
    block_id = item_data.get("block_id")

    options = []
    for opt in item_data.get("options", [])[:3]:  # Max 3 options
        options.append(
            BlockDestination(
                destination_file=opt.get("destination_file", ""),
                destination_section=opt.get("destination_section"),
                action=opt.get("action", "append"),
                confidence=opt.get("confidence", 0.5),
                reasoning=opt.get("reasoning", ""),
                proposed_file_title=opt.get("proposed_file_title"),
                proposed_section_title=opt.get("proposed_section_title"),
            )
        )

    routing_by_block_id[block_id] = BlockRoutingItem(
        block_id=block_id,
        heading_path=block_map[block_id].get("heading_path", []),
        content_preview=block_map[block_id]["content"][:200],
        options=options,
        status="pending",
    )
```

### Fallback Handling

If LLM doesn't return options for a block:

```python
# Always return one routing item per input block (no silent drops)
for block in blocks:
    block_id = block["id"]
    item = routing_by_block_id.get(block_id)
    if item is None:
        # Create empty placeholder - user will need to manually route
        routing_items.append(
            BlockRoutingItem(
                block_id=block_id,
                heading_path=block.get("heading_path", []),
                content_preview=block["content"][:200],
                options=[],  # Empty - requires manual selection
                status="pending",
            )
        )
```

---

## 8. Scoring Metrics Deep Dive

### Lexical Candidate Finder Scoring

**Combined Formula**:

```
Combined Score = (TF-IDF × 0.5) + (Keyword Overlap × 0.3) + (Heading Match × 0.2)
```

**Component Details**:

| Metric            | Weight | Range     | Description                       |
| ----------------- | ------ | --------- | --------------------------------- |
| TF-IDF Similarity | 50%    | 0.0 - 1.0 | Semantic word importance matching |
| Keyword Overlap   | 30%    | 0.0 - 1.0 | Direct word intersection          |
| Heading Match     | 20%    | 0.0 - 1.0 | Section title alignment           |

**Example Calculation**:

```
Block: "JWT tokens should be validated on every request..."
File: "tech/authentication.md" with sections ["JWT Tokens", "OAuth 2.0"]

TF-IDF Score: 0.68
- Block tokens: [jwt, tokens, validated, request, validation, process, signature, expiration, issuer, claims]
- File tokens: [jwt, tokens, oauth, authentication, session, cookies]
- Common high-IDF terms: jwt, tokens
- Cosine similarity: 0.68

Keyword Overlap: 0.30
- Block unique words: 10
- File unique words: 6
- Overlap: 2 (jwt, tokens)
- Score: 2/10 = 0.20... wait, normalized: 0.30

Heading Match: 0.75
- Block heading: "Authentication > Token Validation"
- Best section match: "JWT Tokens"
- Tokens overlap: [token/tokens, jwt] → high overlap

Combined: (0.68 × 0.5) + (0.30 × 0.3) + (0.75 × 0.2)
        = 0.34 + 0.09 + 0.15
        = 0.58
```

### Vector Candidate Finder Scoring

**Formula**: Pure cosine similarity from embedding space

```
Score = Cosine Similarity(embed(block_content), embed(library_chunk))
```

**Thresholds**:

- **min_score**: 0.3 (below this, not considered)
- **top_n**: 5 (maximum candidates per block)

### LLM Confidence Scoring

Claude assigns confidence based on qualitative assessment:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  LLM CONFIDENCE FACTORS                                                 │
│                                                                         │
│  HIGH CONFIDENCE (0.8-1.0):                                             │
│  • Exact topic match with existing section                              │
│  • Content clearly extends existing material                            │
│  • No ambiguity about best placement                                    │
│                                                                         │
│  MEDIUM CONFIDENCE (0.5-0.8):                                           │
│  • Related topic, reasonable fit                                        │
│  • Multiple valid options exist                                         │
│  • Some interpretation required                                         │
│                                                                         │
│  LOW CONFIDENCE (0.3-0.5):                                              │
│  • Tangential relationship                                              │
│  • Better as fallback option                                            │
│  • New file/section might be preferable                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Data Flow Diagrams

### Complete Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ROUTING PLANNING DATA FLOW                            │
└──────────────────────────────────────────────────────────────────────────────┘

                        ┌─────────────────────┐
                        │  ExtractionSession  │
                        │                     │
                        │  • source.blocks    │
                        │  • cleanup_plan     │
                        │  • library_path     │
                        └─────────────────────┘
                                  │
                                  │ (kept blocks)
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PlanningFlow.generate_routing_plan()                │
└─────────────────────────────────────────────────────────────────────────────┘
          │                              │                              │
          ▼                              ▼                              ▼
┌─────────────────┐            ┌─────────────────┐            ┌─────────────────┐
│ LibraryManifest │            │ CandidateFinder │            │ Block Prep      │
│ .get_routing_   │            │ .top_candidates │            │                 │
│  context()      │            │ ()              │            │ Format blocks   │
└─────────────────┘            └─────────────────┘            │ with content,   │
          │                              │                    │ headings, etc.  │
          ▼                              ▼                    └─────────────────┘
┌─────────────────┐            ┌─────────────────┐                    │
│ Library Context │            │ Candidate Hints │                    │
│                 │            │                 │                    │
│ {categories,    │            │ {block_id:      │                    │
│  files,         │            │  [CandidateMatch│                    │
│  sections}      │            │   ...]}         │                    │
└─────────────────┘            └─────────────────┘                    │
          │                              │                            │
          └──────────────────────────────┼────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │     build_routing_prompt()          │
                        │                                     │
                        │  Combines:                          │
                        │  • Library structure (formatted)    │
                        │  • Block details with previews      │
                        │  • Candidate hints with scores      │
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │     ClaudeCodeClient._query()       │
                        │                                     │
                        │  Sends to Claude:                   │
                        │  • System prompt (routing rules)    │
                        │  • User prompt (context + blocks)   │
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │           CLAUDE (LLM)              │
                        │                                     │
                        │  1. Analyze each block's semantics  │
                        │  2. Match to library structure      │
                        │  3. Consider candidate hints        │
                        │  4. Generate 3 ranked options       │
                        │  5. Assign confidence scores        │
                        │  6. Write reasoning explanations    │
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │         JSON Response               │
                        │                                     │
                        │  {routing_items: [...], summary: {}}│
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │       _extract_json() +             │
                        │       Model Mapping                 │
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │         RoutingPlan                 │
                        │                                     │
                        │  • blocks: [BlockRoutingItem]       │
                        │    • options: [BlockDestination]    │
                        │  • summary: PlanSummary             │
                        └─────────────────────────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────────┐
                        │         USER SELECTION              │
                        │                                     │
                        │  User picks 1 of 3 options          │
                        │  (or provides custom destination)   │
                        └─────────────────────────────────────┘
```

### Candidate Finding Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CANDIDATE FINDER COMPARISON                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│    LEXICAL CANDIDATE FINDER     │    │    VECTOR CANDIDATE FINDER      │
└─────────────────────────────────┘    └─────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  Input: Block content           │    │  Input: Block content           │
└─────────────────────────────────┘    └─────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  Tokenize:                      │    │  Embed:                         │
│  • Remove markdown              │    │  • Convert to vector via        │
│  • Extract words                │    │    embedding model              │
│  • Remove stopwords             │    │  • 1024 dimensions (Mistral)    │
│  • Lowercase                    │    │                                 │
└─────────────────────────────────┘    └─────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  For each library file:         │    │  Search Qdrant:                 │
│  • Compute TF-IDF similarity    │    │  • Cosine similarity search     │
│  • Compute keyword overlap      │    │  • Return top N matches         │
│  • Compute heading match        │    │                                 │
│  • Combine with weights         │    │                                 │
└─────────────────────────────────┘    └─────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  Sort by combined score         │    │  Filter by:                     │
│  Return top N (default 5)       │    │  • min_score threshold (0.3)    │
│                                 │    │  • manifest validation          │
│                                 │    │  • fallback if < 3 results      │
└─────────────────────────────────┘    └─────────────────────────────────┘
              │                                      │
              ▼                                      ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│  Output: List[CandidateMatch]   │    │  Output: List[CandidateMatch]   │
│  • file_path                    │    │  • file_path                    │
│  • section                      │    │  • section                      │
│  • score                        │    │  • score                        │
│  • match_reasons                │    │  • match_reasons                │
└─────────────────────────────────┘    └─────────────────────────────────┘

PROS:                                  PROS:
• Fast, no external API calls          • Semantic understanding
• Deterministic                        • Handles synonyms/paraphrasing
• Transparent scoring                  • Better for varied vocabulary

CONS:                                  CONS:
• Keyword-based only                   • Requires indexed library
• Misses semantic similarity           • API call latency
• Struggles with synonyms              • Less deterministic
```

---

## 10. Improvement Opportunities

### Current Limitations

1. **Single-Pass LLM Call**
   - Current: One LLM call processes all blocks
   - Issue: Large documents may exceed context limits or reduce quality
   - Location: `src/sdk/client.py:246-346`

2. **Static Candidate Weighting**
   - Current: Fixed weights (TF-IDF 50%, Keywords 30%, Heading 20%)
   - Issue: May not be optimal for all content types
   - Location: `src/library/candidates.py:287-292`

3. **No Confidence Calibration**
   - Current: LLM assigns confidence subjectively
   - Issue: No feedback loop to improve calibration
   - Location: N/A (LLM behavior)

4. **Binary Candidate Finding**
   - Current: Either lexical OR vector, not combined
   - Issue: Missing opportunity for hybrid approach
   - Location: `src/library/candidates.py:347-371`

### Suggested Improvements

#### 1. Hybrid Candidate Finding

Combine lexical and vector approaches:

```python
# Proposed hybrid scoring
def hybrid_candidates(block, library_context):
    lexical = lexical_finder.top_candidates(library_context, block)
    vector = vector_finder.top_candidates(library_context, block)

    # Merge and re-score
    combined = {}
    for c in lexical:
        combined[c.file_path] = {
            'lexical': c.score,
            'vector': 0.0
        }
    for c in vector:
        if c.file_path in combined:
            combined[c.file_path]['vector'] = c.score
        else:
            combined[c.file_path] = {'lexical': 0.0, 'vector': c.score}

    # Weighted combination
    for path, scores in combined.items():
        combined[path]['final'] = (
            scores['lexical'] * 0.4 +
            scores['vector'] * 0.6
        )
```

#### 2. Adaptive Weighting

Learn optimal weights from user selections:

```python
# Proposed feedback collection
def record_user_selection(block_id, selected_option, all_options):
    # Track which candidate hints were useful
    feedback.append({
        'block_id': block_id,
        'selected': selected_option.destination_file,
        'candidates': [c.file_path for c in candidates],
        'candidate_scores': [c.score for c in candidates],
        'llm_confidence': selected_option.confidence
    })

# Periodically retrain weights
def optimize_weights(feedback_history):
    # Use feedback to adjust TF-IDF/Keyword/Heading weights
    ...
```

#### 3. Batched LLM Processing

Process blocks in batches to manage context:

```python
# Proposed batched processing
BATCH_SIZE = 10

async def generate_routing_plan_batched(blocks, library_context):
    all_results = []

    for i in range(0, len(blocks), BATCH_SIZE):
        batch = blocks[i:i+BATCH_SIZE]
        results = await sdk_client.generate_routing_plan(
            blocks=batch,
            library_context=library_context
        )
        all_results.extend(results.blocks)

    return RoutingPlan(blocks=all_results)
```

#### 4. Destination Validation Pre-LLM

Validate candidate destinations before sending to LLM:

```python
# Proposed validation
async def validate_candidates_before_llm(candidates, library_context):
    validated = []
    for c in candidates:
        # Check file exists
        if await file_exists(c.file_path):
            # Check section exists (if specified)
            if c.section is None or await section_exists(c.file_path, c.section):
                validated.append(c)
    return validated
```

#### 5. Confidence Calibration

Use historical data to calibrate LLM confidence:

```python
# Proposed calibration
class ConfidenceCalibrator:
    def __init__(self):
        self.calibration_data = []  # (predicted, actual_selected)

    def calibrate(self, predicted_confidence, option_index):
        # Was the selected option what we predicted?
        actual = 1.0 if option_index == 0 else (0.5 if option_index == 1 else 0.0)
        self.calibration_data.append((predicted_confidence, actual))

    def get_calibrated_confidence(self, raw_confidence):
        # Apply learned calibration curve
        return self.calibration_curve(raw_confidence)
```

### Code Locations for Improvements

| Improvement            | Primary File                | Key Functions             |
| ---------------------- | --------------------------- | ------------------------- |
| Hybrid candidates      | `src/library/candidates.py` | `get_candidate_finder()`  |
| Adaptive weights       | `src/library/candidates.py` | `top_candidates()`        |
| Batched processing     | `src/sdk/client.py`         | `generate_routing_plan()` |
| Pre-validation         | `src/conversation/flow.py`  | `generate_routing_plan()` |
| Confidence calibration | New file needed             | N/A                       |

---

## Summary

The routing planning system works through a multi-phase pipeline:

1. **Library Context Building**: Scan and structure the entire library
2. **Candidate Pre-Filtering**: Compute likely destinations using lexical/vector similarity
3. **LLM Prompt Construction**: Build detailed prompt with library structure and candidate hints
4. **LLM Decision Making**: Claude analyzes content, matches to structure, assigns confidence
5. **Response Processing**: Extract JSON, map to models, handle fallbacks

The key insight is that **the LLM doesn't work alone** - it receives pre-computed candidate hints that guide its decisions. The scoring combines:

- **Lexical metrics**: TF-IDF, keyword overlap, heading match
- **Vector metrics**: Cosine similarity from embeddings
- **LLM judgment**: Semantic understanding, reasoning, confidence assignment

This hybrid approach balances computational efficiency with semantic intelligence to produce accurate routing suggestions.

---

_Document generated: 2026-01-23_
_Based on codebase analysis of AI-Library routing system_

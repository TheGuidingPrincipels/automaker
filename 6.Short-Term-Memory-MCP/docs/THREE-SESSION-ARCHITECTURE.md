# Three-Session Learning Architecture

## System Overview

This document provides **fact-based recommendations** for implementing three dedicated Claude Code sessions that work together through the Short-Term Memory MCP:

1. **Research Session** - Researches concepts and stores to Short-Term Memory MCP
2. **Teaching Session** - Retrieves concepts and explains them to the user
3. **Transfer Session** - Moves concepts to permanent Knowledge MCP storage

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER LEARNING WORKFLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│   SESSION 1   │          │   SESSION 2   │          │   SESSION 3   │
│   RESEARCH    │          │   TEACHING    │          │   TRANSFER    │
│               │          │               │          │               │
│ • Identify    │          │ • Retrieve    │          │ • Get unstored│
│ • Research    │          │ • Explain     │          │ • Transfer    │
│ • Store       │          │ • Q&A         │          │ • Link IDs    │
└───────┬───────┘          └───────┬───────┘          └───────┬───────┘
        │                          │                          │
        │    WRITES                │    READS                 │    READS/WRITES
        │                          │                          │
        ▼                          ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SHORT-TERM MEMORY MCP                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Sessions   │  │   Concepts   │  │ Stage Data   │  │ Research     │    │
│  │   Table      │  │   Table      │  │ Table        │  │ Cache        │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ TRANSFER (Session 3)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       KNOWLEDGE MCP (Long-Term)                             │
│                    Neo4j + ChromaDB + Event Store                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Session 1: Research Session

### Purpose

Identify and research concepts, storing all findings to Short-Term Memory MCP for later teaching and transfer.

### Required Tools (10 tools)

| Tool                           | Purpose                        | When Used                        |
| ------------------------------ | ------------------------------ | -------------------------------- |
| `initialize_daily_session`     | Create session with goals      | Start of research                |
| `store_concepts_from_research` | Bulk store identified concepts | After research                   |
| `update_concept_status`        | Progress through stages        | After each stage                 |
| `store_stage_data`             | Store stage-specific data      | After processing                 |
| `add_concept_question`         | Record questions for teaching  | During research                  |
| `add_concept_relationship`     | Link related concepts          | After identification             |
| `check_research_cache`         | Check for cached research      | Before deep research             |
| `trigger_research`             | Trigger new research           | On cache miss                    |
| `update_research_cache`        | Store research results         | After research                   |
| `add_domain_to_whitelist`      | Add new trusted sources        | When discovering quality sources |

### Workflow

```
RESEARCH SESSION WORKFLOW
═════════════════════════

STEP 1: Initialize Session
──────────────────────────
Tool: initialize_daily_session
{
  "learning_goal": "User's learning objective",
  "building_goal": "User's building objective"
}
→ session_id = "YYYY-MM-DD"

STEP 2: Identify Concepts (SCOUR Stage)
───────────────────────────────────────
User provides topic → Research to identify 10-25 concepts
Each concept needs:
  - concept_name: Clear, searchable name
  - data: {
      description: Brief explanation,
      source: Where identified,
      category: Domain/topic area,
      difficulty: beginner|intermediate|advanced,
      prerequisites: [list of prior concepts],
      tags: [relevant keywords]
    }

Tool: store_concepts_from_research
{
  "session_id": "2025-01-25",
  "concepts": [array of concept objects]
}

STEP 3: Establish Relationships (AIM Stage)
───────────────────────────────────────────
For each concept pair:
  Tool: add_concept_relationship
  {
    "concept_id": "source-concept-id",
    "related_concept_id": "target-concept-id",
    "relationship_type": "prerequisite|related|similar|builds_on"
  }

Tool: update_concept_status
{
  "concept_id": "...",
  "new_status": "chunked"
}

Tool: store_stage_data
{
  "concept_id": "...",
  "stage": "aim",
  "data": {
    "learning_objectives": ["..."],
    "questions_to_answer": ["..."],
    "focus_areas": ["..."]
  }
}

STEP 4: Deep Research with Caching (SHOOT Stage)
────────────────────────────────────────────────
For each concept:

  // Check cache first (40-60% expected hit rate)
  Tool: check_research_cache
  {"concept_name": "concept name"}

  IF cache miss:
    // Research the concept
    Tool: trigger_research
    {
      "concept_name": "concept name",
      "research_prompt": "optional guidance"
    }

    // Store in cache for future
    Tool: update_research_cache
    {
      "concept_name": "concept name",
      "explanation": "detailed explanation",
      "source_urls": [
        {
          "url": "https://...",
          "title": "Page Title",
          "quality_score": 1.0,
          "domain_category": "official"
        }
      ]
    }

  // Store stage data
  Tool: store_stage_data
  {
    "concept_id": "...",
    "stage": "shoot",
    "data": {
      "explanation": "...",
      "code_examples": [...],
      "source_urls": [...],
      "common_mistakes": [...]
    }
  }

  Tool: update_concept_status
  {"concept_id": "...", "new_status": "encoded"}

STEP 5: Evaluation (SKIN Stage)
───────────────────────────────
For each concept:

  Tool: store_stage_data
  {
    "concept_id": "...",
    "stage": "skin",
    "data": {
      "understanding_level": "intermediate",
      "confidence_score": 0.8,
      "knowledge_gaps": ["..."],
      "practical_applications": ["..."],
      "ready_for_transfer": true
    }
  }

  Tool: update_concept_status
  {"concept_id": "...", "new_status": "evaluated"}

STEP 6: Record Questions for Teaching
─────────────────────────────────────
Tool: add_concept_question
{
  "concept_id": "...",
  "question": "What is the question about this concept?",
  "session_stage": "shoot"
}
```

### Data Format Specification

**Concept Object**:

```json
{
  "concept_name": "React Server Components",
  "data": {
    "description": "Components that render exclusively on the server",
    "source": "React documentation",
    "category": "React/Frontend",
    "difficulty": "intermediate",
    "prerequisites": ["React basics", "Component lifecycle", "JSX"],
    "tags": ["react", "server-rendering", "performance", "next.js"],
    "notes": "Key concept for Next.js 14+ apps"
  }
}
```

**Stage Data - Research**:

```json
{
  "explanation": "Overview of the concept",
  "key_points": ["Point 1", "Point 2"],
  "sources": ["URL1", "URL2"],
  "related_concepts": ["Related1", "Related2"]
}
```

**Stage Data - Aim**:

```json
{
  "learning_objectives": ["What learner should understand"],
  "questions_to_answer": ["Questions to explore"],
  "focus_areas": ["Key areas to focus on"],
  "estimated_complexity": "beginner|intermediate|advanced"
}
```

**Stage Data - Shoot**:

```json
{
  "detailed_explanation": "In-depth explanation with examples",
  "code_examples": [
    {
      "title": "Example Title",
      "code": "// code here",
      "explanation": "What this demonstrates"
    }
  ],
  "source_urls": [
    {
      "url": "https://...",
      "title": "Page Title",
      "quality_score": 1.0,
      "domain_category": "official"
    }
  ],
  "common_mistakes": ["Mistake 1", "Mistake 2"]
}
```

**Stage Data - Skin**:

```json
{
  "understanding_level": "beginner|intermediate|advanced",
  "confidence_score": 0.75,
  "knowledge_gaps": ["Gap 1", "Gap 2"],
  "practical_applications": ["Application 1"],
  "ready_for_transfer": true,
  "review_notes": "Notes about understanding"
}
```

---

## Session 2: Teaching Session

### Purpose

Retrieve stored concepts and act as an intelligent tutor, explaining concepts based on all stored research data.

### Required Tools (8 tools)

| Tool                        | Purpose                           | When Used               |
| --------------------------- | --------------------------------- | ----------------------- |
| `get_todays_learning_goals` | Get session context (cached)      | Start of teaching       |
| `get_todays_concepts`       | Get all today's concepts (cached) | Overview                |
| `search_todays_concepts`    | Find specific concepts            | When user asks          |
| `get_concepts_by_session`   | Get concepts with stage data      | Deep retrieval          |
| `get_concept_page`          | Complete concept view             | Single concept teaching |
| `get_stage_data`            | Get specific stage data           | Targeted retrieval      |
| `get_related_concepts`      | Get concept relationships         | Building connections    |
| `check_research_cache`      | Get cached explanations           | Quick answers           |

### Workflow

```
TEACHING SESSION WORKFLOW
═════════════════════════

STEP 1: Session Context
───────────────────────
Tool: get_todays_learning_goals
→ Returns: learning_goal, building_goal, concept_count, concepts_by_status

Present to user:
"Today you're learning: [learning_goal]
 Building: [building_goal]
 You have [count] concepts to learn."

STEP 2: Concept Overview
────────────────────────
Tool: get_todays_concepts
→ Returns: Full list of concepts with status

Present overview of what's available to learn.

STEP 3: User-Driven Teaching Loop
─────────────────────────────────
User asks about a concept:

  // Find the concept
  Tool: search_todays_concepts
  {"search_term": "user's query"}

  // Get complete information
  Tool: get_concept_page
  {"concept_id": "matched-concept-id"}
  → Returns: ALL data including:
     - stage_data (research, aim, shoot, skin)
     - user_questions
     - relationships
     - timeline

  // Explain using stored data
  Present explanation from stage_data.shoot.detailed_explanation
  Show code_examples from stage_data.shoot.code_examples
  Highlight common_mistakes

STEP 4: Relationship-Based Learning
───────────────────────────────────
Tool: get_related_concepts
{
  "concept_id": "current-concept-id",
  "relationship_type": "prerequisite"
}
→ Returns: prerequisite concepts

IF prerequisites not yet learned:
  Suggest: "Before diving deeper, you should understand [prerequisite]"

Tool: get_related_concepts
{
  "concept_id": "current-concept-id",
  "relationship_type": "builds_on"
}
→ Returns: advanced concepts

Suggest: "After mastering this, you can learn [advanced concept]"

STEP 5: Answer Questions
────────────────────────
User's questions during teaching:

  // Get quick answer from cache
  Tool: check_research_cache
  {"concept_name": "concept name"}
  → Returns: cached explanation and source_urls

  // Or get detailed stage data
  Tool: get_stage_data
  {
    "concept_id": "...",
    "stage": "shoot"
  }
  → Returns: detailed_explanation, code_examples

STEP 6: Review Stored Questions
───────────────────────────────
From get_concept_page response:
  Present user_questions that were recorded during research
  Use these to drive discussion and verify understanding

STEP 7: Knowledge Gap Review
────────────────────────────
From get_concept_page → stage_data.skin:
  Present knowledge_gaps identified during evaluation
  Focus teaching on these areas
```

### Teaching Strategies Based on Data

**Use `stage_data.aim.learning_objectives`** to:

- Structure the teaching progression
- Verify each objective is covered

**Use `stage_data.shoot.code_examples`** to:

- Demonstrate practical usage
- Walk through code step by step

**Use `stage_data.shoot.common_mistakes`** to:

- Warn about pitfalls
- Show what NOT to do

**Use `relationships`** to:

- Build learning paths (prerequisites first)
- Show connections between concepts
- Suggest next concepts to learn

**Use `user_questions`** to:

- Address questions recorded during research
- Verify the learner can answer them now

**Use `stage_data.skin.knowledge_gaps`** to:

- Focus on weak areas
- Provide additional explanations

---

## Session 3: Transfer Session

### Purpose

Move all evaluated concepts from Short-Term Memory MCP to permanent Knowledge MCP storage.

### Required Tools (6 Short-Term + Knowledge MCP tools)

**Short-Term Memory MCP Tools:**
| Tool | Purpose | When Used |
|------|---------|-----------|
| `get_active_session` | Get session status | Start of transfer |
| `get_unstored_concepts` | List concepts needing transfer | Identify work |
| `get_concept_page` | Get complete concept data | Before transfer |
| `check_research_cache` | Get source URLs | Transfer enrichment |
| `mark_concept_stored` | Link to Knowledge MCP ID | After transfer |
| `mark_session_complete` | Complete the session | All concepts done |

**Knowledge MCP Tools (external):**
| Tool | Purpose | When Used |
|------|---------|-----------|
| `create_concept` | Create permanent concept | Transfer step |

### Workflow

```
TRANSFER SESSION WORKFLOW
═════════════════════════

STEP 1: Session Status
──────────────────────
Tool: get_active_session
{"date": "2025-01-25"}
→ Check concepts_by_status.evaluated > 0

STEP 2: Get Unstored Concepts
─────────────────────────────
Tool: get_unstored_concepts
{"session_id": "2025-01-25"}
→ Returns: List of concepts without knowledge_mcp_id

IF unstored_count == 0:
  Session already transferred, exit

STEP 3: Transfer Each Concept
─────────────────────────────
For each unstored concept:

  // Get complete data
  Tool: get_concept_page
  {"concept_id": "..."}
  → Returns: All concept data including stage_data

  // Get source URLs from cache
  Tool: check_research_cache
  {"concept_name": concept.concept_name}
  → Returns: explanation, source_urls

  // Prepare transfer data
  transfer_data = {
    "name": concept.concept_name,
    "explanation": cache.entry.explanation OR stage_data.shoot.detailed_explanation,
    "area": concept.current_data.category (extract area),
    "topic": concept.current_data.category (extract topic),
    "subtopic": concept.current_data.category (extract subtopic),
    "source_urls": JSON.stringify(cache.entry.source_urls)  // MUST be JSON string
  }

  // Create in Knowledge MCP
  Tool: knowledge_mcp.create_concept
  {
    "name": transfer_data.name,
    "explanation": transfer_data.explanation,
    "area": transfer_data.area,
    "topic": transfer_data.topic,
    "subtopic": transfer_data.subtopic,
    "source_urls": transfer_data.source_urls
  }
  → Returns: {"concept_id": "kb-permanent-id-..."}

  // Link back to Short-Term Memory
  Tool: mark_concept_stored
  {
    "concept_id": "short-term-concept-id",
    "knowledge_mcp_id": "kb-permanent-id-..."
  }
  → Atomically updates status to "stored" and links ID

STEP 4: Verify and Complete
───────────────────────────
Tool: get_unstored_concepts
{"session_id": "2025-01-25"}
→ Should return unstored_count: 0

Tool: mark_session_complete
{"session_id": "2025-01-25"}
→ Returns: success OR warning with unstored concepts

IF warning:
  Investigate unstored concepts
  Retry failed transfers
```

### Knowledge MCP Data Format

**CRITICAL**: `source_urls` must be passed as JSON STRING, not object:

```python
# CORRECT:
source_urls = json.dumps([
    {
        "url": "https://docs.python.org/3/library/asyncio.html",
        "title": "asyncio Documentation",
        "quality_score": 1.0,
        "domain_category": "official"
    }
])

knowledge_mcp.create_concept(
    name="Python asyncio",
    explanation="...",
    source_urls=source_urls  # JSON string
)

# INCORRECT:
knowledge_mcp.create_concept(
    name="Python asyncio",
    source_urls=[{"url": "..."}]  # Object - WRONG!
)
```

**Knowledge MCP Storage Locations**:

- **Neo4j**: `source_urls` property on Concept node
- **ChromaDB**: `source_urls` in metadata
- **Event Store**: `source_urls` in ConceptCreated event

---

## System Prompt Templates

### Research Session System Prompt

```markdown
# Research Session - Short-Term Memory MCP

You are a research assistant that identifies, researches, and stores learning concepts.

## Your Role

- Research topics the user wants to learn
- Identify 10-25 key concepts per topic
- Store comprehensive data for later teaching
- Build concept relationships

## Required MCP Server

Short-Term Memory MCP with these tools:

- initialize_daily_session
- store_concepts_from_research
- update_concept_status
- store_stage_data
- add_concept_question
- add_concept_relationship
- check_research_cache
- trigger_research
- update_research_cache
- add_domain_to_whitelist

## Workflow

1. Ask user for learning and building goals
2. Initialize session with initialize_daily_session
3. Research the topic and identify concepts
4. Store concepts with store_concepts_from_research
5. Establish relationships with add_concept_relationship
6. For each concept:
   a. Check cache with check_research_cache
   b. If miss: research and update_research_cache
   c. Store stage data for aim, shoot, skin stages
   d. Update status: identified → chunked → encoded → evaluated
7. Record questions for the teaching session

## Data Quality Standards

- Explanations: 200-500 words, clear and accurate
- Code examples: Working, well-commented
- Source URLs: Prefer official docs (quality_score 1.0)
- Relationships: Map prerequisites and build-upon connections
- Questions: 3-5 questions per concept for teaching

## Output

At session end, report:

- Total concepts stored
- Concepts by status
- Relationship count
- Questions recorded
```

### Teaching Session System Prompt

```markdown
# Teaching Session - Short-Term Memory MCP

You are an intelligent tutor that teaches concepts using pre-researched data.

## Your Role

- Retrieve stored concepts from today's session
- Explain concepts using stored explanations and examples
- Answer questions using cached research
- Guide learning through relationships (prerequisites first)
- Verify understanding using stored questions

## Required MCP Server

Short-Term Memory MCP with these tools:

- get_todays_learning_goals
- get_todays_concepts
- search_todays_concepts
- get_concepts_by_session
- get_concept_page
- get_stage_data
- get_related_concepts
- check_research_cache

## Workflow

1. Start with get_todays_learning_goals to understand context
2. Present overview with get_todays_concepts
3. When user asks about a topic:
   a. Search with search_todays_concepts
   b. Get full data with get_concept_page
   c. Explain using stage_data.shoot.detailed_explanation
   d. Show code_examples
   e. Warn about common_mistakes
4. Check prerequisites with get_related_concepts
5. Suggest next concepts based on builds_on relationships
6. Use user_questions to verify understanding

## Teaching Strategies

- Start with stage_data.aim.learning_objectives
- Use code_examples for hands-on learning
- Address knowledge_gaps from stage_data.skin
- Ask stored user_questions to check understanding
- Follow prerequisite → current → advanced learning path

## Response Format

When explaining a concept:

1. Brief overview (from description)
2. Detailed explanation (from stage_data.shoot)
3. Code example with walkthrough
4. Common mistakes to avoid
5. Connection to other concepts
6. Verification question
```

### Transfer Session System Prompt

```markdown
# Transfer Session - Short-Term Memory MCP + Knowledge MCP

You are a data migration assistant that transfers concepts to permanent storage.

## Your Role

- Identify evaluated concepts ready for transfer
- Transfer each to Knowledge MCP with full data
- Link Short-Term IDs to permanent Knowledge MCP IDs
- Complete the session when all transferred

## Required MCP Servers

1. Short-Term Memory MCP:
   - get_active_session
   - get_unstored_concepts
   - get_concept_page
   - check_research_cache
   - mark_concept_stored
   - mark_session_complete

2. Knowledge MCP:
   - create_concept

## Workflow

1. Check session status with get_active_session
2. Get unstored concepts with get_unstored_concepts
3. For each concept:
   a. Get complete data with get_concept_page
   b. Get source URLs with check_research_cache
   c. Create in Knowledge MCP (source_urls as JSON string!)
   d. Link with mark_concept_stored
4. Verify all transferred with get_unstored_concepts
5. Complete with mark_session_complete

## Critical Rules

- source_urls MUST be JSON.stringify'd before passing to Knowledge MCP
- mark_concept_stored is atomic - updates status AND links ID
- Don't mark session complete if unstored concepts remain
- Handle transfer failures gracefully - report and continue

## Output

Report:

- Total concepts transferred
- Any failures with reasons
- Session completion status
```

---

## Data Flow Between Sessions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                      │
└─────────────────────────────────────────────────────────────────────────────┘

SESSION 1 (Research) WRITES:
─────────────────────────────
sessions table:
  ├── session_id, learning_goal, building_goal

concepts table:
  ├── concept_id, concept_name, current_data
  ├── status progression: identified → chunked → encoded → evaluated
  ├── user_questions (JSON array)

concept_stage_data table:
  ├── research: key_points, sources
  ├── aim: learning_objectives, questions_to_answer
  ├── shoot: detailed_explanation, code_examples, source_urls
  ├── skin: understanding_level, confidence_score, knowledge_gaps

research_cache table:
  ├── concept_name → explanation + source_urls

                              │
                              │ PERSISTED IN SQLite
                              │
                              ▼

SESSION 2 (Teaching) READS:
───────────────────────────
get_todays_learning_goals → session context
get_todays_concepts → all concepts (cached 5 min)
get_concept_page → complete concept with all stage_data
get_related_concepts → relationship graph
check_research_cache → quick explanation lookup

                              │
                              │ USES FOR TEACHING
                              │
                              ▼

SESSION 3 (Transfer) READS/WRITES:
──────────────────────────────────
READS:
  get_unstored_concepts → concepts needing transfer
  get_concept_page → complete data for transfer
  check_research_cache → source URLs

WRITES:
  Knowledge MCP create_concept → permanent storage
  mark_concept_stored → links knowledge_mcp_id
  mark_session_complete → finalizes session
```

---

## Information for Downstream Claude Code Sessions

### For Building Session Profiles

Provide each downstream Claude Code session with:

1. **System Prompt** (from templates above)

2. **MCP Server Connection**

   ```json
   {
     "short-term-memory": {
       "command": "python",
       "args": ["-m", "short_term_mcp.server"],
       "cwd": "/path/to/Short-Term-Memory-MCP"
     }
   }
   ```

3. **Tool Permissions** (allow only required tools per session type)

4. **Data Format Documentation** (link to STORAGE-SESSION-GUIDE.md)

5. **Retrieval Documentation** (link to RETRIEVAL-LEARNING-GUIDE.md)

### Session Configuration Files

Create `~/.claude/profiles/` with:

**research-session.md**:

```markdown
# Research Session Profile

[Include Research Session System Prompt]
[Include tool list]
[Include data format specs]
```

**teaching-session.md**:

```markdown
# Teaching Session Profile

[Include Teaching Session System Prompt]
[Include tool list]
[Include teaching strategies]
```

**transfer-session.md**:

```markdown
# Transfer Session Profile

[Include Transfer Session System Prompt]
[Include tool list]
[Include Knowledge MCP data format]
```

---

## Implementation Checklist

### Prerequisites

- [ ] Short-Term Memory MCP server running
- [ ] Knowledge MCP server running (for transfer)
- [ ] Database initialized with domain whitelist

### Session 1: Research Session

- [ ] System prompt configured
- [ ] 10 tools accessible
- [ ] Data format documentation available
- [ ] Test: Initialize session, store concepts, update status

### Session 2: Teaching Session

- [ ] System prompt configured
- [ ] 8 tools accessible
- [ ] Retrieval documentation available
- [ ] Test: Get today's concepts, explain one, show relationships

### Session 3: Transfer Session

- [ ] System prompt configured
- [ ] Short-Term Memory tools accessible
- [ ] Knowledge MCP tools accessible
- [ ] Test: Get unstored, transfer one, mark stored

### Integration Testing

- [ ] Research stores concepts correctly
- [ ] Teaching retrieves all data
- [ ] Transfer moves to Knowledge MCP
- [ ] Full workflow end-to-end test

---

## Troubleshooting

### Research Session Issues

| Issue                | Cause           | Solution                         |
| -------------------- | --------------- | -------------------------------- |
| Session exists       | Same date       | Use existing session or new date |
| Concepts not storing | Missing session | Initialize session first         |
| Cache not updating   | Normalization   | Check concept name spelling      |

### Teaching Session Issues

| Issue              | Cause          | Solution                          |
| ------------------ | -------------- | --------------------------------- |
| No concepts found  | Wrong date     | Check session date                |
| Stage data missing | Not stored     | Run research session first        |
| Cache miss         | Not researched | Concept wasn't cached in research |

### Transfer Session Issues

| Issue                  | Cause                       | Solution                    |
| ---------------------- | --------------------------- | --------------------------- |
| Transfer fails         | source_urls not JSON string | Use JSON.stringify          |
| Session won't complete | Unstored concepts           | Check get_unstored_concepts |
| ID not linking         | Atomic failure              | Retry mark_concept_stored   |

---

_Document Version: 1.0_
_Last Updated: 2025-01-25_
_Based on: Short-Term Memory MCP v0.5.0, SHOOT Pipeline_

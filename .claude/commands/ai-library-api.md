# AI Library Backend API

Complete reference for the Knowledge Library (AI Library) Python backend.

**Location**: `2.ai-library/`

## API Overview

**Base URL**: `http://localhost:8002` (configurable via `VITE_KNOWLEDGE_LIBRARY_API`)

**Entry Point**: `src/api/main.py` - FastAPI application

**Main Routers**:

- `/api/sessions` - Session CRUD and workflow
- `/api/library` - Library browsing and scanning
- `/api/query` - Semantic search and RAG

## Session Endpoints

### CRUD Operations

| Method   | Endpoint             | Purpose             |
| -------- | -------------------- | ------------------- |
| `POST`   | `/api/sessions`      | Create new session  |
| `GET`    | `/api/sessions`      | List all sessions   |
| `GET`    | `/api/sessions/{id}` | Get session details |
| `DELETE` | `/api/sessions/{id}` | Delete session      |

### Source Upload

| Method | Endpoint                    | Purpose                         |
| ------ | --------------------------- | ------------------------------- |
| `POST` | `/api/sessions/{id}/upload` | Upload markdown file (max 10MB) |
| `GET`  | `/api/sessions/{id}/blocks` | Get extracted blocks            |

### Cleanup Plan Phase

| Method | Endpoint                                       | Purpose                   |
| ------ | ---------------------------------------------- | ------------------------- |
| `POST` | `/api/sessions/{id}/cleanup/generate`          | Generate cleanup plan     |
| `GET`  | `/api/sessions/{id}/cleanup`                   | Get current cleanup plan  |
| `POST` | `/api/sessions/{id}/cleanup/decide/{block_id}` | Set keep/discard decision |
| `POST` | `/api/sessions/{id}/cleanup/approve`           | Approve cleanup plan      |

**Query params for generate**: `use_ai=true/false`

### Routing Plan Phase

| Method | Endpoint                                    | Purpose                  |
| ------ | ------------------------------------------- | ------------------------ |
| `POST` | `/api/sessions/{id}/plan/generate`          | Generate routing plan    |
| `GET`  | `/api/sessions/{id}/plan`                   | Get current routing plan |
| `POST` | `/api/sessions/{id}/plan/select/{block_id}` | Select destination       |
| `POST` | `/api/sessions/{id}/plan/approve`           | Final approval           |

**Query params for generate**: `use_ai=true/false`, `use_candidate_finder=true`

### Execution

| Method | Endpoint                     | Purpose                          |
| ------ | ---------------------------- | -------------------------------- |
| `POST` | `/api/sessions/{id}/execute` | Write approved blocks to library |

### Content Mode

| Method | Endpoint                  | Purpose                    |
| ------ | ------------------------- | -------------------------- |
| `POST` | `/api/sessions/{id}/mode` | Toggle STRICT ↔ REFINEMENT |

## WebSocket Streaming

**Endpoint**: `WebSocket /api/sessions/{id}/stream`

### Commands (Client → Server)

| Command            | Payload                 | Purpose                       |
| ------------------ | ----------------------- | ----------------------------- |
| `generate_cleanup` | -                       | Start cleanup plan generation |
| `generate_routing` | -                       | Start routing plan generation |
| `user_message`     | `{message: string}`     | Send user guidance            |
| `answer`           | `{question_id, answer}` | Answer pending question       |
| `ping`             | -                       | Keep-alive                    |

### Events (Server → Client)

| Event             | Payload          | Purpose                     |
| ----------------- | ---------------- | --------------------------- |
| `cleanup_started` | -                | Cleanup generation begun    |
| `cleanup_ready`   | -                | Plan ready, refresh data    |
| `routing_started` | -                | Routing generation begun    |
| `routing_ready`   | -                | Plan ready, refresh data    |
| `question`        | `{id, question}` | AI asking for clarification |
| `error`           | `{message}`      | Error occurred              |
| `progress`        | `{...}`          | Progress indicator          |
| `connected`       | -                | WebSocket connected         |

## Key Schemas

### Session

```typescript
SessionResponse {
  id: string
  phase: SessionPhase
  created_at: string
  updated_at: string
  content_mode: "strict" | "refinement"
  library_path: string
  source_file: string | null
  total_blocks: number
  kept_blocks: number
  discarded_blocks: number
  has_cleanup_plan: boolean
  has_routing_plan: boolean
  cleanup_approved: boolean
  routing_approved: boolean
  can_execute: boolean
  errors: string[]
}
```

### Session Phases

```
initialized → parsing → cleanup_plan_ready → routing_plan_ready
→ awaiting_approval → ready_to_execute → executing → verifying → completed
                                                              ↘ error
```

### Cleanup Plan

```typescript
CleanupPlanResponse {
  session_id: string
  items: CleanupItemResponse[]
  all_decided: boolean
  approved: boolean
  pending_count: number
  total_count: number
  ai_generated: boolean
  duplicate_groups: string[][]
}

CleanupItemResponse {
  block_id: string
  heading_path: string[]
  content_preview: string
  suggested_disposition: "keep" | "discard"
  suggestion_reason: string
  confidence: number  // 0.0-1.0
  final_disposition: "keep" | "discard" | null
  ai_analyzed: boolean
  similar_block_ids: string[]
  similarity_score: number
}
```

### Routing Plan

```typescript
RoutingPlanResponse {
  session_id: string
  blocks: BlockRoutingItemResponse[]
  all_blocks_resolved: boolean
  approved: boolean
  pending_count: number
  accepted_count: number
}

BlockRoutingItemResponse {
  block_id: string
  heading_path: string[]
  content_preview: string
  options: DestinationOptionResponse[]  // 3 options
  selected_option_index: number | null
  custom_destination_file: string | null
  custom_destination_section: string | null
  custom_action: string | null
  status: "pending" | "selected" | "rejected"
}

DestinationOptionResponse {
  destination_file: string
  destination_section: string
  action: "create_file" | "create_section" | "append" | "insert_before" | "insert_after" | "merge"
  confidence: number
  reasoning: string
  proposed_file_title: string | null
  proposed_file_overview: string | null
}
```

### Execution Result

```typescript
ExecuteResponse {
  session_id: string
  success: boolean
  total_blocks: number
  blocks_written: number
  blocks_failed: number
  all_verified: boolean
  results: WriteResultResponse[]
  errors: string[]
}

WriteResultResponse {
  block_id: string
  destination_file: string
  success: boolean
  checksum_verified: boolean
  error: string | null
}
```

## File Structure

```
2.ai-library/
├── src/
│   ├── api/
│   │   ├── main.py           # FastAPI app entry
│   │   ├── routes/
│   │   │   ├── sessions.py   # Session endpoints
│   │   │   ├── library.py    # Library endpoints
│   │   │   └── query.py      # Query endpoints
│   │   └── schemas.py        # Pydantic schemas
│   ├── session/
│   │   └── manager.py        # Session lifecycle management
│   ├── models/
│   │   ├── session.py        # ExtractionSession model
│   │   ├── cleanup_plan.py   # CleanupPlan model
│   │   └── routing_plan.py   # RoutingPlan model
│   ├── sdk/
│   │   └── client.py         # Claude SDK integration
│   └── config.py             # Configuration
├── configs/
│   └── settings.yaml         # Default settings
└── start-api.sh              # Launch script
```

## Running the Backend

```bash
cd 2.ai-library
./start-api.sh
# Or manually:
uvicorn src.api.main:app --reload --port 8002
```

## AI Integration

The backend uses Claude Code SDK for AI-powered decisions:

**Location**: `src/sdk/client.py`

**Authentication**:

1. `ANTHROPIC_AUTH_TOKEN` env var
2. `~/.automaker/credentials.json` → `anthropic_oauth_token`

**System Prompts**:

- `CLEANUP_SYSTEM_PROMPT` - Guides keep/discard decisions
- `ROUTING_SYSTEM_PROMPT` - Suggests destination options
